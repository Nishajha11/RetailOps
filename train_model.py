"""Train (or retrain) the demand forecasting model from current DB sales.

    python train_model.py

Prints the backtest comparison so you can see whether the ML model beat the
naive baseline on your latest data.
"""
from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

from app import analytics, ml
from app.database import SessionLocal, init_db
from app.seed import seed


def main():
    init_db()
    seed()  # ensure data exists
    db = SessionLocal()
    try:
        art = ml.train(analytics.sales_frame(db))
    finally:
        db.close()
    print("Trained forecasting model")
    print("  selected model :", art.kind)
    for k, v in art.metrics.items():
        print(f"  {k:16s}: {v}")
    print("  saved to       :", ml.FORECAST_MODEL_PATH)


if __name__ == "__main__":
    main()
