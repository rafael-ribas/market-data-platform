"""
Correlation router (Python 3.9 + Pydantic v1 compatible)

Endpoint:
- GET /correlation?asset1=BTC&asset2=ETH&window=30
Uses daily returns computed from Price series (pct change) and Pearson correlation.
"""
from datetime import date as Date
from typing import Iterator, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import Asset, Price

router = APIRouter(prefix="/correlation", tags=["correlation"])


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CorrelationOut(BaseModel):
    asset1: str
    asset2: str
    window: int = Field(..., description="Window in days (number of return points used)")
    as_of: Date
    n_points: int
    correlation: Optional[float] = Field(None, description="Pearson correlation of aligned daily returns")
    start_date: Optional[Date] = None
    end_date: Optional[Date] = None
    note: Optional[str] = None


def _fetch_price_series(
    db: Session, asset_id: int, start: Date, end: Date
) -> List[Tuple[Date, float]]:
    q = (
        select(Price.date, Price.price)
        .where(Price.asset_id == asset_id)
        .where(Price.date >= start)
        .where(Price.date <= end)
        .order_by(Price.date.asc())
    )
    rows = db.execute(q).all()
    return [(r[0], float(r[1])) for r in rows]


def _pct_returns(series: List[Tuple[Date, float]]) -> List[Tuple[Date, float]]:
    # returns aligned to "current" day: (date_t, (p_t/p_{t-1}) - 1)
    out: List[Tuple[Date, float]] = []
    for i in range(1, len(series)):
        d0, p0 = series[i - 1]
        d1, p1 = series[i]
        if p0 == 0:
            continue
        out.append((d1, (p1 / p0) - 1.0))
    return out


def _pearson(x: List[float], y: List[float]) -> Optional[float]:
    n = len(x)
    if n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denx = sum((xi - mx) ** 2 for xi in x)
    deny = sum((yi - my) ** 2 for yi in y)
    if denx <= 0 or deny <= 0:
        return None
    return num / ((denx * deny) ** 0.5)


@router.get("", response_model=CorrelationOut)
def correlation(
    asset1: str = Query(..., description="First asset symbol (e.g., BTC)"),
    asset2: str = Query(..., description="Second asset symbol (e.g., ETH)"),
    window: int = Query(30, ge=7, le=365, description="Window in days"),
    as_of: Optional[Date] = Query(None, description="Reference date (YYYY-MM-DD). Defaults to latest common date."),
    db: Session = Depends(get_db),
) -> CorrelationOut:
    a1 = asset1.upper()
    a2 = asset2.upper()
    if a1 == a2:
        raise HTTPException(status_code=422, detail="asset1 must be different from asset2")

    asset_obj1 = db.execute(select(Asset).where(Asset.symbol == a1)).scalar_one_or_none()
    asset_obj2 = db.execute(select(Asset).where(Asset.symbol == a2)).scalar_one_or_none()
    if asset_obj1 is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {a1}")
    if asset_obj2 is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {a2}")

    # choose latest common date if as_of not provided
    if as_of is None:
        max1 = db.execute(select(func.max(Price.date)).where(Price.asset_id == asset_obj1.id)).scalar_one()
        max2 = db.execute(select(func.max(Price.date)).where(Price.asset_id == asset_obj2.id)).scalar_one()
        if max1 is None or max2 is None:
            return CorrelationOut(
                asset1=a1, asset2=a2, window=window, as_of=Date.today(),
                n_points=0, correlation=None, note="No price data available for one or both assets."
            )
        as_of = min(max1, max2)

    start = as_of.fromordinal(as_of.toordinal() - (window + 1))

    s1 = _fetch_price_series(db, asset_obj1.id, start, as_of)
    s2 = _fetch_price_series(db, asset_obj2.id, start, as_of)

    r1 = _pct_returns(s1)
    r2 = _pct_returns(s2)

    # align by date intersection
    m1 = {d: v for d, v in r1}
    m2 = {d: v for d, v in r2}
    common_dates = sorted(set(m1.keys()) & set(m2.keys()))
    if len(common_dates) < 2:
        return CorrelationOut(
            asset1=a1,
            asset2=a2,
            window=window,
            as_of=as_of,
            n_points=len(common_dates),
            correlation=None,
            note="Not enough overlapping return points to compute correlation.",
        )

    # keep last `window` points if we have more
    common_dates = common_dates[-window:]
    x = [m1[d] for d in common_dates]
    y = [m2[d] for d in common_dates]
    corr = _pearson(x, y)

    return CorrelationOut(
        asset1=a1,
        asset2=a2,
        window=window,
        as_of=as_of,
        n_points=len(common_dates),
        correlation=corr,
        start_date=common_dates[0],
        end_date=common_dates[-1],
    )
