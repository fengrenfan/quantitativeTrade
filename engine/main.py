"""命令行入口。

用法（在项目根目录 quantitativeTrade/ 下运行）：
    python -m engine.main --catalog
    python -m engine.main --symbol 600519.SH --strategy dual_ma --fast 5 --slow 20
    python -m engine.main --symbol 002594.SZ --strategy macd --timeframe weekly --full
"""
import argparse
import json

from engine.service import catalog, run_signal


def main() -> None:
    p = argparse.ArgumentParser(description="量化趋势引擎 CLI")
    p.add_argument("--symbol", default="600519.SH")
    p.add_argument("--strategy", default="dual_ma")
    p.add_argument("--timeframe", default="daily")
    p.add_argument("--fast", type=int, default=5)
    p.add_argument("--slow", type=int, default=20)
    p.add_argument("--start", default="2021-01-01")
    p.add_argument("--end", default=None)
    p.add_argument("--cost-bps", type=float, default=10.0)
    p.add_argument("--catalog", action="store_true", help="列出可用标的/策略/周期")
    p.add_argument("--full", action="store_true", help="输出完整 JSON（含 K 线/净值数组）")
    args = p.parse_args()

    if args.catalog:
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return

    res = run_signal(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        fast=args.fast,
        slow=args.slow,
        start=args.start,
        end=args.end,
        cost_bps=args.cost_bps,
    )

    if args.full:
        print(json.dumps(res, ensure_ascii=False))
        return

    # 默认只打印摘要
    m = res["metrics"]
    print(f"标的 {res['symbol']}  策略 {res['strategy']}  周期 {res['timeframe']}  参数 {res['fast']}/{res['slow']}")
    print(f"最新 {res['lastDate']}  收盘 {res['lastClose']}  当前信号：{res['signal']}")
    print("-" * 46)
    print(f"年化收益 {m['annualReturn']}  年化波动 {m['annualVol']}  夏普 {m['sharpe']}")
    print(f"最大回撤 {m['maxDrawdown']}  卡玛 {m['calmar']}  胜率 {m['winRate']}")
    print(f"区间收益 {m['totalReturn']}  基准收益 {m['benchmarkReturn']}  交易次数 {len(res['signals'])}")


if __name__ == "__main__":
    main()
