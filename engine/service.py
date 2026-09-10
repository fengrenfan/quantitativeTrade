"""编排层：把「取数 → 策略 → 回测 → 绩效」串起来，输出前端可直接渲染的结构。"""
import pandas as pd

from . import config
from .backtest import backtest_weights
from .data import get_price
from .metrics import summary
from .strategies import STRATEGY_FUNCS, build_weights


def _fmt(dt, timeframe: str) -> str:
    if timeframe == "60min":
        return pd.Timestamp(dt).strftime("%Y-%m-%d %H:%M")
    return pd.Timestamp(dt).strftime("%Y-%m-%d")


def run_signal(
    symbol: str,
    strategy: str = "dual_ma",
    timeframe: str = "daily",
    fast: int = config.DEFAULT_FAST,
    slow: int = config.DEFAULT_SLOW,
    start: str = config.DEFAULT_START,
    end: str | None = config.DEFAULT_END,
    cost_bps: float = config.DEFAULT_COST_BPS,
) -> dict:
    if strategy not in STRATEGY_FUNCS:
        raise ValueError(f"未知策略：{strategy}")
    if timeframe not in config.TIMEFRAMES:
        raise ValueError(f"未知周期：{timeframe}")

    raw = get_price(symbol, start=start, end=end, timeframe=timeframe)
    close = raw["Adj Close"].astype(float)
    close.name = symbol

    weights = build_weights(strategy, close, fast, slow)
    bt = backtest_weights(close, weights, cost_bps)
    metrics = summary(bt)

    raw2 = raw.reindex(bt.index)

    dates = [_fmt(dt, timeframe) for dt in bt.index]
    kline = [
        {
            "date": _fmt(dt, timeframe),
            "open": round(float(o), 3),
            "close": round(float(c), 3),
            "low": round(float(l), 3),
            "high": round(float(h), 3),
        }
        for dt, o, c, l, h in zip(bt.index, raw2["Open"], raw2["Close"], raw2["Low"], raw2["High"])
    ]

    nav = [round(float(x), 4) for x in bt["nav"]]
    benchmark_nav = [round(float(x), 4) for x in bt["benchmark_nav"]]
    position = [int(x > 0.5) for x in bt["position"].fillna(0.0)]

    # 交易信号（持仓 0/1 变化点）
    pos = bt["position"].fillna(0.0)
    delta = pos.diff().fillna(pos)
    signals = []
    for dt, d in delta.items():
        if d > 0.5:
            signals.append({"date": _fmt(dt, timeframe), "type": "buy", "price": round(float(close.loc[dt]), 3)})
        elif d < -0.5:
            signals.append({"date": _fmt(dt, timeframe), "type": "sell", "price": round(float(close.loc[dt]), 3)})

    current_pos = position[-1] if position else 0

    return {
        "symbol": symbol,
        "strategy": strategy,
        "timeframe": timeframe,
        "fast": fast,
        "slow": slow,
        "dates": dates,
        "kline": kline,
        "nav": nav,
        "benchmarkNav": benchmark_nav,
        "position": position,
        "signals": signals,
        "signal": "持多" if current_pos else "空仓",
        "lastClose": kline[-1]["close"] if kline else None,
        "lastDate": dates[-1] if dates else None,
        "metrics": metrics,
    }


def catalog() -> dict:
    return {
        "symbols": config.DEFAULT_SYMBOLS,
        "strategies": config.STRATEGIES,
        "timeframes": config.TIMEFRAMES,
        "defaultFast": config.DEFAULT_FAST,
        "defaultSlow": config.DEFAULT_SLOW,
    }
