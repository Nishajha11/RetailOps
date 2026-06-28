"""Database engine and session management."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DATABASE_URL

# check_same_thread is a SQLite-only flag; harmless to compute conditionally.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables, then add any newly-introduced columns to existing
    tables. Safe to call repeatedly; preserves existing data."""
    from . import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
    _migrate()


# Columns added after the original schema shipped. (table, column, SQL type+default)
_ADDED_COLUMNS = [
    ("products", "hsn_code", "VARCHAR DEFAULT ''"),
    ("products", "gst_rate", "FLOAT DEFAULT 0"),
    ("customers", "gstin", "VARCHAR DEFAULT ''"),
    ("invoices", "invoice_no", "VARCHAR DEFAULT ''"),
    ("invoices", "cgst", "FLOAT DEFAULT 0"),
    ("invoices", "sgst", "FLOAT DEFAULT 0"),
    ("invoices", "tax_total", "FLOAT DEFAULT 0"),
    ("invoices", "payment_mode", "VARCHAR DEFAULT 'Cash'"),
    ("invoices", "amount_paid", "FLOAT DEFAULT 0"),
    ("invoices", "balance_due", "FLOAT DEFAULT 0"),
    ("invoices", "status", "VARCHAR DEFAULT 'Paid'"),
]


def _migrate() -> None:
    """Lightweight additive migration for SQLite/Postgres: ADD COLUMN where it
    is missing. No data is dropped."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table, col, decl in _ADDED_COLUMNS:
            if table not in existing_tables:
                continue
            cols = {c["name"] for c in insp.get_columns(table)}
            if col not in cols:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {decl}'))