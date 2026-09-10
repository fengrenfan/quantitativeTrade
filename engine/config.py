"""全局配置：缓存目录、默认参数、标的池。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.getenv("QUANT_CACHE_DIR", os.path.join(BASE_DIR, "cache"))

# 回测默认区间
DEFAULT_START = "2021-01-01"
DEFAULT_END = None  # None 表示到今天

# 交易成本（万分之）
DEFAULT_COST_BPS = 10

# 默认标的池（沿用示范池）
DEFAULT_SYMBOLS = ["600519.SH", "002594.SZ", "300750.SZ", "600036.SH"]

# 支持的策略与周期
STRATEGIES = ["dual_ma", "macd", "bollinger", "momentum"]
TIMEFRAMES = ["daily", "weekly", "60min"]

# 默认策略参数
DEFAULT_FAST = 5
DEFAULT_SLOW = 20
