"""Load the NSK spreadsheet into the relational database.

Idempotent: running it on a populated database is a no-op unless --force is
passed, in which case every table is truncated and reloaded.

We reconstruct opening stock as (current spreadsheet quantity + everything
already sold) so the historical sales replay leaves stock at the spreadsheet
value -- giving an internally consistent starting point.

Each customer's sales on a given day are grouped into a single historical
**invoice**, so the Bills view and all invoice-based metrics (receivables,
revenue, payment mix) are populated with realistic data instead of being empty.
"""
from __future__ import annotations

import argparse

import pandas as pd

from .config import SEED_FILE
from .database import SessionLocal, init_db
from .models import Category, Customer, Invoice, Product, Sale

# A small, deterministic slice of invoices is left on credit / unpaid so the
# "to collect" figures and payment mix look real rather than all-paid.
_PAY_CYCLE = ["Cash", "UPI", "Card", "Bank", "Cash", "UPI"]


def _truncate(db) -> None:
    for model in (Sale, Invoice, Product, Customer, Category):
        db.query(model).delete()
    db.commit()


def seed(path: str = SEED_FILE, force: bool = False) -> dict:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Product).count() and not force:
            return {"status": "skipped", "reason": "already populated"}
        if force:
            _truncate(db)

        cat = pd.read_excel(path, sheet_name="Category")
        prod = pd.read_excel(path, sheet_name="Product")
        cust = pd.read_excel(path, sheet_name="Customer")
        sales = pd.read_excel(path, sheet_name="Sales", parse_dates=["Date"])

        # Categories
        for _, r in cat.iterrows():
            db.add(Category(id=int(r.category_id), name=str(r.category_name)))

        # Customers
        for _, r in cust.iterrows():
            db.add(Customer(
                id=int(r.customer_id), name=str(r.customer_name),
                address=str(r.get("c_address", "")), phone=str(r.get("c_phone", "")),
                email=str(r.get("c_email", "")),
            ))

        # Opening stock = spreadsheet qty + units sold historically
        sold_by_prod = sales.groupby("product_id")["order_qty"].sum().to_dict()
        for _, r in prod.iterrows():
            pid = int(r.product_id)
            opening = int(r.quantity) + int(sold_by_prod.get(pid, 0))
            db.add(Product(
                id=pid, name=str(r.product_name),
                category_id=int(r.category_id) if pd.notna(r.category_id) else None,
                cost=float(r.rate), mrp=float(r.mrp), stock=opening,
            ))
        db.flush()

        prod_by_id = {p.id: p for p in db.query(Product).all()}
        price_lookup = {pid: float(p.mrp) for pid, p in prod_by_id.items()}

        # ---- group each customer's daily sales into one invoice -------------
        sales = sales.sort_values(["Date", "customer_id", "sale_id"])
        groups = list(sales.groupby(["Date", "customer_id"], sort=True))

        invoices = []
        meta = []   # parallel list of (invoice, group_df) to fill after flush
        for (date, cust_id), grp in groups:
            inv = Invoice(
                customer_id=int(cust_id),
                created_at=pd.to_datetime(date).to_pydatetime(),
                discount_pct=0.0, tax_pct=0.0,
            )
            invoices.append(inv)
            meta.append((inv, grp))
        db.add_all(invoices)
        db.flush()  # assigns invoice ids

        sale_objs = []
        for inv, grp in meta:
            subtotal = 0.0
            for _, r in grp.iterrows():
                pid, qty = int(r.product_id), int(r.order_qty)
                unit = price_lookup.get(pid, 0.0)
                line = round(unit * qty, 2)
                subtotal += line
                sale_objs.append(Sale(
                    id=int(r.sale_id),
                    date=pd.to_datetime(r.Date).to_pydatetime(),
                    customer_id=int(inv.customer_id), product_id=pid,
                    invoice_id=inv.id, qty=qty,
                    unit_price=unit, line_total=line,
                ))
                p = prod_by_id.get(pid)
                if p:
                    p.stock -= qty   # replay leaves stock at spreadsheet value

            subtotal = round(subtotal, 2)
            inv.invoice_no = f"INV-{inv.id:04d}"
            inv.subtotal = subtotal
            inv.cgst = 0.0
            inv.sgst = 0.0
            inv.tax_total = 0.0
            inv.total = subtotal

            # ~1 in 7 invoices left on credit (unpaid) for realistic receivables
            if inv.id % 7 == 0:
                inv.payment_mode = "Credit"
                inv.amount_paid = 0.0
                inv.balance_due = subtotal
                inv.status = "Unpaid"
            else:
                inv.payment_mode = _PAY_CYCLE[inv.id % len(_PAY_CYCLE)]
                inv.amount_paid = subtotal
                inv.balance_due = 0.0
                inv.status = "Paid"

        db.add_all(sale_objs)
        db.commit()

        return {
            "status": "seeded",
            "categories": db.query(Category).count(),
            "products": db.query(Product).count(),
            "customers": db.query(Customer).count(),
            "invoices": db.query(Invoice).count(),
            "sales": db.query(Sale).count(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Seed RetailOps from NSK spreadsheet")
    ap.add_argument("--force", action="store_true", help="wipe and reload")
    args = ap.parse_args()
    print(seed(force=args.force))