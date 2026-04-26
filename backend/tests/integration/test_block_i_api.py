"""Integration tests for Block I — Operations & Supply Chain endpoints."""
import pytest


@pytest.fixture
def ops_headers(client):
    resp = client.post("/api/v1/auth/token",
                       json={"email": "analyst@bank.uz", "password": "analyst123"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_inventory_optimizer(client, ops_headers):
    resp = client.post(
        "/api/v1/operations/inventory-optimizer",
        json={
            "sku_id": "SKU001",
            "annual_demand": 12000, "unit_cost": 25.0,
            "ordering_cost": 80.0, "holding_cost_pct": 0.20,
            "lead_time_days": 14, "demand_std_daily": 8.0,
            "service_level": 0.95,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["economic_order_quantity"] > 0
    assert pred["reorder_point"] > 0
    assert pred["safety_stock"] >= 0
    assert pred["total_annual_cost"] > 0


def test_stockout_risk_low(client, ops_headers):
    resp = client.post(
        "/api/v1/operations/stockout-risk",
        json={
            "sku_id": "SKU002",
            "on_hand_units": 5000, "on_order_units": 1000,
            "daily_demand_mean": 30, "daily_demand_std": 5,
            "lead_time_days_mean": 10, "lead_time_days_std": 1,
            "horizon_days": 30,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["risk_level"] in ["low", "medium"]
    assert pred["days_of_cover"] > 0


def test_stockout_risk_critical(client, ops_headers):
    resp = client.post(
        "/api/v1/operations/stockout-risk",
        json={
            "sku_id": "SKU003",
            "on_hand_units": 50, "on_order_units": 0,
            "daily_demand_mean": 30, "daily_demand_std": 8,
            "lead_time_days_mean": 14, "lead_time_days_std": 3,
            "horizon_days": 30,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert pred["risk_level"] in ["high", "critical"]
    assert pred["stockout_probability"] > 0.5


def test_supplier_risk(client, ops_headers):
    resp = client.post(
        "/api/v1/operations/supplier-risk",
        json={
            "supplier_id": "SUP001",
            "months_active": 6, "on_time_delivery_rate": 0.70,
            "quality_defect_rate": 0.04, "payment_terms_days": 30,
            "payment_delay_avg_days": 12, "revenue_concentration_pct": 0.55,
            "single_source_flag": True, "geopolitical_risk": 0.65,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert 0 <= pred["risk_score"] <= 1000
    assert pred["risk_band"] in ["low", "medium", "high", "severe"]
    assert pred["primary_risk_factor"]
    assert isinstance(pred["contingency_actions"], list)


def test_staffing_optimizer(client, ops_headers):
    # Demand profile peaks at noon
    demand = [0, 0, 0, 0, 0, 0, 0, 5, 20, 40, 60, 80,
              90, 80, 60, 50, 40, 50, 70, 50, 30, 10, 0, 0]
    resp = client.post(
        "/api/v1/operations/staffing-optimizer",
        json={
            "location_id": "LOC001", "hourly_demand": demand,
            "units_per_staff_hour": 12, "min_staff_per_open_hour": 1,
            "max_staff": 10, "hourly_wage": 18, "open_hour": 8, "close_hour": 22,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert len(pred["hourly_staff"]) == 24
    # Closed hours have 0 staff
    assert pred["hourly_staff"][3] == 0
    assert pred["hourly_staff"][23] == 0
    # Peak should be around noon (hour 12)
    assert pred["peak_hour"] == 12
    assert pred["estimated_labor_cost"] > 0


def test_delivery_routing(client, ops_headers):
    resp = client.post(
        "/api/v1/operations/delivery-routing",
        json={
            "depot_lat": 41.30, "depot_lon": 69.25,
            "stops": [
                {"stop_id": "S1", "lat": 41.31, "lon": 69.26, "demand": 10},
                {"stop_id": "S2", "lat": 41.29, "lon": 69.24, "demand": 15},
                {"stop_id": "S3", "lat": 41.32, "lon": 69.27, "demand": 20},
                {"stop_id": "S4", "lat": 41.28, "lon": 69.23, "demand": 5},
                {"stop_id": "S5", "lat": 41.33, "lon": 69.28, "demand": 25},
            ],
            "vehicle_capacity": 50, "n_vehicles": 3,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    pred = resp.json()["prediction"]
    assert len(pred["routes"]) >= 1
    # All routed stops should be present in some route
    routed_stops = [s for r in pred["routes"] for s in r["stop_sequence"]]
    assert set(routed_stops) | set(pred["unrouted_stops"]) == {"S1", "S2", "S3", "S4", "S5"}
    # No route should exceed capacity
    for r in pred["routes"]:
        assert r["load"] <= 50.0001
    assert pred["total_distance_km"] > 0


def test_operations_blocked_for_customer(client):
    """Customer role must NOT access Block I."""
    resp = client.post("/api/v1/auth/token",
                       json={"email": "customer@bank.uz", "password": "customer123"})
    assert resp.status_code == 200
    customer_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = client.post(
        "/api/v1/operations/inventory-optimizer",
        json={
            "sku_id": "SKU001", "annual_demand": 1000, "unit_cost": 10,
            "lead_time_days": 7,
        },
        headers=customer_headers,
    )
    assert resp.status_code == 403
