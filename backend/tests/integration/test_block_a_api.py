"""Integration tests for Block A — Market Analysis endpoints."""
import pytest


def test_market_sizing(client, auth_headers):
    resp = client.post(
        "/api/v1/market-analysis/market-sizing",
        json={"region_id": "tashkent-01", "mcc_code": "5812", "population": 50000, "avg_income": 800},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "M-A1"
    assert data["is_stub"] is True
    assert "prediction" in data
    assert data["prediction"]["tam"] > 0
    assert data["prediction"]["som"] < data["prediction"]["sam"] < data["prediction"]["tam"]


def test_gap_analysis(client, auth_headers):
    resp = client.post(
        "/api/v1/market-analysis/gap-analysis",
        json={"region_id": "tashkent-01", "mcc_code": "5812",
              "normative_density": 3.0, "actual_count": 8, "population": 50000},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == "M-A2"
    assert "verdict" in data["prediction"]


def test_saturation_index(client, auth_headers):
    resp = client.post(
        "/api/v1/market-analysis/saturation-index",
        json={"region_id": "tashkent-01", "mcc_code": "5812",
              "competitor_count": 12, "population": 50000, "avg_revenue_per_outlet": 30000},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert 0 <= resp.json()["prediction"]["saturation_index"] <= 100


def test_niche_opportunity(client, auth_headers):
    resp = client.post(
        "/api/v1/market-analysis/niche-opportunity",
        json={"region_id": "tashkent-01", "mcc_code": "5812",
              "population": 80000, "avg_income": 700, "competitor_count": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert 0 <= resp.json()["prediction"]["opportunity_score"] <= 100


def test_explain_flag(client, auth_headers):
    resp = client.post(
        "/api/v1/market-analysis/market-sizing?explain=true",
        json={"region_id": "tashkent-01", "mcc_code": "5812", "population": 50000, "avg_income": 800},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["explanation"] is not None
