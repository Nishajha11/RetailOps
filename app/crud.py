"""Data-access layer.

The billing function is the heart of the system: it must never sell stock that
isn't there and must leave inventory consistent even if one line fails. We do
the whole invoice inside a single transaction and re-read each product with a
row lock semantics (SQLite serialises writes; on Postgres use SELECT ... FOR
UPDATE) so concurrent bills can't oversell.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


# --- products -------------------------------------------------------------
def list_products(db: Session):
    return db.query(models.Product).order_by(models.Product.name).all()


def create_product(db: Session, data: schemas.ProductCreate) -> models.Product:
    p = models.Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def adjust_stock(db: Session, product_id: int, delta: int) -> models.Product:
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, f"Product {product_id} not found")
    if p.stock + delta < 0:
        raise HTTPException(400, "Adjustment would make stock negative")
    p.stock += delta
    db.commit()
    db.refresh(p)
    return p


def update_product(db: Session, product_id: int, data: schemas.ProductUpdate) -> models.Product:
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, f"Product {product_id} not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


def delete_product(db: Session, product_id: int) -> dict:
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, f"Product {product_id} not found")
    sales = db.query(models.Sale).filter(models.Sale.product_id == product_id).count()
    if sales:
        raise HTTPException(
            409,
            f"Cannot delete '{p.name}': it has {sales} sales on record. "
            f"Set its stock to 0 instead to retire it.",
        )
    db.delete(p)
    db.commit()
    return {"status": "deleted", "product_id": product_id}


# --- categories -----------------------------------------------------------
def list_categories(db: Session):
    cats = db.query(models.Category).order_by(models.Category.name).all()
    counts = dict(
        db.query(models.Product.category_id, func.count(models.Product.id))
          .group_by(models.Product.category_id).all()
    )
    out = []
    for c in cats:
        out.append(schemas.CategoryOut(
            id=c.id, name=c.name, product_count=int(counts.get(c.id, 0))
        ))
    return out


def create_category(db: Session, data: schemas.CategoryCreate) -> models.Category:
    exists = db.query(models.Category).filter(models.Category.name == data.name).first()
    if exists:
        raise HTTPException(409, f"Category '{data.name}' already exists")
    c = models.Category(name=data.name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_category(db: Session, category_id: int) -> dict:
    c = db.get(models.Category, category_id)
    if not c:
        raise HTTPException(404, f"Category {category_id} not found")
    used = db.query(models.Product).filter(models.Product.category_id == category_id).count()
    if used:
        raise HTTPException(
            409,
            f"Cannot delete '{c.name}': {used} product(s) belong to it. "
            f"Move those products to another category first.",
        )
    db.delete(c)
    db.commit()
    return {"status": "deleted", "category_id": category_id}


# --- customers ------------------------------------------------------------
def list_customers(db: Session):
    return db.query(models.Customer).order_by(models.Customer.name).all()


def get_customer(db: Session, customer_id: int) -> models.Customer:
    c = db.get(models.Customer, customer_id)
    if not c:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return c


def create_customer(db: Session, data: schemas.CustomerCreate) -> models.Customer:
    c = models.Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def update_customer(db: Session, customer_id: int, data: schemas.CustomerUpdate) -> models.Customer:
    c = get_customer(db, customer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c


def delete_customer(db: Session, customer_id: int) -> dict:
    c = db.get(models.Customer, customer_id)
    if not c:
        raise HTTPException(404, f"Customer {customer_id} not found")
    sales = db.query(models.Sale).filter(models.Sale.customer_id == customer_id).count()
    invoices = db.query(models.Invoice).filter(models.Invoice.customer_id == customer_id).count()
    if sales or invoices:
        raise HTTPException(
            409,
            f"Cannot delete '{c.name}': it has {invoices} invoice(s) and {sales} "
            f"sale line(s) on record. Deleting would erase billing history.",
        )
    db.delete(c)
    db.commit()
    return {"status": "deleted", "customer_id": customer_id}


# --- expenses -------------------------------------------------------------
def list_expenses(db: Session):
    return db.query(models.Expense).order_by(models.Expense.date.desc()).all()


def create_expense(db: Session, data: schemas.ExpenseCreate) -> models.Expense:
    payload = data.model_dump()
    if not payload.get("date"):
        payload["date"] = datetime.utcnow()
    e = models.Expense(**payload)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def delete_expense(db: Session, expense_id: int) -> dict:
    e = db.get(models.Expense, expense_id)
    if not e:
        raise HTTPException(404, f"Expense {expense_id} not found")
    db.delete(e)
    db.commit()
    return {"status": "deleted", "expense_id": expense_id}


# --- billing (transactional) ---------------------------------------------
def _payment_status(total: float, paid: float) -> str:
    if paid >= total - 0.005:
        return "Paid"
    if paid <= 0.005:
        return "Unpaid"
    return "Partial"


def _apply_lines(db: Session, invoice: "models.Invoice",
                 data: schemas.InvoiceCreate) -> list[schemas.InvoiceLineOut]:
    """Validate items against current stock, then decrement inventory, write the
    sale rows and compute every money field on ``invoice``. Shared by create and
    edit so both price a bill identically. Caller owns the transaction.

    Validation runs fully *before* any mutation, so an oversell raises without
    touching stock. (On edit, the old lines are restored first, so validation
    sees the corrected availability.)
    """
    products: dict[int, models.Product] = {}
    for item in data.items:
        p = db.get(models.Product, item.product_id)
        if not p:
            raise HTTPException(404, f"Product {item.product_id} not found")
        if item.qty > p.stock:
            raise HTTPException(
                409,
                f"Insufficient stock for '{p.name}': requested {item.qty}, "
                f"available {p.stock}",
            )
        products[item.product_id] = p

    invoice.customer_id = data.customer_id
    invoice.discount_pct = data.discount_pct
    invoice.payment_mode = data.payment_mode or "Cash"

    factor = 1 - (data.discount_pct or 0) / 100  # discount applied per line
    lines: list[schemas.InvoiceLineOut] = []
    subtotal = 0.0   # taxable value, pre-discount (also = analytics revenue)
    tax_total = 0.0
    for item in data.items:
        p = products[item.product_id]
        unit = float(item.price) if item.price is not None else float(p.mrp)
        line_total = round(unit * item.qty, 2)            # pre-discount, pre-tax
        taxable = line_total * factor                      # after discount
        gst_rate = float(p.gst_rate or 0)
        gst_amount = round(taxable * gst_rate / 100, 2)
        subtotal += line_total
        tax_total += gst_amount
        p.stock -= item.qty  # decrement live inventory
        db.add(models.Sale(
            date=invoice.created_at, customer_id=data.customer_id,
            product_id=p.id, invoice_id=invoice.id, qty=item.qty,
            unit_price=unit, line_total=line_total,
        ))
        lines.append(schemas.InvoiceLineOut(
            product_id=p.id, product_name=p.name, hsn_code=p.hsn_code or "",
            qty=item.qty, unit_price=unit, line_total=line_total,
            gst_rate=gst_rate, gst_amount=gst_amount, stock_after=p.stock,
        ))

    taxable_total = round(subtotal * factor, 2)
    tax_total = round(tax_total, 2)
    total = round(taxable_total + tax_total, 2)

    # payment / credit handling
    if data.amount_paid is not None:
        paid = max(0.0, min(float(data.amount_paid), total))
    else:
        paid = 0.0 if (data.payment_mode or "").lower() == "credit" else total
    balance = round(total - paid, 2)

    invoice.subtotal = round(subtotal, 2)
    invoice.cgst = round(tax_total / 2, 2)
    invoice.sgst = round(tax_total - tax_total / 2, 2)
    invoice.tax_total = tax_total
    invoice.total = total
    invoice.amount_paid = round(paid, 2)
    invoice.balance_due = balance
    invoice.status = _payment_status(total, paid)
    return lines


def create_invoice(db: Session, data: schemas.InvoiceCreate) -> schemas.InvoiceOut:
    if not data.items:
        raise HTTPException(400, "Cart is empty")

    invoice = models.Invoice(
        customer_id=data.customer_id, created_at=datetime.utcnow(),
        discount_pct=data.discount_pct, payment_mode=data.payment_mode or "Cash",
    )
    db.add(invoice)
    db.flush()  # get invoice.id
    invoice.invoice_no = f"INV-{invoice.id:04d}"
    try:
        lines = _apply_lines(db, invoice, data)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(invoice)
    return _invoice_out(invoice, lines)


def update_invoice(db: Session, invoice_id: int,
                   data: schemas.InvoiceCreate) -> schemas.InvoiceOut:
    """Edit an existing bill. Reverses the old lines (returning their stock),
    then re-prices the invoice from the new cart -- all in one transaction, so
    inventory can never be left half-applied. The invoice number and date are
    preserved; totals, GST, payment and stock are recomputed.
    """
    if not data.items:
        raise HTTPException(400, "Cart is empty")
    inv = db.get(models.Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    try:
        for line in list(inv.items):            # put the old quantities back
            product = db.get(models.Product, line.product_id)
            if product:
                product.stock += line.qty
            db.delete(line)
        db.flush()                               # restored stock visible to validation
        lines = _apply_lines(db, inv, data)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(inv)
    return _invoice_out(inv, lines)


def _invoice_out(inv: "models.Invoice", lines) -> schemas.InvoiceOut:
    return schemas.InvoiceOut(
        invoice_id=inv.id, invoice_no=inv.invoice_no or f"INV-{inv.id:04d}",
        customer_id=inv.customer_id, created_at=inv.created_at, lines=lines,
        subtotal=inv.subtotal, discount_pct=inv.discount_pct,
        cgst=inv.cgst or 0, sgst=inv.sgst or 0, tax_total=inv.tax_total or 0,
        total=inv.total, payment_mode=inv.payment_mode or "Cash",
        amount_paid=inv.amount_paid or 0, balance_due=inv.balance_due or 0,
        status=inv.status or "Paid",
    )


def list_invoices(db: Session) -> list[schemas.InvoiceSummary]:
    invoices = db.query(models.Invoice).order_by(models.Invoice.id.desc()).all()
    names = {c.id: c.name for c in db.query(models.Customer).all()}
    out = []
    for inv in invoices:
        units = sum(s.qty for s in inv.items)
        out.append(schemas.InvoiceSummary(
            invoice_id=inv.id, invoice_no=inv.invoice_no or f"INV-{inv.id:04d}",
            customer_id=inv.customer_id,
            customer_name=names.get(inv.customer_id, "Walk-in customer"),
            created_at=inv.created_at, item_count=len(inv.items),
            units=units, total=inv.total, amount_paid=inv.amount_paid or 0,
            balance_due=inv.balance_due or 0, status=inv.status or "Paid",
            payment_mode=inv.payment_mode or "Cash",
        ))
    return out


def void_invoice(db: Session, invoice_id: int) -> dict:
    """Cancel an invoice and put its stock back.

    Real-world need: a bill was created by mistake, or the whole order was
    returned. We reverse it atomically -- every line's quantity is added back
    to live inventory, the sale fact rows are removed (so analytics, revenue,
    GST and receivables all self-correct), and the invoice is deleted. Done in
    one transaction so stock can never be left half-restored.
    """
    inv = db.get(models.Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    no = inv.invoice_no or f"INV-{inv.id:04d}"
    try:
        restored = 0
        for line in list(inv.items):           # inv.items are Sale rows
            product = db.get(models.Product, line.product_id)
            if product:
                product.stock += line.qty       # return goods to shelf
                restored += line.qty
            db.delete(line)                      # drop the sale fact
        db.delete(inv)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "voided", "invoice_id": invoice_id,
            "invoice_no": no, "units_restored": restored}


def get_invoice(db: Session, invoice_id: int) -> schemas.InvoiceOut:
    inv = db.get(models.Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    lines = [schemas.InvoiceLineOut(
        product_id=s.product_id, product_name=s.product.name,
        hsn_code=(s.product.hsn_code or ""), qty=s.qty,
        unit_price=s.unit_price, line_total=s.line_total,
        gst_rate=float(s.product.gst_rate or 0),
        gst_amount=round(s.line_total * (1 - (inv.discount_pct or 0) / 100)
                         * float(s.product.gst_rate or 0) / 100, 2),
        stock_after=s.product.stock,
    ) for s in inv.items]
    return _invoice_out(inv, lines)


# --- business profile -----------------------------------------------------
def get_profile(db: Session) -> models.BusinessProfile:
    prof = db.get(models.BusinessProfile, 1)
    if not prof:
        prof = models.BusinessProfile(id=1)
        db.add(prof)
        db.commit()
        db.refresh(prof)
    return prof


def update_profile(db: Session, data: schemas.BusinessProfileIn) -> models.BusinessProfile:
    prof = get_profile(db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prof, field, value)
    db.commit()
    db.refresh(prof)
    return prof