# RetailOps — Inventory Intelligence & Billing Platform

A retail analytics and billing system that turns raw sales data into decisions:
it classifies the products that drive revenue, segments customers, forecasts
demand, recommends what to reorder, and keeps stock accurate by decrementing
inventory the moment a bill is generated — all served through a live dashboard.

It is a ground-up rebuild of an old Tkinter desktop app into a deployable
FastAPI web service. The focus is the **analytics layer**: ABC/Pareto, RFM,
reorder points, profit & loss, and an honest demand forecaster.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-service-009688)
![Tests](https://img.shields.io/badge/tests-20%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> **Note:** the bundled dataset is **sample/synthetic** — ~2,700 orders across
> two academic years for a stationery shop — generated to exercise the
> analytics, not real customer data.

> _Tip: add a screenshot at `docs/dashboard.png` and uncomment the line below._
> <!-- ![RetailOps dashboard](docs/dashboard.png) -->

---

## Analytics & insights

The heart of the project. Every metric is computed live from the database.

- **ABC / Pareto classification** — which ~20% of SKUs drive ~80% of revenue.
- **RFM customer segmentation** — Champion / Loyal / Promising / At-risk, scored
  on recency, frequency and monetary value.
- **Demand forecasting** — weekly/monthly/yearly forecasts from a seasonal model,
  benchmarked against a naive baseline (see [How the forecasting works](#how-the-forecasting-works)).
- **Reorder points & safety stock** — classic (Q,R) inventory math from observed
  demand variability and lead time, with suggested order quantities and
  days-of-cover, surfaced as stockout-risk alerts.
- **Profit & loss** — revenue − COGS = gross profit, minus operating expenses =
  net profit, plus per-product margins and expense breakdown.
- **Best sellers / slow movers** and headline KPIs (revenue, AOV, units,
  inventory value at cost, low-stock count).
- **Downloadable report** — the same analysis is exported to Markdown on demand,
  always reflecting the current database.

## Operational features

- **Transactional billing** — every invoice is priced (discount + GST) and
  decrements live stock in a single database transaction; overselling is
  rejected and a failed line rolls back the whole bill, so stock never drifts.
- **Edit / void bills** — re-price an existing invoice (stock reconciled
  atomically) or void it to return stock to inventory.
- **Live dashboard** — a single-page app (Chart.js) that auto-refreshes on a
  poll, with a weekly/monthly/yearly granularity toggle for the time-series.
- **Full CRUD** for products, customers, categories and operating expenses.

---

## Tech stack

| Layer | Tools |
|------|------|
| API | FastAPI, Pydantic, Uvicorn |
| Data | SQLAlchemy ORM, SQLite (dev) / Postgres (prod), pandas |
| Analytics & ML | pandas, NumPy (dependency-light forecaster) |
| Frontend | Vanilla SPA + Chart.js (served by the API) |
| Tooling | pytest, Docker / docker-compose, matplotlib (offline EDA) |

## Project structure

```
app/
  models.py       Relational schema (Category, Product, Customer, Invoice, Sale, Expense)
  crud.py         Data access + transactional billing (create / edit / void) + CRUD
  analytics.py    ABC, reorder points, sellers, KPIs, RFM, profit & loss, report
  ml.py           Demand forecasting: seasonal model + backtest model-selection
  main.py         FastAPI routes, dashboard host, startup seed/train
  seed.py         Loads data/NSK_Dataset.xlsx into the database
static/
  dashboard.html  Single-page operations dashboard
analysis.py       Standalone EDA -> charts + reports/analysis_report.md
train_model.py    CLI to (re)train the forecaster and print backtest MAE
test_api.py       Pytest suite (billing, analytics, forecasting)
```

---

## Getting started

### Local (Python 3.11+)

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

On first start it seeds the database from the spreadsheet and trains the model.

- Dashboard → http://localhost:8000/
- API docs (Swagger) → http://localhost:8000/docs

### Docker

```bash
docker compose up --build
```

### Common tasks

```bash
python -m app.seed --force     # wipe & reload data from the spreadsheet
python train_model.py          # retrain the forecaster, print backtest MAE
python analysis.py             # generate EDA charts + markdown report
pytest -q                      # run the test suite
```

---

## How the forecasting works

Demand forecasting on a couple of years of seasonal retail data is a small-data
problem, so the model is deliberately simple and **honest** rather than flashy:

1. Sales are aggregated to the chosen bucket (weekly / monthly / yearly).
2. Three transparent candidates compete:
   - **trend + seasonal** — a linear trend plus an additive seasonal profile, so
     the forecast follows the trend and repeats the seasonal pattern (e.g. the
     back-to-school spike) instead of going flat.
   - **seasonal-naive** — the value from the same period one cycle ago; a strong
     baseline a real model must beat.
   - **persistence** — repeat the last bucket; the fallback when there isn't even
     one full season of history.
3. Candidates are scored on a **multi-step walk-forward backtest (MAE)** — the
   way the forecast is actually used — and the winner is selected.
4. It stays honest: it never forecasts further ahead than it has history, and
   flags low confidence on short series. The dashboard shows the selected model
   and its error versus the seasonal baseline.

The forecaster uses only NumPy/pandas, so it retrains in milliseconds — the model
is refreshed in the background after each sale.

## API overview

```
POST   /api/billing            create invoice (atomic stock decrement)
GET    /api/billing            list all invoices
GET    /api/billing/{id}       fetch one invoice (preview / print)
PATCH  /api/billing/{id}       edit an invoice (re-price, reconcile stock)
DELETE /api/billing/{id}       void an invoice (restore stock)
GET    /api/analytics/kpis            headline KPIs
GET    /api/analytics/profit-loss     revenue, COGS, gross/net profit
GET    /api/analytics/abc             ABC / Pareto classification
GET    /api/analytics/reorder         reorder points & alerts
GET    /api/analytics/customers       RFM segments
GET    /api/analytics/report          live data-analysis report (Markdown)
GET    /api/forecast                  demand forecast (model vs naive)
# plus full CRUD for /api/products, /api/customers, /api/categories, /api/expenses
```

## Configuration

All via environment variables (see `app/config.py`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///retailops.db` | Point at Postgres in production |
| `SERVICE_LEVEL_Z` | `1.65` | Safety-stock service level (~95%) |
| `DEFAULT_LEAD_TIME_DAYS` | `7` | Lead time used in reorder math |

## Possible improvements

- Per-product (rather than aggregate) demand forecasting.
- Authentication and multi-user roles.
- Power BI / Tableau export for the analytics layer.
- Backfill real transaction data in place of the synthetic seed.

## License

MIT — see `LICENSE`. (Change if you prefer a different license.)