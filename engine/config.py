"""全局配置：缓存目录、默认参数、标的池。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.getenv("QUANT_CACHE_DIR", os.path.join(BASE_DIR, "cache"))

# 回测默认区间
DEFAULT_START = "2021-01-01"
DEFAULT_END = None  # None 表示到今天

# 交易成本（万分之）
DEFAULT_COST_BPS = 10

# 默认关注标的（首页下拉里的「常用」；全市场搜索见 engine/symbols.py）
# 混排个股/指数/ETF，让用户一进来就能看到三类标的都有什么表现
DEFAULT_SYMBOLS = [
    "600519.SH",   # 贵州茅台
    "300750.SZ",   # 宁德时代
    "002594.SZ",   # 比亚迪
    "600036.SH",   # 招商银行
    "000300.SH",   # 沪深300（指数）
    "000001.SH",   # 上证指数
    "510300.SH",   # 沪深300ETF
    "159915.SZ",   # 创业板ETF
]

# 支持的策略与周期
STRATEGIES = ["dual_ma", "macd", "bollinger", "momentum"]
TIMEFRAMES = ["daily", "weekly", "60min"]

# 默认策略参数
DEFAULT_FAST = 5
DEFAULT_SLOW = 20
