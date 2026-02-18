"""
Assets router.

Goal: keep OpenAPI generation stable on Python 3.9 by avoiding PEP604 unions (X | Y)
and using explicit Pydantic response models.

This module supports both Pydantic v1 and v2.
"""
from typing import Iterator, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Asset
from db.session import SessionLocal

# Robust Pydantic version detection:
# - In v2, BaseModel has .model_validate()
# - In v1, it does not (uses .from_orm())
PYDANTIC_V2: bool = hasattr(BaseModel, "model_validate")

router = APIRouter(prefix="/assets", tags=["assets"])


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AssetOut(BaseModel):
    id: int = Field(..., description="Internal asset id")
    symbol: str = Field(..., description="Ticker symbol (e.g., BTC)")
    name: str = Field(..., description="Asset name (e.g., Bitcoin)")
    source: str = Field(..., description="Data source (e.g., coingecko)")

    if PYDANTIC_V2:
        # Pydantic v2
        model_config = {"from_attributes": True}
    else:
        # Pydantic v1
        class Config:
            orm_mode = True


def to_asset_out(row: Asset) -> AssetOut:
    """Convert ORM -> Pydantic schema (works on Pydantic v1 and v2)."""
    if PYDANTIC_V2:
        # type: ignore[attr-defined] - exists only on v2
        return AssetOut.model_validate(row)  # pragma: no cover
    return AssetOut.from_orm(row)


@router.get("", response_model=List[AssetOut])
def list_assets(
    limit: int = Query(20, ge=1, le=250, description="Max number of assets to return"),
    db: Session = Depends(get_db),
) -> List[AssetOut]:
    rows = db.execute(select(Asset).order_by(Asset.id).limit(limit)).scalars().all()
    return [to_asset_out(r) for r in rows]


@router.get("/{symbol}", response_model=AssetOut)
def get_asset(symbol: str, db: Session = Depends(get_db)) -> AssetOut:
    sym = symbol.upper()
    row = db.execute(select(Asset).where(Asset.symbol == sym)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Asset not found: {sym}")
    return to_asset_out(row)
