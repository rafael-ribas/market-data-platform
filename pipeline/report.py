from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


DATA_DIR = Path("data/processed")
REPORT_DIR = Path("reports")
TEMPLATE_DIR = Path("templates")

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _fmt_pct(x: float) -> str:
    return f"{x*100:.2f}%"


def _compute_insights(
    df_returns: pd.DataFrame,
    df_vol: pd.DataFrame,
    corr: pd.DataFrame,
) -> Dict:
    # Normaliza colunas esperadas
    # df_returns: symbol, date, cumulative_return_30d, volatility_30d
    # df_vol: symbol, date, volatility_30d, cumulative_return_30d
    df_returns = df_returns.copy()
    df_vol = df_vol.copy()

    # Top/Bottom returns
    top_returns = df_returns.sort_values("cumulative_return_30d", ascending=False).head(5)
    bottom_returns = df_returns.sort_values("cumulative_return_30d", ascending=True).head(5)

    # Top vol (risk)
    top_vol = df_vol.sort_values("volatility_30d", ascending=False).head(5)

    # Correlation pairs (upper triangle)
    pairs: List[Tuple[str, str, float]] = []
    cols = list(corr.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            val = float(corr.iloc[i, j])
            if pd.notna(val):
                pairs.append((a, b, val))
    pairs_sorted = sorted(pairs, key=lambda t: t[2], reverse=True)

    top_corr = pairs_sorted[:5]
    low_corr = sorted(pairs_sorted, key=lambda t: t[2])[:5]

    # Outlier: menor correlação média com o resto
    corr_mean = corr.copy()
    for c in corr_mean.columns:
        corr_mean.loc[c, c] = pd.NA
    avg_corr = corr_mean.mean(axis=1, skipna=True).sort_values()
    outlier_symbol = str(avg_corr.index[0])
    outlier_value = float(avg_corr.iloc[0]) if pd.notna(avg_corr.iloc[0]) else None

    insights = {
        "top_returns": [
            {"symbol": r["symbol"], "value": float(r["cumulative_return_30d"])}
            for _, r in top_returns.iterrows()
        ],
        "bottom_returns": [
            {"symbol": r["symbol"], "value": float(r["cumulative_return_30d"])}
            for _, r in bottom_returns.iterrows()
        ],
        "top_vol": [
            {"symbol": r["symbol"], "value": float(r["volatility_30d"])}
            for _, r in top_vol.iterrows()
        ],
        "top_corr": [{"a": a, "b": b, "value": v} for a, b, v in top_corr],
        "low_corr": [{"a": a, "b": b, "value": v} for a, b, v in low_corr],
        "outlier": {"symbol": outlier_symbol, "avg_corr": outlier_value},
    }
    return insights


def generate_html_report(df_returns: pd.DataFrame, df_vol: pd.DataFrame, insights: Dict) -> Path:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html.j2")

    html = template.render(
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        returns_table=df_returns.to_html(index=False, float_format="%.6f"),
        volatility_table=df_vol.to_html(index=False, float_format="%.6f"),
        correlation_image="../data/processed/correlation_heatmap.png",
        insights=insights,
    )

    output_path = REPORT_DIR / "report.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _df_to_table_data(df: pd.DataFrame, max_rows: int = 15) -> List[List[str]]:
    df2 = df.head(max_rows).copy()
    headers = list(df2.columns)
    data = [headers]
    for _, row in df2.iterrows():
        data.append([str(row[h]) for h in headers])
    return data


def generate_pdf_report(
    df_returns: pd.DataFrame,
    df_vol: pd.DataFrame,
    insights: Dict,
    correlation_img_path: Path
) -> Path:
    pdf_path = REPORT_DIR / "report.pdf"

    styles = getSampleStyleSheet()
    story = []

    title = Paragraph("Market Data Platform — Crypto Analytics Report", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 16))

    # Insights section
    story.append(Paragraph("Automatic Insights", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Build insights text
    def bullet(text: str) -> Paragraph:
        return Paragraph(f"• {text}", styles["Normal"])

    # Top returns
    top_ret = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights["top_returns"]])
    bottom_ret = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights["bottom_returns"]])
    top_vol = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights["top_vol"]])

    story.append(bullet(f"Top 5 cumulative returns (30d): {top_ret}"))
    story.append(Spacer(1, 4))
    story.append(bullet(f"Bottom 5 cumulative returns (30d): {bottom_ret}"))
    story.append(Spacer(1, 4))
    story.append(bullet(f"Top 5 volatility (30d): {top_vol}"))
    story.append(Spacer(1, 10))

    # Correlation highlights
    top_pairs = ", ".join([f"{p['a']}–{p['b']} ({p['value']:.2f})" for p in insights["top_corr"]])
    low_pairs = ", ".join([f"{p['a']}–{p['b']} ({p['value']:.2f})" for p in insights["low_corr"]])
    story.append(bullet(f"Most correlated daily-return pairs: {top_pairs}"))
    story.append(Spacer(1, 4))
    story.append(bullet(f"Least correlated daily-return pairs: {low_pairs}"))
    story.append(Spacer(1, 4))

    out = insights["outlier"]
    if out["avg_corr"] is not None:
        story.append(bullet(f"Outlier (lowest average correlation): {out['symbol']} (avg corr {out['avg_corr']:.2f})"))
    else:
        story.append(bullet(f"Outlier (lowest average correlation): {out['symbol']}"))
    story.append(Spacer(1, 18))

    # Tables
    story.append(Paragraph("30-Day Cumulative Returns Ranking (Top 15)", styles["Heading2"]))
    story.append(Spacer(1, 8))
    t1 = Table(_df_to_table_data(df_returns.sort_values("cumulative_return_30d", ascending=False), max_rows=15))
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ]))
    story.append(t1)
    story.append(Spacer(1, 18))

    story.append(Paragraph("30-Day Volatility Ranking (Top 15)", styles["Heading2"]))
    story.append(Spacer(1, 8))
    t2 = Table(_df_to_table_data(df_vol.sort_values("volatility_30d", ascending=False), max_rows=15))
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ]))
    story.append(t2)
    story.append(PageBreak())

    # Correlation image
    story.append(Paragraph("Correlation Matrix — Daily Returns", styles["Heading2"]))
    story.append(Spacer(1, 10))
    if correlation_img_path.exists():
        img = RLImage(str(correlation_img_path), width=520, height=400)  # ajusta se quiser
        story.append(img)
    else:
        story.append(Paragraph(f"Missing image: {correlation_img_path}", styles["Normal"]))

    story.append(Spacer(1, 18))
    story.append(Paragraph("Data Source: CoinGecko API | Engineered by Rafael Ribas", styles["Normal"]))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=32)
    doc.build(story)

    return pdf_path


def main():
    returns_path = DATA_DIR / "ranking_returns_30d.csv"
    vol_path = DATA_DIR / "ranking_volatility_30d.csv"
    corr_csv_path = DATA_DIR / "correlation_daily_returns.csv"
    corr_img_path = DATA_DIR / "correlation_heatmap.png"

    if not returns_path.exists() or not vol_path.exists() or not corr_csv_path.exists():
        raise RuntimeError("Run: python -m pipeline.analytics first")

    df_returns = pd.read_csv(returns_path)
    df_vol = pd.read_csv(vol_path)
    corr = pd.read_csv(corr_csv_path, index_col=0)

    insights = _compute_insights(df_returns, df_vol, corr)

    html_path = generate_html_report(df_returns, df_vol, insights)
    pdf_path = generate_pdf_report(df_returns, df_vol, insights, corr_img_path)

    print(f"HTML report: {html_path.resolve()}")
    print(f"PDF report:  {pdf_path.resolve()}")


if __name__ == "__main__":
    main()
