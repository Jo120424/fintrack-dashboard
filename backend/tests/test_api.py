"""Automated pytest suite verifying FINTRACK API, analytics, CSV validation, reports, and edge cases."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from database.init_db import init_database


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "test_fintrack.db"
    init_database(db_path=db_file, reset=True, seed_demo=True, reference_date=date.today())
    app = create_app(db_path=db_file)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_and_dashboard_kpis(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"

    dash = client.get("/api/dashboard?period=this_year")
    assert dash.status_code == 200
    data = dash.get_json()
    kpis = data["kpis"]
    assert kpis["total_revenue"] > 0
    assert kpis["total_expenses"] > 0
    assert round(kpis["total_revenue"] - kpis["total_expenses"], 2) == kpis["net_profit"]
    assert kpis["total_sales_transactions"] > 0
    assert "cash_flow" in kpis
    assert data["settings"]["business_name"] == "SMART MART RETAIL STORE"
    assert data["settings"]["is_demo_data"] is True


def test_all_date_filters_work(client):
    for period in (
        "today",
        "this_week",
        "this_month",
        "last_month",
        "last_3_months",
        "last_6_months",
        "this_year",
        "all",
    ):
        res = client.get(f"/api/dashboard?period={period}")
        assert res.status_code == 200, f"Failed for period {period}"
        payload = res.get_json()
        assert payload["filter"]["period"] == period

    # Custom date range
    today = date.today()
    start = date(today.year, 1, 1).isoformat()
    end = today.isoformat()
    res = client.get(f"/api/dashboard?period=custom&start_date={start}&end_date={end}")
    assert res.status_code == 200

    # Invalid custom date range
    bad = client.get("/api/dashboard?period=custom&start_date=2026-12-01&end_date=2026-01-01")
    assert bad.status_code == 400


def test_transaction_crud_and_validation(client):
    today_str = date.today().isoformat()
    # Create
    create_res = client.post(
        "/api/transactions",
        json={
            "transaction_date": today_str,
            "description": "Test Organic Honey Batch",
            "transaction_type": "Revenue",
            "category": "Groceries & Staples",
            "amount": 12500.50,
            "payment_method": "UPI",
            "notes": "Integration test",
        },
    )
    assert create_res.status_code == 201
    tx_id = create_res.get_json()["transaction"]["id"]

    # Read / Search
    list_res = client.get("/api/transactions?search=Organic+Honey")
    assert list_res.status_code == 200
    assert any(r["id"] == tx_id for r in list_res.get_json()["transactions"])

    # Update
    upd_res = client.put(
        f"/api/transactions/{tx_id}",
        json={
            "transaction_date": today_str,
            "description": "Updated Organic Honey Batch",
            "transaction_type": "Revenue",
            "category": "Groceries & Staples",
            "amount": 15000,
            "payment_method": "Cash",
            "notes": "Updated note",
        },
    )
    assert upd_res.status_code == 200
    assert upd_res.get_json()["transaction"]["amount"] == 15000.0

    # Delete
    del_res = client.delete(f"/api/transactions/{tx_id}")
    assert del_res.status_code == 200

    # Invalid payload
    bad_res = client.post(
        "/api/transactions",
        json={
            "transaction_date": "bad-date",
            "description": "",
            "transaction_type": "Invalid",
            "category": "Rent",
            "amount": -50,
            "payment_method": "Cash",
        },
    )
    assert bad_res.status_code == 400


def test_csv_validation_preview_and_deduplication(client):
    today_str = date.today().isoformat()
    csv_body = "\n".join(
        [
            "transaction_date,description,transaction_type,category,amount,payment_method,notes",
            f"{today_str},CSV Valid Sale,Revenue,Beverages & Snacks,8400,UPI,Valid row",
            f"{today_str},CSV Valid Sale,Revenue,Beverages & Snacks,8400,UPI,Dup inside file",
            "not-a-date,Broken Date Row,Expense,Rent,5000,Cash,Invalid date",
            f"{today_str},Negative Amount Row,Expense,Utilities,-120,Cash,Invalid amount",
        ]
    )

    prev_res = client.post("/api/upload", json={"action": "preview", "csv_text": csv_body})
    assert prev_res.status_code == 200
    prev = prev_res.get_json()
    assert prev["valid_count"] == 1
    assert prev["duplicate_count"] == 1
    assert prev["invalid_count"] == 2

    imp_res = client.post("/api/upload", json={"action": "import", "csv_text": csv_body})
    assert imp_res.status_code == 200
    assert imp_res.get_json()["inserted_count"] == 1

    # Re-importing same CSV should block database duplicates
    reimp = client.post("/api/upload", json={"action": "preview", "csv_text": csv_body})
    assert reimp.get_json()["valid_count"] == 0
    assert reimp.get_json()["duplicate_count"] == 2


def test_analytics_forecast_insights_and_reports(client):
    analytics_res = client.get("/api/analytics?period=all")
    assert analytics_res.status_code == 200
    ana = analytics_res.get_json()
    assert ana["forecast"]["can_forecast"] is True
    assert len(ana["forecast"]["forecast"]) == 3
    # Ensure accrual vs cash flow difference exists in demo data
    assert ana["performance_metrics"]["accrual_receivables"] > 0

    insights_res = client.get("/api/insights?period=all")
    assert insights_res.status_code == 200
    ins = insights_res.get_json()
    assert len(ins["insights"]) >= 4

    for rtype in ("monthly", "quarterly", "annual"):
        rep = client.get(f"/api/reports?report_type={rtype}")
        assert rep.status_code == 200
        assert len(rep.get_json()["observations"]) >= 1

    csv_exp = client.get("/api/export/csv?period=this_year")
    assert csv_exp.status_code == 200
    assert b"transaction_date,description" in csv_exp.data

    pdf_exp = client.get("/api/export/pdf?report_type=annual")
    assert pdf_exp.status_code == 200
    assert pdf_exp.data.startswith(b"%PDF-")


def test_settings_and_empty_dataset_safety(client):
    upd = client.put("/api/settings", json={"business_name": "NOVA SUPERMARKET", "currency": "USD"})
    assert upd.status_code == 200
    assert upd.get_json()["settings"]["business_name"] == "NOVA SUPERMARKET"

    clr = client.post("/api/settings/clear-data")
    assert clr.status_code == 200

    # Empty state across all endpoints must not raise 500 or ZeroDivisionError
    for ep in (
        "/api/dashboard?period=this_year",
        "/api/analytics?period=this_year",
        "/api/insights?period=this_year",
        "/api/reports?report_type=monthly",
    ):
        res = client.get(ep)
        assert res.status_code == 200
        assert res.get_json()["is_empty"] is True

    # Reset demo dataset restores SMART MART RETAIL STORE
    rst = client.post("/api/settings/reset-demo")
    assert rst.status_code == 200
    assert rst.get_json()["total_transactions"] >= 180
