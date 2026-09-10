"""绩效指标：年化收益、夏普、最大回撤、卡玛、胜率、换手等。"""
import numpy as np
import pandas as pd


def annualize_return(daily_ret: pd.Series, freq: int = 252) -> float:
    cum = (1.0 + daily_ret).prod()
    n = daily_ret.shape[0]
    if n == 0:
        return float("nan")
    return float(cum ** (freq / n) - 1.0)


def annualize_vol(daily_ret: pd.Series, freq: int = 252) -> float:
    return float(daily_ret.std() * np.sqrt(freq))


def sharpe(daily_ret: pd.Series, rf: float = 0.0, freq: int = 252) -> float:
    vol = annualize_vol(daily_ret, freq)
    if not vol or vol == 0:
        return float("nan")
    er = daily_ret.mean() * freq - rf
    return float(er / vol)


def max_drawdown(nav: pd.Series) -> float:
    dd = nav / nav.cummax() - 1.0
    return float(dd.min())


def calmar(daily_ret: pd.Series, nav: pd.Series) -> float:
    cagr = annualize_return(daily_ret)
    mdd = max_drawdown(nav)
    if not mdd or mdd == 0:
        return float("nan")
    return float(cagr / abs(mdd))


def _clean(x: float) -> float | None:
    if x is None:
        return None
    try:
        if np.isnan(x) or np.isinf(x):
            return None
    except TypeError:
        return None
    return round(float(x), 4)


def summary(bt: pd.DataFrame) -> dict:
    daily = bt["port_ret"]
    nav = bt["nav"]
    total_return = float(nav.iloc[-1] - 1.0) if len(nav) else float("nan")
    bench_total = float(bt["benchmark_nav"].iloc[-1] - 1.0) if len(bt) else float("nan")
    return {
        "annualReturn": _clean(annualize_return(daily)),
        "annualVol": _clean(annualize_vol(daily)),
        "sharpe": _clean(sharpe(daily)),
        "maxDrawdown": _clean(max_drawdown(nav)),
        "calmar": _clean(calmar(daily, nav)),
        "winRate": _clean(float((daily > 0).mean())),
        "avgTurnover": _clean(float(bt["turnover"].mean())),
        "totalReturn": _clean(total_return),
        "benchmarkReturn": _clean(bench_total),
        "bars": int(len(bt)),
    }
