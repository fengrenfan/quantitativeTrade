"""标的注册表：全市场 A 股 + ETF + 主要指数，支持「代码 / 名称 / 拼音」模糊搜索。

构建来源：
  - A 股个股：`ak.stock_info_a_code_name()`  → ~5500 条
  - ETF     ：`ak.fund_etf_spot_em()`        → ~1600 条
  - 指  数  ：`engine.indexes.INDEXES`（静态表，见该模块说明）

拉一次全市场列表要 20 秒上下（东财接口本身就慢），所以这里的策略是：

  1. 结果落盘为 JSON 快照（`<CACHE_DIR>/symbols.json`），默认 TTL 7 天；
  2. 进程内内存缓存，搜索是纯内存扫描（微秒级），绝不会按每次键入去打网络；
  3. 应用启动时由后台线程预热，避免第一次搜索卡 20 秒；
  4. 预热没完成时先返回内置热门标的，保证搜索框永远有东西可选；
  5. 刷新失败保留旧快照 —— 绝不让一次网络抖动把一张好表清成空。
"""
from __future__ import annotations

import json
import os
import threading
import time

from . import config
from .indexes import INDEXES

try:  # 拼音搜索是加分项，缺了也不影响主流程
    from pypinyin import Style, lazy_pinyin

    _HAS_PINYIN = True
except Exception:  # pragma: no cover
    _HAS_PINYIN = False

SNAPSHOT_VERSION = 1
SNAPSHOT_TTL_SECONDS = 7 * 24 * 3600
TYPE_ORDER = {"index": 0, "stock": 1, "etf": 2}

# 网络全挂时的兜底：至少让最常用的标的能搜到、能看
_FALLBACK: list[tuple[str, str, str]] = [
    ("600519.SH", "贵州茅台", "stock"),
    ("000858.SZ", "五粮液", "stock"),
    ("300750.SZ", "宁德时代", "stock"),
    ("002594.SZ", "比亚迪", "stock"),
    ("600036.SH", "招商银行", "stock"),
    ("601318.SH", "中国平安", "stock"),
    ("000333.SZ", "美的集团", "stock"),
    ("000651.SZ", "格力电器", "stock"),
    ("601899.SH", "紫金矿业", "stock"),
    ("600900.SH", "长江电力", "stock"),
    ("002415.SZ", "海康威视", "stock"),
    ("600276.SH", "恒瑞医药", "stock"),
    ("510300.SH", "沪深300ETF", "etf"),
    ("510500.SH", "中证500ETF", "etf"),
    ("159915.SZ", "创业板ETF", "etf"),
    ("512880.SH", "证券ETF", "etf"),
    ("518880.SH", "黄金ETF", "etf"),
    ("588000.SH", "科创50ETF", "etf"),
]

_LOCK = threading.Lock()
_STATE: dict = {
    "entries": None,       # list[dict]，None 表示尚未构建
    "by_code": None,       # dict[code, entry]
    "updated_at": 0.0,
    "building": False,
    "source": "none",      # network | snapshot | fallback
}


# --------------------------------------------------------------------------- #
# 拼音
# --------------------------------------------------------------------------- #
def _pinyin_pair(name: str) -> tuple[str, str]:
    """返回 (首字母缩写, 全拼)，例如 贵州茅台 → ("gzmt", "guizhoumaotai")。"""
    if not _HAS_PINYIN or not name:
        return "", ""
    try:
        initials = "".join(lazy_pinyin(name, style=Style.FIRST_LETTER, errors="ignore")).lower()
        full = "".join(lazy_pinyin(name, errors="ignore")).lower()
        return initials, full
    except Exception:
        return "", ""


def _make_entry(code: str, name: str, kind: str, group: str | None = None) -> dict:
    initials, full = _pinyin_pair(name)
    entry = {
        "code": code,
        "name": name,
        "type": kind,
        "py": initials,
        "pyf": full,
    }
    if group:
        entry["group"] = group
    return entry


# --------------------------------------------------------------------------- #
# 交易所后缀推断
# --------------------------------------------------------------------------- #
def _stock_suffix(num: str) -> str | None:
    """6 位股票代码 → 交易所后缀；北交所（4/8 开头）当前引擎不支持，返回 None。"""
    if num.startswith(("6", "9")):
        return "SH"
    if num.startswith(("0", "2", "3")):
        return "SZ"
    return None


def _etf_suffix(num: str) -> str | None:
    if num.startswith("5"):
        return "SH"
    if num.startswith("1"):
        return "SZ"
    return None


def _pick_col(df, *candidates) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _fetch_stocks(ak) -> list[dict]:
    df = ak.stock_info_a_code_name()
    code_col = _pick_col(df, "code", "代码")
    name_col = _pick_col(df, "name", "名称")
    out: list[dict] = []
    for raw_code, raw_name in zip(df[code_col], df[name_col]):
        num = str(raw_code).strip().split(".")[0].zfill(6)
        suffix = _stock_suffix(num)
        if suffix is None:
            continue
        name = str(raw_name).strip()
        if not name or name.upper() == "NAN":
            continue
        out.append(_make_entry(f"{num}.{suffix}", name, "stock"))
    return out


def _fetch_etfs(ak) -> list[dict]:
    df = ak.fund_etf_spot_em()
    code_col = _pick_col(df, "代码", "code")
    name_col = _pick_col(df, "名称", "name")
    out: list[dict] = []
    for raw_code, raw_name in zip(df[code_col], df[name_col]):
        num = str(raw_code).strip().split(".")[0].zfill(6)
        suffix = _etf_suffix(num)
        if suffix is None:
            continue
        name = str(raw_name).strip()
        if not name or name.upper() == "NAN":
            continue
        out.append(_make_entry(f"{num}.{suffix}", name, "etf"))
    return out


def _static_entries() -> list[dict]:
    return [_make_entry(code, name, "index", group) for code, name, group in INDEXES]


def _fallback_entries() -> list[dict]:
    entries = _static_entries()
    seen = {e["code"] for e in entries}
    for code, name, kind in _FALLBACK:
        if code not in seen:
            entries.append(_make_entry(code, name, kind))
    return entries


def _build_from_network() -> list[dict]:
    """拉取全市场列表；指数用静态表。个股/ETF 任一失败不影响另一部分。"""
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"akshare 不可用：{exc}") from exc

    # 先放静态指数，保证即使个股/ETF 全挂也有可用内容
    merged: dict[str, dict] = {e["code"]: e for e in _static_entries()}
    errors: list[str] = []

    for label, fetcher in (("个股", _fetch_stocks), ("ETF", _fetch_etfs)):
        try:
            for entry in fetcher(ak):
                merged.setdefault(entry["code"], entry)
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    if len(merged) <= len(INDEXES):
        raise RuntimeError("全市场列表拉取失败：" + "；".join(errors))
    if errors:
        print(f"[symbols] 部分数据源失败（已降级）：{'；'.join(errors)}")
    return list(merged.values())


# --------------------------------------------------------------------------- #
# 快照读写
# --------------------------------------------------------------------------- #
def _snapshot_path() -> str:
    return os.path.join(config.CACHE_DIR, "symbols.json")


def _read_snapshot() -> tuple[list[dict], float] | None:
    path = _snapshot_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("version") != SNAPSHOT_VERSION:
            return None
        entries = payload.get("entries") or []
        if not entries:
            return None
        return entries, float(payload.get("updated_at") or 0.0)
    except Exception:
        return None


def _write_snapshot(entries: list[dict]) -> None:
    path = _snapshot_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(
                {"version": SNAPSHOT_VERSION, "updated_at": time.time(), "entries": entries},
                fh,
                ensure_ascii=False,
            )
        os.replace(tmp, path)
    except Exception as exc:
        print(f"[symbols] 写入快照失败：{exc}")


def _install(entries: list[dict], source: str, updated_at: float | None = None) -> None:
    _STATE["entries"] = entries
    _STATE["by_code"] = {e["code"]: e for e in entries}
    _STATE["updated_at"] = updated_at if updated_at is not None else time.time()
    _STATE["source"] = source


def _is_fresh() -> bool:
    return bool(_STATE["entries"]) and (time.time() - _STATE["updated_at"]) < SNAPSHOT_TTL_SECONDS


# 兜底表的时间戳固定为 0，这样它永远被判定为「陈旧」——
# 否则一旦先读了兜底表，_is_fresh() 就会返回 True，refresh() 直接跳过真正的构建。
_STALE_TS = 0.0


def refresh(force: bool = False) -> bool:
    """重建注册表。成功返回 True。并发调用只会有一个真正执行。"""
    if not force and _is_fresh():
        return True
    with _LOCK:
        if _STATE["building"]:
            return bool(_STATE["entries"])
        if not force and _is_fresh():
            return True
        _STATE["building"] = True
    try:
        entries = _build_from_network()
        _install(entries, "network")
        _write_snapshot(entries)
        print(f"[symbols] 标的表已刷新：{len(entries)} 条")
        return True
    except Exception as exc:
        print(f"[symbols] 刷新失败，沿用现有数据：{exc}")
        if _STATE["entries"]:
            return True
        cached = _read_snapshot()
        if cached:
            _install(cached[0], "snapshot", cached[1])
            return True
        _install(_fallback_entries(), "fallback", _STALE_TS)
        return False
    finally:
        _STATE["building"] = False


def _ensure_loaded() -> list[dict]:
    """取注册表；首次调用若内存为空，先尝试快照，再退回兜底，绝阻塞在网络上。"""
    if _STATE["entries"]:
        return _STATE["entries"]
    cached = _read_snapshot()
    if cached:
        entries, updated_at = cached
        _install(entries, "snapshot", updated_at)
        return entries
    _install(_fallback_entries(), "fallback", _STALE_TS)
    return _STATE["entries"]


def warmup(blocking: bool = False) -> None:
    """启动时调用：后台预热，避免第一次搜索卡 20 秒。"""
    def _run() -> None:
        _ensure_loaded()
        refresh()

    if blocking:
        _run()
        return
    threading.Thread(target=_run, name="symbols-warmup", daemon=True).start()


# --------------------------------------------------------------------------- #
# 查询
# --------------------------------------------------------------------------- #
def lookup(code: str) -> dict | None:
    if not code:
        return None
    _ensure_loaded()
    return (_STATE["by_code"] or {}).get(code.upper())


def _score(entry: dict, q: str) -> int | None:
    """越小越相关；None 表示不匹配。"""
    code: str = entry["code"]
    num = code.split(".")[0]
    name: str = entry["name"]
    if num == q or code.lower() == q:
        return 0
    if num.startswith(q):
        return 1
    if entry["py"] and entry["py"].startswith(q):
        return 2
    if name.lower().startswith(q):
        return 3
    if q in name.lower():
        return 4
    if entry["pyf"] and entry["pyf"].startswith(q):
        return 5
    return None


def search(q: str = "", types: set[str] | None = None, limit: int = 30) -> dict:
    """按代码 / 名称 / 拼音首字母搜索。q 为空时返回常用标的。"""
    entries = _ensure_loaded()
    limit = max(1, min(int(limit or 30), 200))
    q = (q or "").strip().lower()

    pool = [e for e in entries if not types or e["type"] in types]
    if not q:
        pool.sort(key=lambda e: (TYPE_ORDER.get(e["type"], 9), e["code"]))
        return {
            "query": "",
            "total": len(entries),
            "count": len(pool[:limit]),
            "source": _STATE["source"],
            "results": pool[:limit],
        }

    hits: list[tuple[int, int, str, dict]] = []
    for entry in pool:
        rank = _score(entry, q)
        if rank is None:
            continue
        hits.append((rank, TYPE_ORDER.get(entry["type"], 9), entry["code"], entry))
    hits.sort(key=lambda x: (x[0], x[1], x[2]))

    return {
        "query": q,
        "total": len(hits),
        "count": len(hits[:limit]),
        "source": _STATE["source"],
        "results": [h[3] for h in hits[:limit]],
    }


def stats() -> dict:
    entries = _ensure_loaded()
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    return {
        "total": len(entries),
        "byType": counts,
        "source": _STATE["source"],
        "building": _STATE["building"],
        "updatedAt": _STATE["updated_at"] or None,
        "stale": not _is_fresh(),
    }
