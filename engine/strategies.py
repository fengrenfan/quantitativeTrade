"""策略层：每个策略输入收盘价，输出权重表（列 = [标的, CASH]，两列之和恒为 1）。

设计参考：PandOvo 的「持多 / 持现金」二选一结构；公式参考 je-suis-tm 的策略库。
所有策略都遵循「策略只产出权重，回测与绩效由 backtest/metrics 负责」的解耦原则。
"""
import pandas as pd


def _weights_from_signal(close: pd.Series, signal: pd.Series) -> pd.DataFrame:
    """把 0/1 信号转换为 [标的, CASH] 权重表。"""
    sig = signal.reindex(close.index).fillna(0.0).clip(0.0, 1.0)
    name = close.name or "ASSET"
    return pd.DataFrame({name: sig, "CASH": 1.0 - sig})


def dual_ma(close: pd.Series, fast: int = 5, slow: int = 20) -> pd.DataFrame:
    """双均线：快线上穿慢线持多，下穿空仓。"""
    fast, slow = max(1, int(fast)), max(2, int(slow))
    ma_f = close.rolling(fast).mean()
    ma_s = close.rolling(slow).mean()
    signal = (ma_f > ma_s).astype(float)
    return _weights_from_signal(close, signal)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> pd.DataFrame:
    """MACD：DIF 上穿 DEA 持多，下穿空仓。"""
    fast, slow = max(1, int(fast)), max(2, int(slow))
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    dif = ema_f - ema_s
    dea = dif.ewm(span=max(1, int(signal_period)), adjust=False).mean()
    signal = (dif > dea).astype(float)
    return _weights_from_signal(close, signal)


def bollinger(close: pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    """布林带均值回归（状态机）：跌破下轨买入，回升过中轨卖出。"""
    w = max(3, int(window))
    mid = close.rolling(w).mean()
    std = close.rolling(w).std()
    upper = mid + k * std
    lower = mid - k * std

    in_pos = False
    out = []
    for dt, price in close.items():
        if not in_pos:
            if pd.notna(lower.loc[dt]) and price <= lower.loc[dt]:
                in_pos = True
        else:
            if pd.notna(mid.loc[dt]) and price >= mid.loc[dt]:
                in_pos = False
        out.append(1.0 if in_pos else 0.0)
    return _weights_from_signal(close, pd.Series(out, index=close.index))


def momentum(close: pd.Series, lookback: int = 20) -> pd.DataFrame:
    """动量：过去 lookback 根涨幅为正则持多。"""
    lb = max(1, int(lookback))
    signal = (close > close.shift(lb)).astype(float)
    return _weights_from_signal(close, signal)


STRATEGY_FUNCS = {
    "dual_ma": dual_ma,
    "macd": macd,
    "bollinger": bollinger,
    "momentum": momentum,
}


def build_weights(strategy: str, close: pd.Series, fast: int, slow: int) -> pd.DataFrame:
    """统一入口：把前端的 fast/slow 映射到各策略所需的参数。"""
    if strategy == "dual_ma":
        return dual_ma(close, fast=fast, slow=slow)
    if strategy == "macd":
        # fast/slow 作为长短 EMA 周期（默认 12/26）
        return macd(close, fast=fast or 12, slow=slow or 26)
    if strategy == "bollinger":
        return bollinger(close, window=fast or 20)
    if strategy == "momentum":
        return momentum(close, lookback=fast or 20)
    raise ValueError(f"未知策略：{strategy}，可选 {list(STRATEGY_FUNCS)}")
