import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from typing import Optional

from db.session import engine

OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)



def _read_df(query: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)


def export_rankings(as_of_date: Optional[str] = None):
    # pega a última data disponível no asset_metrics (ou uma data específica)
    if as_of_date is None:
        as_of_date = _read_df("select max(date) as d from asset_metrics")["d"].iloc[0]
        as_of_date = str(as_of_date)

    # ranking retorno 30d
    df_ret = _read_df(f"""
        select a.symbol, m.date, m.cumulative_return_30d, m.volatility_30d
        from asset_metrics m
        join assets a on a.id = m.asset_id
        where m.date = '{as_of_date}'
        order by m.cumulative_return_30d desc
    """)

    df_ret.to_csv(OUT_DIR / "ranking_returns_30d.csv", index=False)

    # ranking volatilidade 30d (risco)
    df_vol = df_ret.sort_values("volatility_30d", ascending=False)[
        ["symbol", "date", "volatility_30d", "cumulative_return_30d"]
    ]
    df_vol.to_csv(OUT_DIR / "ranking_volatility_30d.csv", index=False)

    return df_ret, df_vol


def export_correlation():
    # pega retornos diários e pivota para matriz (date x symbol)
    df = _read_df("""
        select a.symbol, m.date, m.daily_return
        from asset_metrics m
        join assets a on a.id = m.asset_id
        order by m.date, a.symbol
    """)

    pivot = df.pivot_table(index="date", columns="symbol", values="daily_return")
    corr = pivot.corr()

    corr.to_csv(OUT_DIR / "correlation_daily_returns.csv")

    # heatmap simples (matplotlib puro)
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


def main():
    export_rankings()
    export_correlation()
    print(f"Saved outputs to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
