"""
Prices router (Python 3.9 + Pydantic v1 compatible)

Endpoints:
- GET /prices/{symbol}?start=YYYY-MM-DD&end=YYYY-MM-DD
"""

from datetime import date as Date
from typing import Iterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Asset, Price

router = APIRouter(prefix="/prices", tags=["prices"])


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PriceOut(BaseModel):
    symbol: str = Field(..., description="Asset symbol (e.g., BTC)")
    date: Date = Field(..., description="Price reference date (UTC)")
    price: float
    market_cap: Optional[float] = None
    volume: Optional[float] = None

    class Config:
        orm_mode = True


@router.get("/{symbol}", response_model=List[PriceOut])
def get_prices(
    symbol: str,
    start: Optional[Date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[Date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(
        400, ge=1, le=2000, description="Max rows returned (safety cap)"
    ),
    db: Session = Depends(get_db),
) -> List[PriceOut]:
    sym = symbol.upper()

    asset = db.execute(select(Asset).where(Asset.symbol == sym)).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {sym}")

    # Default window: last 30 days available in DB for this asset
    if start is None or end is None:
        max_date = db.execute(
            select(func.max(Price.date)).where(Price.asset_id == asset.id)
        ).scalar_one()
        if max_date is None:
            return []
        if end is None:
            end = max_date
        if start is None:
            start = end.fromordinal(end.toordinal() - 30)

    if start > end:
        raise HTTPException(status_code=422, detail="`start` must be <= `end`")

    q = (
        select(Price.date, Price.price, Price.market_cap, Price.volume)
        .where(Price.asset_id == asset.id)
        .where(Price.date >= start)
        .where(Price.date <= end)
        .order_by(Price.date.asc())
        .limit(limit)
    )

    rows = db.execute(q).all()
    out: List[PriceOut] = []
    for d, p, mc, vol in rows:
        out.append(
            PriceOut(
                symbol=asset.symbol,
                date=d,
                price=float(p),
                market_cap=float(mc) if mc is not None else None,
                volume=float(vol) if vol is not None else None,
            )
        )
    return out
