from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "processed"
TEMPLATE_DIR = BASE_DIR / "templates"
REPORT_DIR = BASE_DIR / "reports"


def _fmt_pct(x: float) -> str:
    try:
        return f"{x*100:.2f}%"
    except Exception:
        return "N/A"


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def _df_to_table_data(df: pd.DataFrame, max_rows: int = 15) -> list:
    df2 = df.head(max_rows).copy()
    return [list(df2.columns)] + df2.values.tolist()


def _compute_insights(df_ret: pd.DataFrame, df_vol: pd.DataFrame, corr: pd.DataFrame) -> Dict[str, Any]:
    # Expected columns:
    # df_ret: symbol, cumulative_return_30d
    # df_vol: symbol, volatility_30d
    out: Dict[str, Any] = {}

    df_ret2 = df_ret.copy()
    df_vol2 = df_vol.copy()

    if "cumulative_return_30d" in df_ret2.columns:
        df_ret2 = df_ret2.sort_values("cumulative_return_30d", ascending=False)
        out["top_returns"] = df_ret2.head(5)[["symbol", "cumulative_return_30d"]].rename(
            columns={"cumulative_return_30d": "value"}
        ).to_dict("records")
        out["bottom_returns"] = df_ret2.tail(5)[["symbol", "cumulative_return_30d"]].rename(
            columns={"cumulative_return_30d": "value"}
        ).to_dict("records")
    else:
        out["top_returns"] = []
        out["bottom_returns"] = []

    if "volatility_30d" in df_vol2.columns:
        df_vol2 = df_vol2.sort_values("volatility_30d", ascending=False)
        out["top_vol"] = df_vol2.head(5)[["symbol", "volatility_30d"]].rename(
            columns={"volatility_30d": "value"}
        ).to_dict("records")
    else:
        out["top_vol"] = []

    # Correlation pairs
    top_corr = []
    low_corr = []
    outlier = {"symbol": None, "avg_corr": None}

    if corr is not None and not corr.empty:
        # make sure diagonal ignored
        c = corr.copy()
        for i in c.index:
            if i in c.columns:
                c.loc[i, i] = float("nan")

        # Flatten
        pairs = []
        for a in c.index:
            for b in c.columns:
                if a < b:  # unique upper triangle
                    v = c.loc[a, b]
                    if pd.notna(v):
                        pairs.append((a, b, float(v)))

        pairs_sorted = sorted(pairs, key=lambda x: x[2], reverse=True)
        top_corr = [{"a": a, "b": b, "value": v} for a, b, v in pairs_sorted[:5]]
        low_corr = [{"a": a, "b": b, "value": v} for a, b, v in sorted(pairs, key=lambda x: x[2])[:5]]

        # Outlier: lowest average correlation (excluding nan)
        avg = c.mean(axis=1, skipna=True)
        if not avg.empty:
            sym = avg.idxmin()
            outlier = {"symbol": sym, "avg_corr": float(avg.loc[sym]) if pd.notna(avg.loc[sym]) else None}

    out["top_corr"] = top_corr
    out["low_corr"] = low_corr
    out["outlier"] = outlier

    return out


def generate_html_report(df_returns: pd.DataFrame, df_vol: pd.DataFrame, insights: Dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html.j2")

    def rel_from_reports(path: Path) -> str:
        # Make paths work when opening reports/market_report.html via file:// on Windows
        rel = Path(os.path.relpath(path, start=REPORT_DIR))
        return rel.as_posix()

    df_pairs = _safe_read_csv(DATA_DIR / "top_correlation_pairs.csv")

    html = template.render(
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        returns_table=df_returns.to_html(index=False, float_format="%.6f"),
        volatility_table=df_vol.to_html(index=False, float_format="%.6f"),
        top_corr_pairs_table=(df_pairs.to_html(index=False, float_format="%.4f") if not df_pairs.empty else "<p class='muted'>N/A</p>"),

        correlation_image=(rel_from_reports(DATA_DIR / "correlation_heatmap.png") if (DATA_DIR / "correlation_heatmap.png").exists() else None),
        top10_price_image=(rel_from_reports(DATA_DIR / "top10_price_normalized.png") if (DATA_DIR / "top10_price_normalized.png").exists() else None),
        risk_return_image=(rel_from_reports(DATA_DIR / "risk_return_scatter.png") if (DATA_DIR / "risk_return_scatter.png").exists() else None),
        drawdown_btc_image=(rel_from_reports(DATA_DIR / "drawdown_BTC.png") if (DATA_DIR / "drawdown_BTC.png").exists() else None),

        insights=insights,
    )

    out = REPORT_DIR / "market_report.html"
    out.write_text(html, encoding="utf-8")
    return out


def generate_pdf_report(
    df_returns: pd.DataFrame,
    df_vol: pd.DataFrame,
    insights: Dict[str, Any],
) -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    pdf_path = REPORT_DIR / "market_report.pdf"

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Market Data Platform — Crypto Analytics Report", styles["Title"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    story.append(Spacer(1, 14))

    # Insights
    story.append(Paragraph("Automatic Insights", styles["Heading2"]))
    story.append(Spacer(1, 6))

    def bullet(txt: str) -> Paragraph:
        return Paragraph(f"• {txt}", styles["Normal"])

    top_ret = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights.get("top_returns", [])]) or "N/A"
    bottom_ret = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights.get("bottom_returns", [])]) or "N/A"
    top_vol = ", ".join([f"{x['symbol']} ({_fmt_pct(x['value'])})" for x in insights.get("top_vol", [])]) or "N/A"

    story.append(bullet(f"Top 5 cumulative returns (30d): {top_ret}"))
    story.append(Spacer(1, 3))
    story.append(bullet(f"Bottom 5 cumulative returns (30d): {bottom_ret}"))
    story.append(Spacer(1, 3))
    story.append(bullet(f"Top 5 volatility (30d): {top_vol}"))
    story.append(Spacer(1, 8))

    top_pairs = ", ".join([f"{p['a']}–{p['b']} ({p['value']:.2f})" for p in insights.get("top_corr", [])]) or "N/A"
    low_pairs = ", ".join([f"{p['a']}–{p['b']} ({p['value']:.2f})" for p in insights.get("low_corr", [])]) or "N/A"
    story.append(bullet(f"Most correlated daily-return pairs: {top_pairs}"))
    story.append(Spacer(1, 3))
    story.append(bullet(f"Least correlated daily-return pairs: {low_pairs}"))
    story.append(Spacer(1, 3))

    out = insights.get("outlier") or {}
    if out.get("symbol"):
        if out.get("avg_corr") is not None:
            story.append(bullet(f"Outlier (lowest average correlation): {out['symbol']} (avg corr {out['avg_corr']:.2f})"))
        else:
            story.append(bullet(f"Outlier (lowest average correlation): {out['symbol']}"))
    story.append(PageBreak())

    # Charts pages
    chart_specs = [
        ("Top 10 Price Performance (Normalized)", DATA_DIR / "top10_price_normalized.png", 520, 320),
        ("Risk vs Return (30d)", DATA_DIR / "risk_return_scatter.png", 520, 320),
        ("BTC Drawdown (60d)", DATA_DIR / "drawdown_BTC.png", 520, 320),
        ("Correlation — Daily Returns", DATA_DIR / "correlation_heatmap.png", 520, 400),
    ]

    for i, (title, path, w, h) in enumerate(chart_specs):
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(Spacer(1, 10))
        if path.exists():
            story.append(RLImage(str(path), width=w, height=h))
        else:
            story.append(Paragraph(f"Missing image: {path}", styles["Normal"]))
        if i != len(chart_specs) - 1:
            story.append(PageBreak())

    story.append(PageBreak())

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
    story.append(Spacer(1, 16))

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

    story.append(Spacer(1, 18))
    story.append(Paragraph("Data Source: CoinGecko API | Engineered by Rafael Ribas", styles["Normal"]))

    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        rightMargin=32, leftMargin=32, topMargin=32, bottomMargin=32
    )
    doc.build(story)
    return pdf_path


def main():
    REPORT_DIR.mkdir(exist_ok=True)

    df_ret = pd.read_csv(DATA_DIR / "ranking_returns_30d.csv")
    df_vol = pd.read_csv(DATA_DIR / "ranking_volatility_30d.csv")
    df_corr = pd.read_csv(DATA_DIR / "correlation_daily_returns.csv", index_col=0)

    insights = _compute_insights(df_ret, df_vol, df_corr)

    html_path = generate_html_report(df_ret, df_vol, insights)
    print(f"HTML report saved to: {html_path.resolve()}")

    pdf_path = generate_pdf_report(df_ret, df_vol, insights)
    print(f"PDF report saved to: {pdf_path.resolve()}")


if __name__ == "__main__":
    main()
