"""回测引擎（向量化）：给定价格与权重表，算出净值、回撤、换手与成本。

关键防坑：用 weights.shift(1)（昨日权重）乘以今日收益，杜绝未来函数。
"""
import pandas as pd

from . import config


def backtest_weights(
    close: pd.Series,
    weights: pd.DataFrame,
    cost_bps: float = config.DEFAULT_COST_BPS,
) -> pd.DataFrame:
    close = close.sort_index().astype(float)
    weights = weights.reindex(close.index).ffill().fillna(0.0)
    asset = weights.columns[0]

    rets = close.pct_change().fillna(0.0)
    w_prev = weights.shift(1).fillna(0.0)  # 昨日权重

    # 单边换手率 = |权重变化| 之和 / 2（asset 与 cash 各算一半）
    turnover = (weights - w_prev).abs().sum(axis=1) / 2.0
    tc = turnover * (cost_bps / 1e4)

    port_ret_gross = rets * w_prev[asset]
    port_ret = port_ret_gross - tc
    nav = (1.0 + port_ret).cumprod()
    dd = nav / nav.cummax() - 1.0
    benchmark_nav = (1.0 + rets).cumprod()

    return pd.DataFrame(
        {
            "port_ret": port_ret,
            "port_ret_gross": port_ret_gross,
            "turnover": turnover,
            "nav": nav,
            "dd": dd,
            "benchmark_nav": benchmark_nav,
            "position": weights[asset],
            "close": close,
        },
        index=close.index,
    )
