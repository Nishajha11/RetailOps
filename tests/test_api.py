"""Tests. Run: pytest -q"""
import warnings
warnings.filterwarnings("ignore")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_kpis_nonempty(client):
    k = client.get("/api/analytics/kpis").json()
    assert k["products"] >= 20 and k["orders"] >= 30


def test_top_and_bottom(client):
    top = client.get("/api/analytics/top-sellers?n=3").json()
    bottom = client.get("/api/analytics/bottom-sellers?n=3").json()
    assert len(top) == 3 and len(bottom) == 3
    assert top[0]["units_sold"] >= bottom[0]["units_sold"]


def test_abc_classes(client):
    classes = {r["class"] for r in client.get("/api/analytics/abc").json()}
    assert classes <= {"A", "B", "C"}


def test_billing_decrements_stock(client):
    p = client.get("/api/products").json()[0]
    before = p["stock"]
    r = client.post("/api/billing", json={"items": [{"product_id": p["id"], "qty": 3}]})
    assert r.status_code == 200
    assert r.json()["lines"][0]["stock_after"] == before - 3
    after = [x for x in client.get("/api/products").json() if x["id"] == p["id"]][0]
    assert after["stock"] == before - 3


def test_oversell_rejected(client):
    p = client.get("/api/products").json()[0]
    r = client.post("/api/billing", json={"items": [{"product_id": p["id"], "qty": 10**9}]})
    assert r.status_code == 409


def test_forecast_returns_series(client):
    f = client.get("/api/forecast?horizon=3").json()
    fc = [x for x in f["series"] if x["kind"] == "forecast"]
    assert len(fc) == 3 and all(x["predicted_units"] >= 0 for x in fc)


# --- new: product management ---------------------------------------------
def test_product_create_edit_delete(client):
    created = client.post("/api/products", json={
        "name": "QA Marker", "cost": 4.0, "mrp": 10.0, "stock": 50, "lead_time_days": 5,
    }).json()
    assert created["margin"] == 6.0
    edited = client.patch(f"/api/products/{created['id']}", json={"mrp": 14.0}).json()
    assert edited["margin"] == 10.0
    assert client.delete(f"/api/products/{created['id']}").status_code == 200


def test_product_delete_blocked_with_sales(client):
    pid = client.get("/api/products").json()[0]["id"]
    assert client.delete(f"/api/products/{pid}").status_code == 409


# --- new: customers & categories -----------------------------------------
def test_customer_create_and_edit(client):
    c = client.post("/api/customers", json={"name": "QA Store", "phone": "12345"}).json()
    assert c["id"] > 0
    upd = client.patch(f"/api/customers/{c['id']}", json={"phone": "67890"}).json()
    assert upd["phone"] == "67890" and upd["name"] == "QA Store"


def test_category_create_and_duplicate(client):
    client.post("/api/categories", json={"name": "QA Cat"})
    dup = client.post("/api/categories", json={"name": "QA Cat"})
    assert dup.status_code == 409
    assert "product_count" in client.get("/api/categories").json()[0]


# --- new: expenses & profit/loss -----------------------------------------
def test_expense_affects_net_profit(client):
    pl0 = client.get("/api/analytics/profit-loss").json()
    e = client.post("/api/expenses", json={
        "category": "Utilities", "payee": "Board", "amount": 1000,
    }).json()
    pl1 = client.get("/api/analytics/profit-loss").json()
    assert abs((pl0["net_profit"] - pl1["net_profit"]) - 1000) < 0.5
    assert abs(pl1["gross_profit"] - (pl1["revenue"] - pl1["cogs"])) < 0.5
    assert client.post("/api/expenses", json={"category": "Other", "amount": 0}).status_code == 422
    assert client.delete(f"/api/expenses/{e['id']}").status_code == 200


def test_product_profit_shape(client):
    pp = client.get("/api/analytics/product-profit").json()
    assert pp and {"profit", "margin_pct", "cogs"} <= set(pp[0])
    assert pp[0]["profit"] >= pp[-1]["profit"]  # sorted desc by profit


def test_bills_list(client):
    p = client.get("/api/products").json()[0]
    client.post("/api/billing", json={"customer_id": 2, "items": [{"product_id": p["id"], "qty": 1}]})
    bills = client.get("/api/billing").json()
    assert bills and "customer_name" in bills[0] and bills[0]["total"] >= 0


# --- new: GST billing, payments, profile ---------------------------------
def test_gst_invoice_and_payment(client):
    p = client.get("/api/products").json()[0]
    client.patch(f"/api/products/{p['id']}", json={"gst_rate": 18, "hsn_code": "9608"})
    inv = client.post("/api/billing", json={
        "customer_id": 1, "items": [{"product_id": p["id"], "qty": 2}],
        "payment_mode": "Credit",
    }).json()
    assert inv["invoice_no"].startswith("INV-")
    assert inv["tax_total"] > 0 and abs(inv["cgst"] - inv["sgst"]) < 0.05
    assert inv["status"] == "Unpaid" and abs(inv["balance_due"] - inv["total"]) < 0.05
    rec = client.get("/api/analytics/receivables").json()
    assert rec["total_to_collect"] > 0 and rec["open_invoices"] >= 1
    g = client.get("/api/analytics/gst").json()
    assert abs(g["total_gst"] - (g["cgst"] + g["sgst"])) < 0.05


def test_business_profile(client):
    prof = client.put("/api/profile", json={"name": "Test Shop", "gstin": "27ABCDE1234F1Z5"}).json()
    assert prof["name"] == "Test Shop" and prof["gstin"].startswith("27")
    assert client.get("/api/profile").json()["name"] == "Test Shop"


# --- new: deletes, void & live report ------------------------------------
def test_category_delete_blocked_then_allowed(client):
    # a category that has products cannot be deleted
    cats = client.get("/api/categories").json()
    with_products = next(c for c in cats if c["product_count"] > 0)
    assert client.delete(f"/api/categories/{with_products['id']}").status_code == 409
    # an empty category can be deleted
    fresh = client.post("/api/categories", json={"name": "Temp Cat"}).json()
    assert client.delete(f"/api/categories/{fresh['id']}").status_code == 200


def test_customer_delete_blocked_then_allowed(client):
    # seeded customer #1 has sales history -> blocked
    assert client.delete("/api/customers/1").status_code == 409
    # a brand-new customer with no history -> deletable
    c = client.post("/api/customers", json={"name": "Throwaway Cust"}).json()
    assert client.delete(f"/api/customers/{c['id']}").status_code == 200


def test_void_bill_restores_stock(client):
    p = client.get("/api/products").json()[0]
    before = p["stock"]
    inv = client.post("/api/billing", json={
        "customer_id": 1, "items": [{"product_id": p["id"], "qty": 4}],
    }).json()
    after_sale = [x for x in client.get("/api/products").json() if x["id"] == p["id"]][0]
    assert after_sale["stock"] == before - 4
    # void it -> stock comes back, invoice gone
    res = client.delete(f"/api/billing/{inv['invoice_id']}")
    assert res.status_code == 200 and res.json()["units_restored"] == 4
    restored = [x for x in client.get("/api/products").json() if x["id"] == p["id"]][0]
    assert restored["stock"] == before
    assert client.get(f"/api/billing/{inv['invoice_id']}").status_code == 404


def test_live_report(client):
    r = client.get("/api/analytics/report").json()
    assert "generated_at" in r
    assert r["markdown"].startswith("# RetailOps")
    assert "Best sellers" in r["markdown"]