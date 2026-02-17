from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text

from db.session import engine

# Output directory (relative to project root)
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _read_df(query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def export_rankings(as_of_date: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Exports 30d cumulative return ranking and 30d volatility ranking for the latest (or given) date."""
    if as_of_date is None:
        as_of_date = _read_df("select max(date) as d from asset_metrics")["d"].iloc[0]
        as_of_date = str(as_of_date)

    df_ret = _read_df(f"""
        select a.symbol, m.date, m.cumulative_return_30d, m.volatility_30d
        from asset_metrics m
        join assets a on a.id = m.asset_id
        where m.date = '{as_of_date}'
        order by m.cumulative_return_30d desc
    """)
    df_ret.to_csv(OUT_DIR / "ranking_returns_30d.csv", index=False)

    df_vol = df_ret.sort_values("volatility_30d", ascending=False)[
        ["symbol", "date", "volatility_30d", "cumulative_return_30d"]
    ]
    df_vol.to_csv(OUT_DIR / "ranking_volatility_30d.csv", index=False)

    return df_ret, df_vol


def export_correlation() -> pd.DataFrame:
    """Builds correlation matrix from daily returns (asset_metrics.daily_return) and saves CSV + heatmap."""
    df = _read_df("""
        select a.symbol, m.date, m.daily_return
        from asset_metrics m
        join assets a on a.id = m.asset_id
        order by m.date, a.symbol
    """)

    pivot = df.pivot_table(index="date", columns="symbol", values="daily_return")
    corr = pivot.corr()
    corr.to_csv(OUT_DIR / "correlation_daily_returns.csv")

    plt.figure(figsize=(10, 8))
    plt.imshow(corr.values, aspect="auto")
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.index)), corr.index)
    plt.title("Correlation — Daily Returns")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(OUT_DIR / "correlation_heatmap.png", dpi=200)
    plt.close()

    return corr


def export_top10_price_chart(days: int = 60, top_n: int = 10) -> Path:
    """Normalized price performance (base=100) for top N assets (by 30d return)."""
    df_ret, _ = export_rankings()
    top_symbols = (
        df_ret.sort_values("cumulative_return_30d", ascending=False)["symbol"]
        .head(top_n)
        .tolist()
    )
    if not top_symbols:
        raise RuntimeError("No symbols found for top price chart.")

    symbols_in = ",".join([f"'{s}'" for s in top_symbols])

    df_prices = _read_df(f"""
        select a.symbol, p.date, p.price
        from prices p
        join assets a on a.id = p.asset_id
        where a.symbol in ({symbols_in})
        order by p.date asc
    """)

    df_prices["date"] = pd.to_datetime(df_prices["date"])
    cutoff = df_prices["date"].max() - pd.Timedelta(days=days)
    df_prices = df_prices[df_prices["date"] >= cutoff].copy()

    pivot = df_prices.pivot_table(index="date", columns="symbol", values="price")
    pivot = pivot.dropna(axis=1, how="all").ffill().dropna(how="all")

    norm = pivot / pivot.iloc[0] * 100.0

    plt.figure(figsize=(12, 6))
    plt.plot(norm.index, norm.values)
    plt.title(f"Top {top_n} — Price Performance (Normalized, base=100)")
    plt.xlabel("Date")
    plt.ylabel("Normalized Price (base=100)")
    plt.legend(norm.columns, ncol=2, fontsize=8)
    plt.tight_layout()

    out = OUT_DIR / "top10_price_normalized.png"
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def export_risk_return_scatter(as_of_date: Optional[str] = None) -> Path:
    """Scatter plot: X=30d volatility, Y=30d cumulative return."""
    if as_of_date is None:
        as_of_date = _read_df("select max(date) as d from asset_metrics")["d"].iloc[0]
        as_of_date = str(as_of_date)

    df = _read_df(f"""
        select a.symbol, m.date, m.cumulative_return_30d, m.volatility_30d
        from asset_metrics m
        join assets a on a.id = m.asset_id
        where m.date = '{as_of_date}'
        order by a.symbol
    """)

    plt.figure(figsize=(10, 6))
    plt.scatter(df["volatility_30d"], df["cumulative_return_30d"])
    for _, r in df.iterrows():
        plt.annotate(
            r["symbol"],
            (r["volatility_30d"], r["cumulative_return_30d"]),
            fontsize=8,
        )

    plt.title("Risk vs Return (30d)")
    plt.xlabel("Volatility (30d)")
    plt.ylabel("Cumulative Return (30d)")
    plt.axhline(0, linewidth=1)
    plt.axvline(df["volatility_30d"].median(), linewidth=1)
    plt.tight_layout()

    out = OUT_DIR / "risk_return_scatter.png"
    plt.savefig(out, dpi=200)
    plt.close()

    df.to_csv(OUT_DIR / "risk_return_table.csv", index=False)
    return out


def export_drawdown(symbol: str = "BTC", days: int = 60) -> Optional[Path]:
    """Drawdown series for an asset over the last N days."""
    df = _read_df(f"""
        select a.symbol, p.date, p.price
        from prices p
        join assets a on a.id = p.asset_id
        where a.symbol = '{symbol}'
        order by p.date asc
    """)
    if df.empty:
        return None

    df["date"] = pd.to_datetime(df["date"])
    cutoff = df["date"].max() - pd.Timedelta(days=days)
    df = df[df["date"] >= cutoff].copy()

    prices = df["price"].astype(float).values
    peak = np.maximum.accumulate(prices)
    dd = (prices / peak) - 1.0

    plt.figure(figsize=(12, 4))
    plt.plot(df["date"], dd)
    plt.title(f"{symbol} — Drawdown (last {days}d)")
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.axhline(0, linewidth=1)
    plt.tight_layout()

    out = OUT_DIR / f"drawdown_{symbol}.png"
    plt.savefig(out, dpi=200)
    plt.close()
    return out


def export_top_correlation_pairs(n: int = 10) -> pd.DataFrame:
    """Exports top N most correlated pairs from the correlation CSV."""
    corr_path = OUT_DIR / "correlation_daily_returns.csv"
    corr = pd.read_csv(corr_path, index_col=0)

    pairs: List[Tuple[str, str, float]] = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            val = float(corr.iloc[i, j])
            if pd.notna(val):
                pairs.append((a, b, val))

    top = sorted(pairs, key=lambda x: x[2], reverse=True)[:n]
    df_out = pd.DataFrame(top, columns=["asset_a", "asset_b", "corr"])
    df_out.to_csv(OUT_DIR / "top_correlation_pairs.csv", index=False)
    return df_out


def main():
    export_rankings()
    export_correlation()
    export_top_correlation_pairs(10)
    export_top10_price_chart(days=60, top_n=10)
    export_risk_return_scatter()
    export_drawdown("BTC", days=60)
    print(f"Saved outputs to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
