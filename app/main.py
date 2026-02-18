from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.api.routers.assets import router as assets_router
from app.api.routers.metrics import router as metrics_router
from app.api.routers.prices import router as prices_router
from app.api.routers.correlation import router as correlation_router

app = FastAPI(
    title="Market Data Platform API",
    version="0.1.0",
    description="Crypto market data platform with ETL, analytics and automated reporting.",
)

app.include_router(health_router)
app.include_router(assets_router)
app.include_router(metrics_router)
app.include_router(prices_router)
app.include_router(correlation_router)
