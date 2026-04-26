"""Integration tests for Block J — Fraud, AML & Identity endpoints."""
import pytest


@pytest.fixture
def officer_headers(client):
    resp = client.post("/api/v1/auth/token",
                       json={"email": "officer@bank.uz", "password": "officer123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_transaction_anomaly_high_risk(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/transaction-anomaly",
        json={
            "customer_id": "CUST001", "transaction_id": "TXN001",
            "amount": 2500, "mcc_code": "5812",
            "txn_count_last_24h": 18, "txn_count_last_7d": 40,
            "avg_amount_last_30d": 120, "distinct_merchants_last_24h": 12,
            "is_foreign": True, "is_cnp": True, "hour_of_day": 3,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "M-J1"
    pred = data["prediction"]
    assert 0 <= pred["anomaly_score"] <= 1
    assert pred["risk_level"] in ["low", "medium", "high", "critical"]
    assert pred["risk_level"] in ["high", "critical"]   # this profile is clearly anomalous
    assert pred["is_anomaly"] is True


def test_transaction_anomaly_normal(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/transaction-anomaly",
        json={
            "customer_id": "CUST002", "transaction_id": "TXN002",
            "amount": 45, "mcc_code": "5411",
            "txn_count_last_24h": 2, "txn_count_last_7d": 12,
            "avg_amount_last_30d": 50, "distinct_merchants_last_24h": 2,
            "is_foreign": False, "is_cnp": False, "hour_of_day": 14,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["risk_level"] in ["low", "medium"]


def test_merchant_fraud_score(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/merchant-fraud",
        json={
            "merchant_id": "M0001", "mcc_code": "5816",
            "months_active": 4, "chargeback_rate_30d": 0.045,
            "refund_rate_30d": 0.08, "avg_ticket_size": 80,
            "txn_velocity_per_day": 250, "pct_cnp_transactions": 0.85,
            "pct_foreign_cards": 0.45, "prior_complaints_count": 4,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "M-J2"
    pred = data["prediction"]
    assert 0 <= pred["fraud_probability"] <= 1
    assert 0 <= pred["fraud_score"] <= 1000
    assert pred["risk_band"] in ["low", "medium", "high", "severe"]
    assert pred["decision"] in ["monitor", "restrict", "suspend"]


def test_aml_pattern_structuring(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/aml-pattern",
        json={
            "customer_id": "CUST003",
            "cash_deposits_last_7d": 8, "cash_amount_last_7d": 68000,
            "structuring_threshold": 10000, "near_threshold_deposits_30d": 7,
            "rapid_in_out_count_30d": 12, "distinct_counterparties_30d": 18,
            "cross_border_count_30d": 6, "high_risk_jurisdiction_count": 2,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["typology"] in ["structuring", "layering", "integration", "none"]
    assert isinstance(pred["sar_recommended"], bool)
    assert 0 <= pred["suspicion_score"] <= 1


def test_synthetic_identity(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/synthetic-identity",
        json={
            "applicant_id": "APP001",
            "credit_file_age_months": 4, "credit_inquiries_last_6m": 8,
            "address_changes_last_24m": 3, "ssn_age_norm": 0.45,
            "phone_tenure_months": 2, "email_tenure_months": 3,
            "distinct_names_at_address": 5, "employer_verifiable": False,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert 0 <= pred["synthetic_probability"] <= 1
    assert pred["confidence_band"] in ["low", "medium", "high"]
    assert isinstance(pred["contributing_factors"], list)
    assert isinstance(pred["verification_steps"], list)


def test_application_fraud(client, officer_headers):
    resp = client.post(
        "/api/v1/fraud/application-fraud",
        json={
            "application_id": "APP100",
            "applications_last_24h": 4, "applications_last_30d": 9,
            "device_seen_count_30d": 6, "ip_seen_count_30d": 5,
            "declared_income": 8000, "bureau_income_estimate": 3500,
            "document_quality_score": 0.4, "velocity_score": 0.8,
            "geolocation_mismatch": True,
        },
        headers=officer_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert 0 <= pred["fraud_probability"] <= 1
    assert pred["decision"] in ["approve", "review", "deny"]
    assert pred["risk_score"] >= 0


def test_fraud_blocked_for_customer(client):
    """Customer role must NOT access Block J."""
    resp = client.post("/api/v1/auth/token",
                       json={"email": "customer@bank.uz", "password": "customer123"})
    assert resp.status_code == 200
    customer_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.post(
        "/api/v1/fraud/transaction-anomaly",
        json={
            "customer_id": "CUST001", "transaction_id": "TXN001",
            "amount": 50, "mcc_code": "5411",
            "txn_count_last_24h": 1, "txn_count_last_7d": 5,
            "avg_amount_last_30d": 50, "distinct_merchants_last_24h": 1,
            "is_foreign": False, "is_cnp": False, "hour_of_day": 12,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 403


def test_fraud_models_bypass_cache(client, officer_headers, registry):
    """All M-J* models must be in _NO_CACHE so fraud signals are always live."""
    from app.services.prediction_service import _NO_CACHE
    for mid in ["M-J1", "M-J2", "M-J3", "M-J4", "M-J5"]:
        assert mid in _NO_CACHE, f"{mid} must be in _NO_CACHE for live fraud signals"
        # Also confirm it actually got registered
        assert mid in registry.all_ids()
