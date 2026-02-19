import os
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

ROOT = Path(__file__).resolve().parents[1]  # pasta raiz do repo
sys.path.insert(0, str(ROOT))

from db.base import Base
from db.session import engine, SessionLocal
from db.models import Asset, Price, AssetMetric
from sqlalchemy.orm import Session
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # 2) cria as tabelas no SQLite em memória
    Base.metadata.create_all(bind=engine)

    # 3) seed mínimo
    db = SessionLocal()
    try:
        btc = Asset(symbol="BTC", name="Bitcoin", source="coingecko")
        eth = Asset(symbol="ETH", name="Ethereum", source="coingecko")
        db.add_all([btc, eth])
        db.commit()

        # precisa refresh pra ter IDs
        db.refresh(btc)
        db.refresh(eth)

        # preços diários (10 dias)
        start = date(2025, 1, 1)
        for i in range(10):
            d = start + timedelta(days=i)
            db.add(Price(asset_id=btc.id, date=d, price=40000 + i * 100, market_cap=None, volume=None))
            db.add(Price(asset_id=eth.id, date=d, price=2000 + i * 10, market_cap=None, volume=None))

            # métricas compatíveis com seus endpoints
            db.add(
                AssetMetric(
                    asset_id=btc.id,
                    date=d,
                    daily_return=0.001,
                    cumulative_return_30d=0.05,
                    volatility_30d=0.20,
                )
            )
            db.add(
                AssetMetric(
                    asset_id=eth.id,
                    date=d,
                    daily_return=0.002,
                    cumulative_return_30d=0.06,
                    volatility_30d=0.25,
                )
            )

        db.commit()
        yield
    finally:
        db.close()

@pytest.fixture
def db_session():
    """
    Provides a transactional scope around a series of operations.
    Rolls back after each test to keep isolation.
    """
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    return TestClient(app)

