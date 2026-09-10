"""离线兜底数据：当 AkShare 不可用（断网/未安装）时，生成确定性的合成行情。

注意：合成数据仅用于让系统跑通，不具备任何投资参考价值。
"""
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd


def _seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.encode("utf-8")).hexdigest()[:8], 16) % (2 ** 32)


def _base_price(symbol: str) -> float:
    # 依 symbol 派生一个 20~300 的基准价，保证不同标的形态不同
    return 20.0 + (_seed(symbol) % 280)


def synthetic_daily(symbol: str, start: str = "2021-01-01", end: str | None = None) -> pd.DataFrame:
    end = end or datetime.now().strftime("%Y-%m-%d")
    idx = pd.bdate_range(start, end)
    n = len(idx)
    if n == 0:
        idx = pd.bdate_range("2021-01-01", datetime.now().strftime("%Y-%m-%d"))
        n = len(idx)

    rng = np.random.default_rng(_seed(symbol))
    drift = 0.0004
    vol = 0.02
    rets = rng.normal(drift, vol, n) + 0.0004 * np.sin(np.arange(n) / 45.0)
    close = _base_price(symbol) * np.exp(np.cumsum(rets))

    high = close * (1 + np.abs(rng.normal(0, 0.009, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.009, n)))
    open_ = close * (1 + rng.normal(0, 0.007, n))
    volume = rng.integers(1_000_000, 6_000_000, n)

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )
    df["Adj Close"] = df["Close"]
    df.index.name = "Date"
    return df


def synthetic_60min(symbol: str, start: str = "2024-01-01", end: str | None = None) -> pd.DataFrame:
    """合成 60 分钟线：每个交易日 4 根（A 股 4 小时）。"""
    end_dt = pd.to_datetime(end) if end else pd.Timestamp.now().normalize()
    days = pd.bdate_range(start, end_dt)
    stamps = []
    for d in days:
        stamps.extend([d + pd.Timedelta(hours=h) for h in (10, 11, 14, 15)])
    idx = pd.DatetimeIndex(stamps)
    n = len(idx)
    if n == 0:
        return synthetic_daily(symbol, start, end)

    rng = np.random.default_rng(_seed(symbol) + 7)
    rets = rng.normal(0.0001, 0.008, n) + 0.0002 * np.sin(np.arange(n) / 30.0)
    close = _base_price(symbol) * np.exp(np.cumsum(rets))
    high = close * (1 + np.abs(rng.normal(0, 0.004, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.004, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(100_000, 900_000, n)

    df = pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )
    df["Adj Close"] = df["Close"]
    df.index.name = "Date"
    return df
