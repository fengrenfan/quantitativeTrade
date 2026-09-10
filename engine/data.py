"""数据层：优先用 AkShare 拉 A 股/ETF 行情并本地缓存，失败时回退到合成数据。

标的代码格式：6 位数字 + 交易所后缀，例如 600519.SH / 002594.SZ / 510300.SH
"""
import os
import re

import pandas as pd

from . import config
from .mock_data import synthetic_60min, synthetic_daily

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


def _download_daily(code: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
    num, ex = _split_code(code)
    s, e = start.replace("-", ""), (end or "").replace("-", "")
    if _is_etf(num, ex):
        df = ak.fund_etf_hist_em(symbol=num, period="daily", start_date=s, end_date=e, adjust=adjust)
    else:
        df = ak.stock_zh_a_hist(symbol=num, period="daily", start_date=s, end_date=e, adjust=adjust)
    return _normalize(df)


def _download_60min(code: str, start: str, end: str, adjust: str = "qfq") -> pd.DataFrame:
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
    """返回规范化行情 DataFrame（索引为日期，含 Adj Close）。失败自动回退合成数据。"""
    start = start or config.DEFAULT_START
    path = _cache_path(code, timeframe)
    source = "akshare"

    if use_cache and os.path.exists(path):
        try:
            cached = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            if len(cached) > 0:
                return cached.loc[start:end]
        except Exception:
            pass

    if ak is not None:
        try:
            if timeframe == "60min":
                raw = _download_60min(code, start, end, adjust)
            else:
                raw = _download_daily(code, start, end, adjust)
            df = _resample(raw, timeframe)
            df.to_csv(path)
            return df.loc[start:end]
        except Exception as exc:  # 网络/接口异常 → 回退
            print(f"[data] AkShare 获取 {code} 失败，回退合成数据：{exc}")
            source = "mock"

    # 兜底：合成数据
    df = synthetic_60min(code, "2024-01-01", end) if timeframe == "60min" else synthetic_daily(code, start, end)
    df = _resample(df, timeframe)
    return df.loc[start:end]


def get_close(code: str, **kwargs) -> pd.Series:
    df = get_price(code, **kwargs)
    s = df["Adj Close"].astype(float)
    s.name = code
    return s
