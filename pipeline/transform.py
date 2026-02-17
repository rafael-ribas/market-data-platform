import math
import logging
from collections import defaultdict
from typing import List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.session import engine, SessionLocal
from db.models import Price, AssetMetric

logger = logging.getLogger("pipeline.transform")

ASSET_METRICS_T = AssetMetric.__table__


def compute_metrics(window: int = 30) -> int:
    session = SessionLocal()

    prices = session.execute(
        select(Price).order_by(Price.asset_id, Price.date)
    ).scalars().all()

    session.close()

    prices_by_asset = defaultdict(list)
    for p in prices:
        prices_by_asset[p.asset_id].append(p)

    rows: List[dict] = []

    for asset_id, asset_prices in prices_by_asset.items():
        # Need window+1 prices to compute window daily returns
        if len(asset_prices) < window + 1:
            logger.warning(
                f"Skipping asset_id={asset_id}: only {len(asset_prices)} price points"
            )
            continue

        returns: List[float] = []

        for i in range(1, len(asset_prices)):
            prev = float(asset_prices[i - 1].price)
            curr = float(asset_prices[i].price)

            if prev <= 0 or curr <= 0:
                continue

            daily_return = (curr / prev) - 1
            returns.append(daily_return)

            if i >= window:
                window_returns = returns[-window:]
                mean = sum(window_returns) / window
                variance = sum((r - mean) ** 2 for r in window_returns) / window
                volatility = math.sqrt(variance)

                base_price = float(asset_prices[i - window].price)
                cumulative = (curr / base_price) - 1

                rows.append(
                    {
                        "asset_id": asset_id,
                        "date": asset_prices[i].date,
                        "daily_return": daily_return,
                        "cumulative_return_30d": cumulative,
                        "volatility_30d": volatility,
                    }
                )

    if not rows:
        return 0

    # Bulk UPSERT to stay idempotent with unique (asset_id, date)
    with engine.begin() as conn:
        stmt = pg_insert(ASSET_METRICS_T).values(rows)

        stmt = stmt.on_conflict_do_update(
            index_elements=[ASSET_METRICS_T.c.asset_id, ASSET_METRICS_T.c.date],
            set_={
                "daily_return": stmt.excluded.daily_return,
                "cumulative_return_30d": stmt.excluded.cumulative_return_30d,
                "volatility_30d": stmt.excluded.volatility_30d,
            },
        ).returning(ASSET_METRICS_T.c.id)

        touched = conn.execute(stmt).fetchall()

    return len(touched)
