"""Pytest fixtures for unit and integration tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.registry import get_registry

# Test JWT for admin role (uses stub auth)
ADMIN_TOKEN = None  # Will be obtained via /auth/token in tests


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post("/api/v1/auth/token", json={"email": "admin@bank.uz", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def registry():
    return get_registry()
