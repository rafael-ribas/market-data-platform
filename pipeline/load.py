import logging
from datetime import date
from typing import Dict, List, Tuple, Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.session import engine
from db.models import Asset, Price

logger = logging.getLogger("pipeline.load")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

ASSETS_T = Asset.__table__
PRICES_T = Price.__table__


def _chunks(items: List[dict], size: int) -> Iterable[List[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_assets(conn, assets: List[dict]) -> int:
    if not assets:
        return 0

    stmt = pg_insert(ASSETS_T).values(assets)

    stmt = stmt.on_conflict_do_update(
        index_elements=[ASSETS_T.c.symbol],
        set_={
            "name": stmt.excluded.name,
            "source": stmt.excluded.source,
        },
    ).returning(ASSETS_T.c.id)

    rows = conn.execute(stmt).fetchall()
    return len(rows)

def fetch_asset_ids(conn, symbols: List[str]) -> Dict[str, int]:
    """
    Returns {symbol: id} for given symbols
    """
    if not symbols:
        return {}

    q = select(ASSETS_T.c.symbol, ASSETS_T.c.id).where(ASSETS_T.c.symbol.in_(symbols))
    rows = conn.execute(q).fetchall()
    return {r.symbol: r.id for r in rows}


def _normalize_price_rows(prices: List[dict], symbol_to_id: Dict[str, int]) -> List[dict]:
    """
    prices: [{symbol, date(YYYY-MM-DD), price, market_cap, volume}]
    -> rows: [{asset_id, date(date obj), price, market_cap, volume}]
    """
    out = []
    for p in prices:
        sym = p["symbol"]
        asset_id = symbol_to_id.get(sym)
        if not asset_id:
            continue  # should not happen, but keep pipeline robust

        # date in extract is 'YYYY-MM-DD' string
        d = p["date"]
        d_obj = d if isinstance(d, date) else date.fromisoformat(d)

        out.append(
            {
                "asset_id": asset_id,
                "date": d_obj,
                "price": p["price"],
                "market_cap": p.get("market_cap"),
                "volume": p.get("volume"),
            }
        )
    return out


def upsert_prices(conn, price_rows: List[dict]) -> int:
    if not price_rows:
        return 0

    stmt = pg_insert(PRICES_T).values(price_rows)

    stmt = stmt.on_conflict_do_update(
        constraint="uq_prices_asset_date",
        set_={
            "price": stmt.excluded.price,
            "market_cap": stmt.excluded.market_cap,
            "volume": stmt.excluded.volume,
        },
    ).returning(PRICES_T.c.id)

    rows = conn.execute(stmt).fetchall()
    return len(rows)

def load_assets_and_prices(
    assets: List[dict],
    prices: List[dict],
    chunk_size_prices: int = 1000,
) -> Tuple[int, int]:
    """
    Full load transaction:
      1) upsert assets
      2) fetch ids
      3) upsert prices (chunked)
    """
    with engine.begin() as conn:
        assets_touched = upsert_assets(conn, assets)

        symbols = [a["symbol"] for a in assets]
        symbol_to_id = fetch_asset_ids(conn, symbols)

        normalized = _normalize_price_rows(prices, symbol_to_id)

        prices_touched = 0
        for batch in _chunks(normalized, chunk_size_prices):
            prices_touched += upsert_prices(conn, batch)

    return assets_touched, prices_touched
