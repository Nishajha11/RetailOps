"""Exploratory data analysis -> charts + a printable report.

Run:  python analysis.py
Outputs PNG charts and analysis_report.md into ./reports/.

This is the "data analysis" deliverable: it documents what the data says,
independent of the live service.
"""
from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from app import analytics
from app.database import SessionLocal, init_db
from app.seed import seed

OUT = Path(__file__).resolve().parent / "reports"
OUT.mkdir(exist_ok=True)
INK, TEAL, AMBER, VIOLET = "#16202C", "#0E7C6B", "#C8761A", "#5B4B8A"


def main():
    init_db(); seed()
    db = SessionLocal()
    try:
        s = analytics.sales_frame(db)
        p = analytics.product_frame(db)
        top = analytics.top_sellers(db, 5)
        bottom = analytics.top_sellers(db, 5, ascending=True)
        abc = analytics.abc_analysis(db)
        reorder = analytics.reorder_report(db, only_alerts=True)
        segs = analytics.customer_segments(db)
        rev_ts = analytics.revenue_timeseries(db, "W")
    finally:
        db.close()

    abc_df = pd.DataFrame(abc)

    # 1. revenue over time
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ts = pd.DataFrame(rev_ts)
    ax.plot(pd.to_datetime(ts["period"]), ts["revenue"], marker="o", color=INK)
    ax.set_title("Weekly revenue"); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(OUT / "revenue_trend.png", dpi=120); plt.close(fig)

    # 2. Pareto / ABC
    fig, ax = plt.subplots(figsize=(8, 3.5))
    colors = {"A": TEAL, "B": VIOLET, "C": "#B7AE9E"}
    ax.bar(abc_df["product_name"], abc_df["revenue"],
           color=[colors[c] for c in abc_df["class"]])
    ax2 = ax.twinx()
    ax2.plot(abc_df["product_name"], abc_df["cumulative_pct"], color=AMBER, marker=".")
    ax2.axhline(80, ls="--", color=AMBER, alpha=.5)
    ax.set_title("ABC analysis (bars=revenue, line=cumulative %)")
    ax.tick_params(axis="x", rotation=70, labelsize=7)
    fig.tight_layout(); fig.savefig(OUT / "abc_pareto.png", dpi=120); plt.close(fig)

    # 3. top vs bottom
    fig, ax = plt.subplots(figsize=(8, 3.2))
    td = pd.DataFrame(top)
    ax.barh(td["product_name"][::-1], td["units_sold"][::-1], color=TEAL)
    ax.set_title("Top 5 sellers by units"); fig.tight_layout()
    fig.savefig(OUT / "top_sellers.png", dpi=120); plt.close(fig)

    # report — identical content to the live /api/analytics/report endpoint,
    # computed from the current database so the offline export never drifts.
    rdb = SessionLocal()
    try:
        report_md = analytics.build_report(rdb)
    finally:
        rdb.close()
    report_md += "\n\n_Charts: revenue_trend.png, abc_pareto.png, top_sellers.png_\n"
    (OUT / "analysis_report.md").write_text(report_md)
    print("Wrote charts + report to", OUT)


if __name__ == "__main__":
    main()
