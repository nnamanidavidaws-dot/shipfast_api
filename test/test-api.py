"""
tests/test_api.py

Run with:  pytest -v
or via Docker:  docker run --rm -e DATABASE_URL=... <image> pytest
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# ── In-memory SQLite for tests (no real DB needed) ────────────────────────────
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    """Create tables before tests, drop them after."""
    import app.database as db_module
    db_module._engine = test_engine
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    # Skip the lifespan (DB URL resolution) in tests
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Health check ──────────────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── Product CRUD ──────────────────────────────────────────────────────────────
SAMPLE = {
    "name":        "Test Sneaker",
    "description": "A test product",
    "price":       29.99,
    "sku":         "TEST-001",
    "in_stock":    True,
}


def test_create_product(client):
    r = client.post("/products", json=SAMPLE)
    assert r.status_code == 201
    body = r.json()
    assert body["sku"] == SAMPLE["sku"]
    assert body["price"] == SAMPLE["price"]


def test_create_duplicate_sku(client):
    r = client.post("/products", json=SAMPLE)
    assert r.status_code == 409


def test_list_products(client):
    r = client.get("/products")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert isinstance(body["products"], list)


def test_get_product(client):
    r = client.get("/products/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_missing_product(client):
    r = client.get("/products/9999")
    assert r.status_code == 404


def test_update_product(client):
    updated = {**SAMPLE, "price": 39.99, "name": "Updated Sneaker"}
    r = client.put("/products/1", json=updated)
    assert r.status_code == 200
    assert r.json()["price"] == 39.99


def test_delete_product(client):
    r = client.delete("/products/1")
    assert r.status_code == 204

    r = client.get("/products/1")
    assert r.status_code == 404


def test_invalid_price(client):
    bad = {**SAMPLE, "price": -5, "sku": "BAD-001"}
    r = client.post("/products", json=bad)
    assert r.status_code == 422