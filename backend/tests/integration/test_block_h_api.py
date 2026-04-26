"""Integration tests for Block H — Marketing & Customer Acquisition endpoints."""
import pytest


@pytest.fixture
def analyst_headers(client):
    resp = client.post("/api/v1/auth/token",
                       json={"email": "analyst@bank.uz", "password": "analyst123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_cac_predictor(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/cac-predictor",
        json={
            "channel": "paid_search", "region_id": "tashkent-01",
            "monthly_budget": 5000, "industry_mcc": "5812",
            "target_segment": "smb", "historical_cac": 0,
            "competition_intensity": 0.6,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["predicted_cac"] > 0
    assert pred["cac_range_low"] <= pred["predicted_cac"] <= pred["cac_range_high"]
    assert pred["channel_efficiency"] in ["excellent", "good", "fair", "poor"]
    assert pred["expected_acquisitions"] > 0


def test_ltv_cac_ratio_healthy(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/ltv-cac-ratio",
        json={
            "arpu_monthly": 80, "gross_margin_pct": 0.7,
            "monthly_churn_rate": 0.03, "discount_rate_annual": 0.10,
            "cac": 100,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["ltv"] > 0
    assert pred["ltv_cac_ratio"] > 0
    assert pred["verdict"] in ["unsustainable", "marginal", "healthy", "excellent"]


def test_channel_attribution(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/channel-attribution",
        json={
            "journey_id": "J001",
            "touchpoints": ["paid_search", "email", "social", "referral"],
            "conversion_value": 500.0,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert abs(sum(pred["weights"].values()) - 1.0) < 0.01
    assert abs(sum(pred["credit"].values()) - 500.0) < 1.0
    assert pred["primary_driver"] in pred["weights"]


def test_promo_uplift(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/promo-uplift",
        json={
            "customer_id": "CUST001", "promo_type": "discount", "promo_value": 50,
            "customer_recency_days": 14, "customer_frequency_30d": 1,
            "customer_monetary_30d": 200, "historical_response_rate": 0.20,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert -1 <= pred["uplift_probability"] <= 1
    assert pred["target_decision"] in ["target", "skip", "do_not_disturb"]
    assert pred["segment"] in ["persuadable", "sure_thing", "lost_cause", "sleeping_dog"]


def test_optimal_pricing(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/optimal-pricing",
        json={
            "product_id": "PROD001", "current_price": 50,
            "current_units_sold": 1000, "unit_cost": 20,
            "elasticity_estimate": -1.8,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["optimal_price"] > 0
    assert pred["expected_units"] > 0
    assert pred["confidence"] in ["low", "medium", "high"]


def test_lookalike_audience(client, analyst_headers):
    resp = client.post(
        "/api/v1/marketing/lookalike-audience",
        json={
            "seed_customer_features": {"monthly_revenue": 8000, "age_months": 24, "credit_score": 720},
            "candidate_pool": [
                {"customer_id": "C1", "monthly_revenue": 7800, "age_months": 22, "credit_score": 700},
                {"customer_id": "C2", "monthly_revenue": 800,  "age_months": 4,  "credit_score": 500},
                {"customer_id": "C3", "monthly_revenue": 9000, "age_months": 30, "credit_score": 740},
                {"customer_id": "C4", "monthly_revenue": 200,  "age_months": 1,  "credit_score": 350},
            ],
            "top_k": 2,
        },
        headers=analyst_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert len(pred["matches"]) == 2
    # The two closest candidates by revenue/age/credit should be C1 and C3
    matched_ids = {m["customer_id"] for m in pred["matches"]}
    assert matched_ids == {"C1", "C3"}


def test_marketing_blocked_for_customer(client):
    """Customer role must NOT access Block H."""
    resp = client.post("/api/v1/auth/token",
                       json={"email": "customer@bank.uz", "password": "customer123"})
    assert resp.status_code == 200
    customer_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.post(
        "/api/v1/marketing/cac-predictor",
        json={
            "channel": "email", "region_id": "tashkent-01",
            "monthly_budget": 1000, "industry_mcc": "5411",
        },
        headers=customer_headers,
    )
    assert resp.status_code == 403
