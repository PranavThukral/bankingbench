import os
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import create_app
from app.gateway import FakeGateway


def test_create():
    client = TestClient(create_app(os.environ["DATABASE_URL"], FakeGateway()))
    result = client.post("/v1/payments", headers={"X-Merchant-Id": "merchant_visible", "Idempotency-Key": str(uuid4())},
                         json={"amount_minor": 1250, "currency": "CAD", "source_token": "token_visible"})
    assert result.status_code == 201
    assert result.json()["amount_minor"] == 1250


def test_retry():
    gateway = FakeGateway()
    client = TestClient(create_app(os.environ["DATABASE_URL"], gateway))
    kwargs = dict(headers={"X-Merchant-Id": "merchant_retry", "Idempotency-Key": str(uuid4())},
                  json={"amount_minor": 100, "currency": "CAD", "source_token": "token_retry"})
    first = client.post("/v1/payments", **kwargs)
    second = client.post("/v1/payments", **kwargs)
    assert second.status_code == first.status_code == 201
    assert second.json() == first.json()
    assert len(gateway.calls) == 1


def test_missing_key():
    client = TestClient(create_app(os.environ["DATABASE_URL"], FakeGateway()))
    response = client.post("/v1/payments", headers={"X-Merchant-Id": "merchant_none"},
                           json={"amount_minor": 100, "currency": "CAD", "source_token": "token"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"
