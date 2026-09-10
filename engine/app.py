"""量化引擎 HTTP 服务（FastAPI）：供 Spring Boot 薄网关调用。

启动（在项目根目录 quantitativeTrade/ 下）：
    uvicorn engine.app:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from engine.service import catalog, run_signal

app = FastAPI(title="Quant Engine", version="0.1.0", description="A股日线趋势信号引擎")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/catalog")
def get_catalog() -> dict:
    return catalog()


@app.get("/signal")
def get_signal(
    symbol: str = Query("600519.SH"),
    strategy: str = Query("dual_ma"),
    timeframe: str = Query("daily"),
    fast: int = Query(5),
    slow: int = Query(20),
    start: str = Query("2021-01-01"),
    end: str | None = Query(None),
    cost_bps: float = Query(10.0),
) -> dict:
    try:
        return run_signal(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            fast=fast,
            slow=slow,
            start=start,
            end=end,
            cost_bps=cost_bps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"引擎计算失败：{exc}") from exc
