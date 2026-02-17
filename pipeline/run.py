import argparse
import logging
from datetime import datetime

from sqlalchemy import insert, update

from pipeline.extract import extract_top_assets_with_history
from pipeline.load import load_assets_and_prices
from db.session import engine
from db.models import ETLRun

logger = logging.getLogger("pipeline.run")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def run_etl(limit: int, days: int, throttle: float, chunk_prices: int):
    started_at = datetime.utcnow()

    with engine.begin() as conn:
        # create initial run record
        stmt = insert(ETLRun).values(
            started_at=started_at,
            status="RUNNING",
        ).returning(ETLRun.id)

        run_id = conn.execute(stmt).scalar()

    try:
        assets, prices = extract_top_assets_with_history(
            limit=limit,
            days=days,
            throttle_seconds=throttle,
            use_cache=True,
        )

        # -------- Data Quality Checks --------
        if not assets:
            raise ValueError("No assets extracted")

        if any(p["price"] is None or p["price"] <= 0 for p in prices):
            raise ValueError("Invalid price detected")

        assets_loaded, prices_loaded = load_assets_and_prices(
            assets, prices, chunk_size_prices=chunk_prices
        )

        finished_at = datetime.utcnow()

        with engine.begin() as conn:
            stmt = update(ETLRun).where(ETLRun.id == run_id).values(
                finished_at=finished_at,
                assets_loaded=assets_loaded,
                prices_loaded=prices_loaded,
                status="SUCCESS",
            )
            conn.execute(stmt)

        logger.info(f"ETL SUCCESS run_id={run_id}")

    except Exception as e:
        finished_at = datetime.utcnow()

        with engine.begin() as conn:
            stmt = update(ETLRun).where(ETLRun.id == run_id).values(
                finished_at=finished_at,
                status="FAILED",
            )
            conn.execute(stmt)

        logger.exception(f"ETL FAILED run_id={run_id}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Run Market Data ETL")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--throttle", type=float, default=2.5)
    parser.add_argument("--chunk-prices", type=int, default=1000)
    args = parser.parse_args()

    run_etl(
        limit=args.limit,
        days=args.days,
        throttle=args.throttle,
        chunk_prices=args.chunk_prices,
    )


if __name__ == "__main__":
    main()
