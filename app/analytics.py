"""Analytics engine.

Pure functions that turn the sales/product tables into decision-ready numbers.
Everything here works robustly on small data, unlike a forecast model, because
it summarises what already happened rather than extrapolating.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from .config import DEFAULT_LEAD_TIME_DAYS, LOW_STOCK_FALLBACK, SERVICE_LEVEL_Z
from .models import Customer, Expense, Invoice, Product, Sale


# --- frame builders -------------------------------------------------------
def sales_frame(db: Session, since=None) -> pd.DataFrame:
    rows = db.query(
        Sale.date, Sale.product_id, Sale.customer_id, Sale.qty, Sale.line_total
    ).all()
    df = pd.DataFrame(rows, columns=["date", "product_id", "customer_id", "qty", "line_total"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        if since is not None:
            df = df[df["date"] >= pd.Timestamp(since)]
    return df


def window_start(db: Session, period) -> Optional[pd.Timestamp]:
    """Translate a W/M/Y period into a 'since' cutoff anchored on the latest
    sale: weekly = last 7 days, monthly = last 30, yearly = last 365.
    Anything else (None / 'all') means no filter."""
    p = str(period or "").upper()
    days = {"W": 7, "M": 30, "Y": 365}.get(p)
    if not days:
        return None
    s = sales_frame(db)
    if s.empty:
        return None
    return s["date"].max() - pd.Timedelta(days=days - 1)


def product_frame(db: Session) -> pd.DataFrame:
    rows = db.query(
        Product.id, Product.name, Product.category_id, Product.cost,
        Product.mrp, Product.stock, Product.lead_time_days,
    ).all()
    return pd.DataFrame(rows, columns=[
        "product_id", "name", "category_id", "cost", "mrp", "stock", "lead_time_days"
    ])


def expense_frame(db: Session) -> pd.DataFrame:
    rows = db.query(
        Expense.id, Expense.date, Expense.category, Expense.description,
        Expense.payee, Expense.amount,
    ).all()
    df = pd.DataFrame(rows, columns=[
        "id", "date", "category", "description", "payee", "amount"
    ])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# --- KPIs -----------------------------------------------------------------
def kpis(db: Session) -> dict:
    s, p = sales_frame(db), product_frame(db)
    revenue = float(s["line_total"].sum()) if not s.empty else 0.0
    units = int(s["qty"].sum()) if not s.empty else 0
    inv_value = float((p["stock"] * p["cost"]).sum()) if not p.empty else 0.0
    span_days = (s["date"].max() - s["date"].min()).days + 1 if not s.empty else 0
    return {
        "total_revenue": round(revenue, 2),
        "units_sold": units,
        "orders": int(len(s)),
        "products": int(len(p)),
        "inventory_value_at_cost": round(inv_value, 2),
        "avg_order_value": round(revenue / len(s), 2) if len(s) else 0.0,
        "history_days": int(span_days),
        "low_stock_count": int(len(reorder_report(db, only_alerts=True))),
    }


# --- best / worst sellers -------------------------------------------------
def top_sellers(db: Session, n: int = 5, ascending: bool = False, since=None) -> list[dict]:
    s, p = sales_frame(db, since), product_frame(db)
    if s.empty:
        return []
    g = (s.groupby("product_id")
           .agg(units_sold=("qty", "sum"), revenue=("line_total", "sum"))
           .reset_index())
    g = g.merge(p[["product_id", "name"]], on="product_id", how="left")
    g = g.sort_values("units_sold", ascending=ascending).head(n)
    return [{
        "product_id": int(r.product_id), "product_name": r["name"],
        "units_sold": int(r.units_sold), "revenue": round(float(r.revenue), 2),
    } for _, r in g.iterrows()]


# --- profit & loss --------------------------------------------------------
def receivables(db: Session) -> dict:
    """Money owed to the business: unpaid/partial invoice balances, per customer.
    This is the 'To collect' figure that credit-tracking apps lead with."""
    invs = db.query(Invoice).filter(Invoice.balance_due > 0.005).all()
    names = {c.id: c.name for c in db.query(Customer).all()}
    by_cust = {}
    for inv in invs:
        by_cust.setdefault(inv.customer_id, 0.0)
        by_cust[inv.customer_id] += float(inv.balance_due or 0)
    rows = [{
        "customer_id": cid,
        "customer_name": names.get(cid, "Walk-in customer"),
        "balance_due": round(amt, 2),
    } for cid, amt in by_cust.items()]
    rows.sort(key=lambda r: r["balance_due"], reverse=True)
    return {"total_to_collect": round(sum(r["balance_due"] for r in rows), 2),
            "open_invoices": len(invs), "by_customer": rows}


def gst_collected(db: Session) -> dict:
    """Total output GST collected, split into CGST/SGST."""
    invs = db.query(Invoice).all()
    cgst = round(sum(float(i.cgst or 0) for i in invs), 2)
    sgst = round(sum(float(i.sgst or 0) for i in invs), 2)
    return {"cgst": cgst, "sgst": sgst, "total_gst": round(cgst + sgst, 2)}


def product_profitability(db: Session, since=None) -> list[dict]:
    """Per-product economics: revenue, cost of goods sold, profit and margin.

    Profit here is gross (revenue - COGS); it does not subtract shared operating
    expenses, which are business-wide and handled separately in profit_loss().
    """
    s, p = sales_frame(db, since), product_frame(db)
    if p.empty:
        return []
    costs = p.set_index("product_id")["cost"].to_dict()
    names = p.set_index("product_id")["name"].to_dict()
    if s.empty:
        agg = pd.DataFrame(columns=["product_id", "units_sold", "revenue"])
    else:
        agg = (s.groupby("product_id")
                 .agg(units_sold=("qty", "sum"), revenue=("line_total", "sum"))
                 .reset_index())
    rows = []
    for pid in p["product_id"]:
        r = agg[agg["product_id"] == pid]
        units = int(r["units_sold"].iloc[0]) if not r.empty else 0
        revenue = float(r["revenue"].iloc[0]) if not r.empty else 0.0
        cogs = units * float(costs.get(pid, 0.0))
        profit = revenue - cogs
        margin = (profit / revenue * 100) if revenue else 0.0
        rows.append({
            "product_id": int(pid), "product_name": names.get(pid, f"#{pid}"),
            "units_sold": units, "revenue": round(revenue, 2),
            "cogs": round(cogs, 2), "profit": round(profit, 2),
            "margin_pct": round(margin, 1),
        })
    rows.sort(key=lambda r: r["profit"], reverse=True)
    return rows


def profit_loss(db: Session, since=None) -> dict:
    """Business-wide P&L: revenue - COGS = gross profit, minus operating
    expenses = net profit. Reports a loss as a negative net profit so the
    dashboard can flag it.
    """
    prof = product_profitability(db, since)
    revenue = round(sum(r["revenue"] for r in prof), 2)
    cogs = round(sum(r["cogs"] for r in prof), 2)
    gross_profit = round(revenue - cogs, 2)

    exp = expense_frame(db)
    if not exp.empty and since is not None:
        exp = exp[exp["date"] >= pd.Timestamp(since)]
    total_expenses = round(float(exp["amount"].sum()), 2) if not exp.empty else 0.0
    if not exp.empty:
        by_cat = (exp.groupby("category")["amount"].sum()
                     .sort_values(ascending=False))
        expense_breakdown = [{"category": k, "amount": round(float(v), 2)}
                             for k, v in by_cat.items()]
    else:
        expense_breakdown = []

    net_profit = round(gross_profit - total_expenses, 2)
    gross_margin = round(gross_profit / revenue * 100, 1) if revenue else 0.0
    net_margin = round(net_profit / revenue * 100, 1) if revenue else 0.0

    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_pct": gross_margin,
        "total_expenses": total_expenses,
        "expense_breakdown": expense_breakdown,
        "net_profit": net_profit,
        "net_margin_pct": net_margin,
        "is_profit": net_profit >= 0,
        "most_profitable": prof[:5],
        "least_profitable": [r for r in prof if r["units_sold"] > 0][-5:][::-1],
    }


# --- ABC / Pareto classification -----------------------------------------
def abc_analysis(db: Session, since=None) -> list[dict]:
    """Classify products by revenue contribution.

    A = top ~80% of revenue, B = next ~15%, C = last ~5%. Tells the operator
    where to focus stock attention.
    """
    s, p = sales_frame(db, since), product_frame(db)
    if s.empty:
        return []
    rev = (s.groupby("product_id")["line_total"].sum()
             .sort_values(ascending=False).reset_index())
    rev = rev.merge(p[["product_id", "name"]], on="product_id", how="left")
    total = rev["line_total"].sum()
    rev["cum_pct"] = rev["line_total"].cumsum() / total * 100

    def band(c):
        if c <= 80:
            return "A"
        if c <= 95:
            return "B"
        return "C"

    rev["abc"] = rev["cum_pct"].apply(band)
    return [{
        "product_id": int(r.product_id), "product_name": r["name"],
        "revenue": round(float(r.line_total), 2),
        "cumulative_pct": round(float(r.cum_pct), 1), "class": r.abc,
    } for _, r in rev.iterrows()]


# --- reorder points & safety stock ---------------------------------------
def reorder_report(db: Session, only_alerts: bool = False) -> list[dict]:
    """Classic (Q,R) inventory math driven by observed demand.

      avg daily demand  d   = total units / days of history
      demand std-dev    sd  (across daily demand)
      safety stock      = z * sd * sqrt(lead_time)
      reorder point     = d * lead_time + safety_stock
      days of cover     = stock / d
    """
    s, p = sales_frame(db), product_frame(db)
    if p.empty:
        return []
    if s.empty:
        days = 1
    else:
        days = max((s["date"].max() - s["date"].min()).days + 1, 1)

    # daily demand per product
    out = []
    for _, prod in p.iterrows():
        pid = int(prod.product_id)
        psales = s[s["product_id"] == pid] if not s.empty else pd.DataFrame()
        total_units = int(psales["qty"].sum()) if not psales.empty else 0
        d = total_units / days
        if not psales.empty:
            daily = psales.groupby(psales["date"].dt.date)["qty"].sum()
            sd = float(daily.std(ddof=0)) if len(daily) > 1 else d * 0.5
        else:
            sd = 0.0
        lt = int(prod.lead_time_days or DEFAULT_LEAD_TIME_DAYS)
        safety = SERVICE_LEVEL_Z * sd * math.sqrt(lt)
        rop = d * lt + safety
        rop = max(rop, 0)
        stock = int(prod.stock)
        cover = (stock / d) if d > 0 else float("inf")
        alert = stock <= rop or (d == 0 and stock <= LOW_STOCK_FALLBACK)
        row = {
            "product_id": pid, "product_name": prod["name"],
            "stock": stock,
            "avg_daily_demand": round(d, 2),
            "safety_stock": round(safety, 1),
            "reorder_point": round(rop, 1),
            "days_of_cover": round(cover, 1) if cover != float("inf") else None,
            "suggested_order_qty": max(int(math.ceil(rop - stock)), 0) if alert else 0,
            "alert": bool(alert),
        }
        if not only_alerts or alert:
            out.append(row)
    out.sort(key=lambda r: (not r["alert"], r["days_of_cover"] if r["days_of_cover"] is not None else 1e9))
    return out


# --- RFM-style customer segmentation -------------------------------------
def customer_segments(db: Session, since=None) -> list[dict]:
    s = sales_frame(db, since)
    if s.empty:
        return []
    now = s["date"].max()
    g = s.groupby("customer_id").agg(
        recency_days=("date", lambda x: (now - x.max()).days),
        frequency=("date", "nunique"),
        monetary=("line_total", "sum"),
    ).reset_index()

    names = {c.id: c.name for c in db.query(Customer).all()}

    # simple 1-3 scoring on quantiles; robust for tiny N
    def score(series, invert=False):
        ranks = series.rank(method="first")
        try:
            q = pd.qcut(ranks, 3, labels=[1, 2, 3])
        except ValueError:
            q = pd.Series([2] * len(series), index=series.index)
        q = q.astype(int)
        return (4 - q) if invert else q

    g["R"] = score(g["recency_days"], invert=True)
    g["F"] = score(g["frequency"])
    g["M"] = score(g["monetary"])
    g["rfm"] = g[["R", "F", "M"]].sum(axis=1)

    def label(v):
        if v >= 8:
            return "Champion"
        if v >= 6:
            return "Loyal"
        if v >= 4:
            return "Promising"
        return "At risk"

    g["segment"] = g["rfm"].apply(label)
    return [{
        "customer_id": int(r.customer_id),
        "customer_name": names.get(int(r.customer_id), f"#{int(r.customer_id)}"),
        "recency_days": int(r.recency_days), "frequency": int(r.frequency),
        "monetary": round(float(r.monetary), 2), "rfm_score": int(r.rfm),
        "segment": r.segment,
    } for _, r in g.sort_values("rfm", ascending=False).iterrows()]


# --- revenue time series (for charts) ------------------------------------
def revenue_timeseries(db: Session, freq: str = "W") -> list[dict]:
    s = sales_frame(db)
    if s.empty:
        return []
    # Friendly period codes -> pandas offset aliases (pandas 2.x safe)
    alias = {"D": "D", "W": "W", "M": "ME", "Q": "QE", "Y": "YE", "ME": "ME", "YE": "YE"}
    rule = alias.get(str(freq).upper(), "W")
    g = s.set_index("date").resample(rule)["line_total"].sum().reset_index()
    # End the series at the last bucket with real sales: drop a trailing partial
    # bucket, then any trailing zero buckets (quiet recent periods / the empty
    # gap before a lone new sale). Interior no-sale periods are kept.
    if len(g) > 1 and s["date"].max() < pd.Timestamp(g["date"].iloc[-1]):
        g = g.iloc[:-1]
    nz = g.index[g["line_total"] != 0]
    if len(nz):
        g = g.loc[:nz[-1]]
    out = []
    for d, v in zip(g["date"], g["line_total"]):
        d = pd.Timestamp(d)
        if rule == "YE":
            label = d.strftime("%Y")
        elif rule == "QE":
            label = f"Q{(d.month - 1) // 3 + 1} {d.year}"
        elif rule == "ME":
            label = d.strftime("%b %Y")
        else:
            label = d.strftime("%d %b %y")
        out.append({"period": d.date().isoformat(), "label": label,
                    "revenue": round(float(v), 2)})
    return out


# --- live report (markdown, built from the current DB) -------------------
def build_report(db: Session) -> str:
    """Render the analysis report as markdown from *live* data.

    Same content the offline analysis.py writes, but computed on demand so the
    dashboard's "Download report" always reflects the current database state.
    """
    s, p = sales_frame(db), product_frame(db)
    k = kpis(db)
    top = top_sellers(db, 5)
    bottom = top_sellers(db, 5, ascending=True)
    abc = abc_analysis(db)
    reorder = reorder_report(db, only_alerts=True)
    segs = customer_segments(db)
    pl = profit_loss(db)

    counts: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    for r in abc:
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    L = [
        "# RetailOps — Data Analysis Report",
        f"_Generated live from the database on {generated}._\n",
        f"- Orders analysed: **{k['orders']}**, products: **{k['products']}**",
        f"- Revenue to date: **₹{pl['revenue']:,.0f}**",
        f"- Gross profit: **₹{pl['gross_profit']:,.0f}** ({pl['gross_margin_pct']}%) · "
        f"Net {'profit' if pl['is_profit'] else 'loss'}: **₹{pl['net_profit']:,.0f}** "
        f"({pl['net_margin_pct']}%)",
        f"- Inventory value at cost: **₹{k['inventory_value_at_cost']:,.0f}**",
        f"- History span: **{k['history_days']} days**\n",
        "## Best sellers",
    ]
    L += [f"- {r['product_name']}: {r['units_sold']:,} units, ₹{r['revenue']:,.0f}" for r in top]
    L.append("\n## Slow movers")
    L += [f"- {r['product_name']}: {r['units_sold']:,} units" for r in bottom]
    L.append("\n## ABC concentration")
    L.append(f"- A-class: {counts.get('A', 0)} products drive ~80% of revenue; "
             f"B: {counts.get('B', 0)}; C: {counts.get('C', 0)}.")
    L.append("\n## Reorder alerts")
    if reorder:
        L += [f"- **{r['product_name']}** — stock {r['stock']}, reorder pt "
              f"{r['reorder_point']}, suggest order {r['suggested_order_qty']}"
              for r in reorder]
    else:
        L.append("- None currently below reorder point.")
    L.append("\n## Top customer segments")
    L += [f"- {r['customer_name']}: {r['segment']} (spend ₹{r['monetary']:,.0f})"
          for r in segs[:5]]
    return "\n".join(L)