from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import Optional


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="coingecko")

    prices = relationship("Price", back_populates="asset", cascade="all, delete-orphan")


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    date: Mapped["Date"] = mapped_column(Date, nullable=False)

    price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    market_cap: Mapped[Optional[float]] = mapped_column(Numeric(24, 2), nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Numeric(24, 2), nullable=True)


    asset = relationship("Asset", back_populates="prices")

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_prices_asset_date"),
        Index("ix_prices_asset_date", "asset_id", "date"),
    )
