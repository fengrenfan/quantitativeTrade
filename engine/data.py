"""数据层：优先用 AkShare 拉 A 股/ETF 行情并本地缓存，失败时回退到合成数据。

标的代码格式：6 位数字 + 交易所后缀，例如 600519.SH / 002594.SZ / 510300.SH

返回的 DataFrame 带 attrs["source"]，取值：
  - "akshare"：真实行情
  - "cache"  ：本地缓存
  - "mock"   ：合成兜底数据（不可用于投资决策）
"""
import os
import re
from datetime import datetime

import pandas as pd

from . import config
from .mock_data import synthetic_60min, synthetic_daily

# 部分行情接口（如东方财富）会对 python-requests 的默认 UA 直接断连
# （RemoteDisconnected），必须伪装成浏览器 UA 才能取到数据。
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _patch_requests_ua() -> None:
    """给 requests 的默认请求补上浏览器 UA（不覆盖调用方已显式设置的 UA）。"""
    try:
        import requests
    except Exception:
        return
    if getattr(requests, "_quant_ua_patched", False):
        return

    original = requests.sessions.Session.request

    def patched(self, method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        if not any(str(k).lower() == "user-agent" for k in headers):
            headers["User-Agent"] = _BROWSER_UA
        kwargs["headers"] = headers
        return original(self, method, url, **kwargs)

    requests.sessions.Session.request = patched
    requests._quant_ua_patched = True


_patch_requests_ua()

try:
    import akshare as ak
except Exception:  # akshare 未安装
    ak = None

# 中文/英文列名 → 统一英文列名
_REN = {
    "日期": "Date", "时间": "Date",
    "开盘": "Open", "最高": "High", "最低": "Low", "收盘": "Close", "成交量": "Volume",
    "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume",
}


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _tag(df: pd.DataFrame, source: str) -> pd.DataFrame:
    df.attrs["source"] = source
    return df


def _ensure_dir(d: str) -> None:
    os.makedirs(d, exist_ok=True)


def _split_code(code: str) -> tuple[str, str]:
    m = re.match(r"^(\d{6})\.(SH|SZ)$", code, re.IGNORECASE)
    if not m:
        raise ValueError(f"代码格式应为 6 位数字+交易所后缀，例如 600519.SH，当前为：{code}")
    return m.group(1), m.group(2).upper()


def _is_etf(num: str, ex: str) -> bool:
    if ex == "SH" and num.startswith(("510", "511", "512", "513", "515", "516", "517", "518", "588")):
        return True
    if ex == "SZ" and num.startswith("159"):
        return True
    return False


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=_REN)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")
    df = df.sort_index()
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df.get("Close")
    for k in ["Open", "High", "Low", "Close", "Volume"]:
        if k not in df.columns:
            df[k] = df["Close"] if "Close" in df.columns else 0.0
    df = df[[c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in df.columns]]
    df.index.name = "Date"
    return df


def _cache_path(code: str, timeframe: str) -> str:
    _ensure_dir(config.CACHE_DIR)
    return os.path.join(config.CACHE_DIR, f"{code}_{timeframe}.csv")


def _download_daily(code: str, start: str, end: str | None, adjust: str = "qfq") -> pd.DataFrame:
    num, ex = _split_code(code)
    # 注意：end 为空时必须补成今天，否则部分接口会静默返回空表
    end = end or _today()
    s, e = start.replace("-", ""), end.replace("-", "")
    if _is_etf(num, ex):
        df = ak.fund_etf_hist_em(symbol=num, period="daily", start_date=s, end_date=e, adjust=adjust)
    else:
        df = ak.stock_zh_a_hist(symbol=num, period="daily", start_date=s, end_date=e, adjust=adjust)
    return _normalize(df)


def _download_60min(code: str, start: str, end: str | None, adjust: str = "qfq") -> pd.DataFrame:
    num, _ = _split_code(code)
    df = ak.stock_zh_a_hist_min_em(symbol=num, period="60", adjust=adjust)
    return _normalize(df)


def _resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "daily":
        return df
    if timeframe == "weekly":
        out = df.resample("W-FRI").agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last",
             "Adj Close": "last", "Volume": "sum"}
        ).dropna(how="all")
        return out
    return df  # 60min 已是目标粒度


def get_price(
    code: str,
    start: str = config.DEFAULT_START,
    end: str | None = config.DEFAULT_END,
    timeframe: str = "daily",
    use_cache: bool = True,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """返回规范化行情 DataFrame（索引为日期，含 Adj Close，attrs['source'] 标明来源）。

    失败自动回退合成数据；空结果不会被当成成功写入缓存。
    """
    start = start or config.DEFAULT_START
    path = _cache_path(code, timeframe)

    # 1) 本地缓存（区间无数据则丢弃，避免用陈旧缓存掩盖新请求）
    if use_cache and os.path.exists(path):
        try:
            cached = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            if len(cached) > 0:
                out = cached.loc[start:end]
                if len(out) > 0:
                    return _tag(out, "cache")
        except Exception:
            pass
        try:
            os.remove(path)
        except OSError:
            pass

    # 2) AkShare 实时拉取
    if ak is not None:
        try:
            if timeframe == "60min":
                raw = _download_60min(code, start, end, adjust)
            else:
                raw = _download_daily(code, start, end, adjust)
            df = _resample(raw, timeframe)
            if df is None or len(df) == 0:
                raise RuntimeError("AkShare 返回空数据")
            out = df.loc[start:end]
            if len(out) == 0:
                raise RuntimeError(f"AkShare 在 {start} ~ {end or _today()} 区间无数据")
            out.to_csv(path)
            return _tag(out, "akshare")
        except Exception as exc:  # 网络/接口异常 → 回退
            print(f"[data] AkShare 获取 {code} 失败，回退合成数据：{exc}")

    # 3) 兜底：合成数据
    df = synthetic_60min(code, "2024-01-01", end) if timeframe == "60min" else synthetic_daily(code, start, end)
    df = _resample(df, timeframe)
    return _tag(df.loc[start:end], "mock")


def get_close(code: str, **kwargs) -> pd.Series:
    df = get_price(code, **kwargs)
    s = df["Adj Close"].astype(float)
    s.name = code
    return s
