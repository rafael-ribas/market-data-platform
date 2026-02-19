import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Set
import json
from pathlib import Path
import random

import requests
import requests_cache

# HTTP cache (1h) to reduce calls during development
requests_cache.install_cache("cg_cache", expire_after=3600)

BASE_URL = "https://api.coingecko.com/api/v3"

logger = logging.getLogger("pipeline.extract")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# --- local cache / resume ---------------------------------------------------

RAW_DIR = Path("data/raw/coingecko")
STATE_DIR = Path("data/state")
STATE_FILE = STATE_DIR / "extract_progress.json"


def _ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict:
    _ensure_dirs()
    if STATE_FILE.exists():
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_coin_ids": [], "meta": {}}


def _save_state(state: dict) -> None:
    _ensure_dirs()
    tmp = STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_FILE)


def _cache_path(coin_id: str, days: int, vs_currency: str) -> Path:
    safe = f"{coin_id}_{vs_currency}_{days}d".replace("/", "_")
    return RAW_DIR / f"{safe}.json"


def _load_cache(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(path: Path, payload: dict) -> None:
    _ensure_dirs()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    tmp.replace(path)


# --- helpers ----------------------------------------------------------------


def _is_valid_symbol(symbol: str) -> bool:
    """
    Accept only standard crypto symbols:
    - Uppercase
    - 2 to 10 characters
    - Letters and numbers only
    (filters out things like FIGR_HELOC)
    """
    return bool(re.fullmatch(r"[A-Z0-9]{2,10}", symbol))


def _get_json(
    url: str, params: Optional[dict] = None, timeout: int = 20, retries: int = 6
) -> dict:
    """
    GET JSON with robust retry/backoff.
    - Respects Retry-After on 429
    - Exponential backoff with jitter on transient errors
    """
    last_err = None

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None and retry_after.isdigit():
                    wait = int(retry_after)
                else:
                    wait = min(60, int((2**attempt) + random.random()))
                logger.warning(
                    f"HTTP 429 (rate limit). Retry {attempt}/{retries} in {wait}s"
                )
                time.sleep(wait)
                continue

            if resp.status_code in (500, 502, 503, 504):
                wait = min(60, int((2**attempt) + random.random()))
                logger.warning(
                    f"HTTP {resp.status_code}. Retry {attempt}/{retries} in {wait}s"
                )
                time.sleep(wait)
                continue

            resp.raise_for_status()

        except Exception as e:
            last_err = e
            wait = min(60, int((2**attempt) + random.random()))
            logger.warning(f"Request error: {e}. Retry {attempt}/{retries} in {wait}s")
            time.sleep(wait)

    raise RuntimeError(
        f"Failed to GET {url} after {retries} retries. Last error: {last_err}"
    )


def _ms_to_utc_date(ms: int) -> str:
    """Convert epoch milliseconds to YYYY-MM-DD (UTC)."""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.date().isoformat()


def fetch_stablecoin_ids() -> set:
    """
    Pulls the 'stablecoins' category to exclude them from the Top-N selection.
    """
    url = f"{BASE_URL}/coins/markets"
    params = {
        "vs_currency": "usd",
        "category": "stablecoins",
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": False,
    }

    data = _get_json(url, params=params)
    return {coin["id"] for coin in data}


# --- public API -------------------------------------------------------------


def fetch_top_assets(limit: int = 20, vs_currency: str = "usd") -> List[dict]:
    """
    Fetch top assets by market cap, excluding:
      - stablecoins (by category lookup)
      - irregular symbols (e.g., FIGR_HELOC)
    Keeps paging until it collects `limit` valid assets.
    """
    stable_ids = fetch_stablecoin_ids()

    collected: List[dict] = []
    page = 1
    per_page = 100  # 50/100 (safer w/ rate-limit)

    logger.info(f"Fetching top {limit} NON-stable assets (vs={vs_currency})...")

    while len(collected) < limit:
        url = f"{BASE_URL}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": False,
        }

        data = _get_json(url, params=params)
        if not data:
            break

        for a in data:
            if len(collected) >= limit:
                break

            coin_id = a["id"]
            symbol = a["symbol"].upper()

            if coin_id in stable_ids:
                continue

            if not _is_valid_symbol(symbol):
                logger.info(f"Skipping invalid symbol: {symbol} ({coin_id})")
                continue

            collected.append(
                {
                    "id": coin_id,
                    "symbol": symbol,
                    "name": a["name"],
                    "source": "coingecko",
                }
            )

        logger.info(f"Page {page}: collected {len(collected)}/{limit}")
        page += 1

    logger.info(f"Fetched {len(collected)} NON-stable assets.")
    return collected[:limit]


def fetch_market_chart(coin_id: str, days: int = 30, vs_currency: str = "usd") -> dict:
    """
    /coins/{id}/market_chart returns arrays of [timestamp_ms, value]:
      - prices
      - market_caps
      - total_volumes
    """
    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}
    return _get_json(url, params=params)


def extract_top_assets_with_history(
    limit: int = 20,
    days: int = 30,
    vs_currency: str = "usd",
    throttle_seconds: float = 5,
    use_cache: bool = True,
) -> Tuple[List[dict], List[dict]]:
    """
    Resume-friendly extraction:
    - Saves each coin's market_chart JSON in data/raw/coingecko/
    - Keeps progress state in data/state/extract_progress.json

    Returns (assets, prices) normalized for loading.

    assets: [{symbol, name, source}]
    prices: [{symbol, date, price, market_cap, volume}]
    """
    _ensure_dirs()

    assets_raw = fetch_top_assets(limit=limit, vs_currency=vs_currency)

    state = _load_state()
    completed: Set[str] = set(state.get("completed_coin_ids", []))

    all_prices: List[dict] = []

    processed = 0

    for asset in assets_raw:
        coin_id = asset["id"]
        symbol = asset["symbol"]  # already upper
        #name = asset["name"]

        # (double safety) ensure symbol ok
        if not _is_valid_symbol(symbol):
            logger.info(
                f"Skipping invalid symbol at history stage: {symbol} ({coin_id})"
            )
            continue

        processed += 1

        cache_file = _cache_path(coin_id=coin_id, days=days, vs_currency=vs_currency)

        if use_cache and cache_file.exists():
            logger.info(f"[{processed}/{limit}] Using cache for {symbol} ({coin_id})")
            chart = _load_cache(cache_file)
        else:
            logger.info(
                f"[{processed}/{limit}] Fetching {days}d history for {symbol} ({coin_id})..."
            )
            chart = fetch_market_chart(
                coin_id=coin_id, days=days, vs_currency=vs_currency
            )
            if use_cache:
                _save_cache(cache_file, chart)

        prices_by_date = {
            _ms_to_utc_date(ts): val for ts, val in chart.get("prices", [])
        }
        mcap_by_date = {
            _ms_to_utc_date(ts): val for ts, val in chart.get("market_caps", [])
        }
        vol_by_date = {
            _ms_to_utc_date(ts): val for ts, val in chart.get("total_volumes", [])
        }

        dates = sorted(set(prices_by_date) | set(mcap_by_date) | set(vol_by_date))

        for d in dates:
            if d not in prices_by_date:
                continue

            all_prices.append(
                {
                    "symbol": symbol,
                    "date": d,
                    "price": float(prices_by_date.get(d)),
                    "market_cap": float(mcap_by_date.get(d))
                    if d in mcap_by_date
                    else None,
                    "volume": float(vol_by_date.get(d)) if d in vol_by_date else None,
                }
            )

        if coin_id not in completed:
            completed.add(coin_id)
            state["completed_coin_ids"] = sorted(completed)
            state["meta"] = {
                "limit": limit,
                "days": days,
                "vs_currency": vs_currency,
                "last_updated_utc": datetime.now(timezone.utc).isoformat(),
            }
            _save_state(state)

        if processed >= limit:
            break

        time.sleep(throttle_seconds)

    assets_out = [
        {"symbol": a["symbol"], "name": a["name"], "source": a["source"]}
        for a in assets_raw
    ]

    logger.info(f"Done. assets={len(assets_out)} price_rows={len(all_prices)}")
    logger.info(f"Progress saved in: {STATE_FILE.as_posix()}")
    return assets_out, all_prices


if __name__ == "__main__":
    assets, prices = extract_top_assets_with_history(limit=20, days=30)
    print(f"assets={len(assets)} prices={len(prices)}")
    print("sample asset:", assets[0])
    print("sample price row:", prices[0])
