"""Integration tests for Block F — Credit endpoints (highest priority)."""
import pytest


@pytest.fixture
def officer_headers(client):
    resp = client.post("/api/v1/auth/token", json={"email": "officer@bank.uz", "password": "officer123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_credit_risk_score(client, officer_headers):
    resp = client.post(
        "/api/v1/credit/risk-score",
        json={
            "customer_id": "CUST001",
            "mcc_code": "5812",
            "region_id": "tashkent-01",
            "lat": 41.299, "lon": 69.240,
            "monthly_revenue_estimate": 15000,
            "requested_loan_amount": 50000,
            "business_age_months": 18,
            "owner_credit_history_score": 680,
            "collateral_value": 25000,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "M-F1"
    assert 0 <= data["prediction"]["credit_score"] <= 1000
    assert data["prediction"]["decision"] in ["approve", "conditional", "reject"]
    assert 0 <= data["prediction"]["default_probability"] <= 1


def test_npl_warning(client, officer_headers):
    resp = client.post(
        "/api/v1/credit/npl-warning",
        json={
            "customer_id": "CUST001",
            "loan_id": "LOAN001",
            "months_since_disbursement": 8,
            "payment_delays_count": 2,
            "revenue_trend_3m_pct": -15.0,
            "current_dti": 0.52,
            "location_score": 45,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["prediction"]["alert_level"] in ["green", "yellow", "orange", "red"]
    assert 0 <= data["prediction"]["npl_probability"] <= 1


def test_credit_blocked_for_customer(client):
    """Customer role should NOT access Block F."""
    # Get a customer-role token
    resp = client.post("/api/v1/auth/token", json={"email": "customer@bank.uz", "password": "customer123"})
    assert resp.status_code == 200
    customer_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.post(
        "/api/v1/credit/risk-score",
        json={
            "customer_id": "CUST001", "mcc_code": "5812", "region_id": "tashkent-01",
            "lat": 41.299, "lon": 69.240, "monthly_revenue_estimate": 15000,
            "requested_loan_amount": 50000, "business_age_months": 12,
            "owner_credit_history_score": 600, "collateral_value": 0,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 403


def test_product_recommender(client, officer_headers):
    resp = client.post(
        "/api/v1/credit/product-recommender",
        json={
            "customer_id": "CUST001",
            "mcc_code": "5812",
            "monthly_revenue": 12000,
            "business_age_months": 24,
            "existing_products": [],
            "credit_score": 650,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["prediction"]["recommendations"]) > 0
    assert data["prediction"]["primary_recommendation"]
