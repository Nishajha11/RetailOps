"""Application configuration.

Everything that varies between dev / staging / production is read from the
environment so the same image can be deployed anywhere without code changes.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Storage --------------------------------------------------------------
# SQLite by default (zero-config, file-backed). Point DATABASE_URL at Postgres
# in production, e.g. postgresql+psycopg://user:pass@host/retailops
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'retailops.db'}")

# Where the source spreadsheet lives (used by the one-shot seeder).
SEED_FILE: str = os.getenv("SEED_FILE", str(BASE_DIR / "data" / "NSK_Dataset.xlsx"))

# Trained ML artifacts.
MODEL_DIR: Path = Path(os.getenv("MODEL_DIR", str(BASE_DIR / "models")))
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FORECAST_MODEL_PATH: Path = MODEL_DIR / "demand_forecaster.joblib"

# --- Inventory policy knobs ----------------------------------------------
# Default service level used for safety-stock (z-score for ~95%).
SERVICE_LEVEL_Z: float = float(os.getenv("SERVICE_LEVEL_Z", "1.65"))
# Lead time (days) assumed between reorder and restock when not set per-product.
DEFAULT_LEAD_TIME_DAYS: int = int(os.getenv("DEFAULT_LEAD_TIME_DAYS", "7"))
# Low-stock alert fires when on-hand stock <= reorder point.
LOW_STOCK_FALLBACK: int = int(os.getenv("LOW_STOCK_FALLBACK", "50"))

# --- API ------------------------------------------------------------------
API_TITLE = "RetailOps Intelligence API"
API_VERSION = "2.0.0"
