"""FastAPI application: REST API + dashboard host.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs   Dashboard: http://localhost:8000/
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import analytics, crud, ml, schemas
from .config import API_TITLE, API_VERSION
from .database import get_db, init_db
from .seed import seed

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()                       # idempotent first-run load
    _retrain()                   # ensure a model exists
    yield


def _retrain():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        ml.train(analytics.sales_frame(db))
    finally:
        db.close()


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)


# ---- dashboard -----------------------------------------------------------
@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


# ---- products ------------------------------------------------------------
@app.get("/api/products", response_model=list[schemas.ProductOut], tags=["products"])
def get_products(db: Session = Depends(get_db)):
    return crud.list_products(db)


@app.post("/api/products", response_model=schemas.ProductOut, tags=["products"])
def add_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, data)


@app.patch("/api/products/{product_id}/stock", response_model=schemas.ProductOut, tags=["products"])
def change_stock(product_id: int, delta: int, db: Session = Depends(get_db)):
    return crud.adjust_stock(db, product_id, delta)


@app.patch("/api/products/{product_id}", response_model=schemas.ProductOut, tags=["products"])
def edit_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    return crud.update_product(db, product_id, data)


@app.delete("/api/products/{product_id}", tags=["products"])
def remove_product(product_id: int, db: Session = Depends(get_db)):
    return crud.delete_product(db, product_id)


# ---- categories ----------------------------------------------------------
@app.get("/api/categories", response_model=list[schemas.CategoryOut], tags=["categories"])
def get_categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)


@app.post("/api/categories", response_model=schemas.CategoryOut, tags=["categories"])
def add_category(data: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db, data)


@app.delete("/api/categories/{category_id}", tags=["categories"])
def remove_category(category_id: int, db: Session = Depends(get_db)):
    return crud.delete_category(db, category_id)


# ---- customers -----------------------------------------------------------
@app.get("/api/customers", response_model=list[schemas.CustomerOut], tags=["customers"])
def get_customers(db: Session = Depends(get_db)):
    return crud.list_customers(db)


@app.post("/api/customers", response_model=schemas.CustomerOut, tags=["customers"])
def add_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db)):
    return crud.create_customer(db, data)


@app.patch("/api/customers/{customer_id}", response_model=schemas.CustomerOut, tags=["customers"])
def edit_customer(customer_id: int, data: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    return crud.update_customer(db, customer_id, data)


@app.delete("/api/customers/{customer_id}", tags=["customers"])
def remove_customer(customer_id: int, db: Session = Depends(get_db)):
    return crud.delete_customer(db, customer_id)


# ---- expenses ------------------------------------------------------------
@app.get("/api/expenses", response_model=list[schemas.ExpenseOut], tags=["expenses"])
def get_expenses(db: Session = Depends(get_db)):
    return crud.list_expenses(db)


@app.post("/api/expenses", response_model=schemas.ExpenseOut, tags=["expenses"])
def add_expense(data: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    return crud.create_expense(db, data)


@app.delete("/api/expenses/{expense_id}", tags=["expenses"])
def remove_expense(expense_id: int, db: Session = Depends(get_db)):
    return crud.delete_expense(db, expense_id)


# ---- billing -------------------------------------------------------------
@app.post("/api/billing", response_model=schemas.InvoiceOut, tags=["billing"])
def create_bill(data: schemas.InvoiceCreate, background_tasks: BackgroundTasks,
                db: Session = Depends(get_db)):
    """Create an invoice. Validates stock, then decrements inventory atomically.

    The invoice is returned to the caller *immediately*; the (cheap) forecaster
    retrain is scheduled as a background task so saving a bill is snappy and the
    user isn't kept waiting on model work.
    """
    result = crud.create_invoice(db, data)
    background_tasks.add_task(_retrain)
    return result


@app.get("/api/billing", response_model=list[schemas.InvoiceSummary], tags=["billing"])
def list_bills(db: Session = Depends(get_db)):
    return crud.list_invoices(db)


@app.get("/api/billing/{invoice_id}", response_model=schemas.InvoiceOut, tags=["billing"])
def read_bill(invoice_id: int, db: Session = Depends(get_db)):
    return crud.get_invoice(db, invoice_id)


@app.delete("/api/billing/{invoice_id}", tags=["billing"])
def void_bill(invoice_id: int, background_tasks: BackgroundTasks,
              db: Session = Depends(get_db)):
    """Void an invoice: restore its stock, remove its sale lines, delete it.

    Sales history changes, so the forecaster is retrained afterwards -- in the
    background, so the void returns immediately.
    """
    result = crud.void_invoice(db, invoice_id)
    background_tasks.add_task(_retrain)
    return result


@app.patch("/api/billing/{invoice_id}", response_model=schemas.InvoiceOut, tags=["billing"])
def edit_bill(invoice_id: int, data: schemas.InvoiceCreate,
              background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Edit an existing bill: re-price it from a new cart, reconciling stock
    atomically. Returns immediately; the forecaster retrains in the background.
    """
    result = crud.update_invoice(db, invoice_id, data)
    background_tasks.add_task(_retrain)
    return result


# ---- analytics -----------------------------------------------------------
@app.get("/api/analytics/kpis", tags=["analytics"])
def kpis(db: Session = Depends(get_db)):
    return analytics.kpis(db)


@app.get("/api/analytics/top-sellers", tags=["analytics"])
def top(n: int = 5, period: str = "all", db: Session = Depends(get_db)):
    return analytics.top_sellers(db, n=n, ascending=False,
                                 since=analytics.window_start(db, period))


@app.get("/api/analytics/bottom-sellers", tags=["analytics"])
def bottom(n: int = 5, period: str = "all", db: Session = Depends(get_db)):
    return analytics.top_sellers(db, n=n, ascending=True,
                                 since=analytics.window_start(db, period))


@app.get("/api/analytics/abc", tags=["analytics"])
def abc(period: str = "all", db: Session = Depends(get_db)):
    return analytics.abc_analysis(db, since=analytics.window_start(db, period))


@app.get("/api/analytics/reorder", tags=["analytics"])
def reorder(alerts_only: bool = False, db: Session = Depends(get_db)):
    return analytics.reorder_report(db, only_alerts=alerts_only)


@app.get("/api/analytics/customers", tags=["analytics"])
def customers(period: str = "all", db: Session = Depends(get_db)):
    return analytics.customer_segments(db, since=analytics.window_start(db, period))


@app.get("/api/analytics/revenue-series", tags=["analytics"])
def revenue_series(freq: str = "W", db: Session = Depends(get_db)):
    return analytics.revenue_timeseries(db, freq=freq)


@app.get("/api/analytics/profit-loss", tags=["analytics"])
def profit_loss(period: str = "all", db: Session = Depends(get_db)):
    return analytics.profit_loss(db, since=analytics.window_start(db, period))


@app.get("/api/analytics/product-profit", tags=["analytics"])
def product_profit(period: str = "all", db: Session = Depends(get_db)):
    return analytics.product_profitability(db, since=analytics.window_start(db, period))


@app.get("/api/analytics/receivables", tags=["analytics"])
def receivables(db: Session = Depends(get_db)):
    return analytics.receivables(db)


@app.get("/api/analytics/gst", tags=["analytics"])
def gst(db: Session = Depends(get_db)):
    return analytics.gst_collected(db)


@app.get("/api/analytics/report", tags=["analytics"])
def analysis_report(db: Session = Depends(get_db)):
    """Live data-analysis report (markdown), computed from the current DB."""
    from datetime import datetime
    return {"generated_at": datetime.now().isoformat(timespec="seconds"),
            "markdown": analytics.build_report(db)}


# ---- business profile ----------------------------------------------------
@app.get("/api/profile", response_model=schemas.BusinessProfileOut, tags=["settings"])
def read_profile(db: Session = Depends(get_db)):
    return crud.get_profile(db)


@app.put("/api/profile", response_model=schemas.BusinessProfileOut, tags=["settings"])
def write_profile(data: schemas.BusinessProfileIn, db: Session = Depends(get_db)):
    return crud.update_profile(db, data)


# ---- ML ------------------------------------------------------------------
@app.get("/api/forecast", tags=["ml"])
def get_forecast(horizon: int = 4, freq: str = "W", db: Session = Depends(get_db)):
    return ml.forecast_series(analytics.sales_frame(db), freq=freq, horizon=horizon)


@app.post("/api/forecast/retrain", tags=["ml"])
def retrain(db: Session = Depends(get_db)):
    art = ml.train(analytics.sales_frame(db))
    return JSONResponse({"status": "retrained", "metrics": art.metrics})


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "version": API_VERSION}


# static assets (if any added later)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")