"""
Metrics router (Python 3.9 + Pydantic v1 compatible)

Endpoints:
- GET /metrics/latest
- GET /metrics/{symbol}?window=30
"""

from datetime import date as Date
from typing import Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Asset, AssetMetric

router = APIRouter(prefix="/metrics", tags=["metrics"])


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MetricOut(BaseModel):
    symbol: str = Field(..., description="Asset symbol")
    date: Date = Field(..., description="Metric reference date (UTC)")
    daily_return: float
    cumulative_return_30d: float
    volatility_30d: float

    class Config:
        orm_mode = True


@router.get("/latest", response_model=List[MetricOut])
def latest_metrics(
    limit: int = Query(20, ge=1, le=250, description="Max number of assets to return"),
    as_of: Optional[Date] = Query(
        None,
        description="Optional reference date (YYYY-MM-DD). Defaults to latest in DB.",
    ),
    db: Session = Depends(get_db),
) -> List[MetricOut]:
    if as_of is None:
        as_of = db.execute(select(func.max(AssetMetric.date))).scalar_one()

    q = (
        select(
            Asset.symbol,
            AssetMetric.date,
            AssetMetric.daily_return,
            AssetMetric.cumulative_return_30d,
            AssetMetric.volatility_30d,
        )
        .join(Asset, Asset.id == AssetMetric.asset_id)
        .where(AssetMetric.date == as_of)
        .order_by(Asset.symbol)
        .limit(limit)
    )

    rows = db.execute(q).all()
    out: List[MetricOut] = []
    for r in rows:
        out.append(
            MetricOut(
                symbol=r[0],
                date=r[1],
                daily_return=float(r[2]) if r[2] is not None else 0.0,
                cumulative_return_30d=float(r[3]) if r[3] is not None else 0.0,
                volatility_30d=float(r[4]) if r[4] is not None else 0.0,
            )
        )
    return out


@router.get("/{symbol}", response_model=List[MetricOut])
def metrics_by_symbol(
    symbol: str,
    window: int = Query(30, ge=7, le=365, description="Number of days to return"),
    as_of: Optional[Date] = Query(
        None, description="Reference date (YYYY-MM-DD). Defaults to latest available."
    ),
    db: Session = Depends(get_db),
) -> List[MetricOut]:
    sym = symbol.upper()
    asset = db.execute(select(Asset).where(Asset.symbol == sym)).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {sym}")

    if as_of is None:
        as_of = db.execute(
            select(func.max(AssetMetric.date)).where(AssetMetric.asset_id == asset.id)
        ).scalar_one()

    if as_of is None:
        return []

    start = as_of.fromordinal(as_of.toordinal() - window)

    q = (
        select(
            Asset.symbol,
            AssetMetric.date,
            AssetMetric.daily_return,
            AssetMetric.cumulative_return_30d,
            AssetMetric.volatility_30d,
        )
        .join(Asset, Asset.id == AssetMetric.asset_id)
        .where(AssetMetric.asset_id == asset.id)
        .where(AssetMetric.date >= start)
        .where(AssetMetric.date <= as_of)
        .order_by(AssetMetric.date.asc())
    )

    rows = db.execute(q).all()
    out: List[MetricOut] = []
    for r in rows:
        out.append(
            MetricOut(
                symbol=r[0],
                date=r[1],
                daily_return=float(r[2]) if r[2] is not None else 0.0,
                cumulative_return_30d=float(r[3]) if r[3] is not None else 0.0,
                volatility_30d=float(r[4]) if r[4] is not None else 0.0,
            )
        )
    return out
