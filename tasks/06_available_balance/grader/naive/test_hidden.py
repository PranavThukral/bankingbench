from datetime import datetime, timezone
from fastapi.testclient import TestClient
from holds.main import create_app


class Clock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_full_capture(tmp_path):
    client = TestClient(create_app(tmp_path / "db", Clock()))
    result = client.post("/accounts/acct_standard/authorizations", json={"amount_minor": 1000})
    assert result.status_code == 201
    identifier = result.json()["auth_id"]
    assert client.post(f"/authorizations/{identifier}/capture", json={"amount_minor": 1000}).status_code == 200
    assert client.get("/accounts/acct_standard/balance").json() == {"posted_minor": 9000, "available_minor": 9000}


def test_ticket_worked_example(tmp_path):
    client = TestClient(create_app(tmp_path / "db", Clock()))
    identifier = client.post("/accounts/acct_standard/authorizations", json={"amount_minor": 3000}).json()["auth_id"]
    assert client.get("/accounts/acct_standard/balance").json() == {"posted_minor": 10000, "available_minor": 7000}
    assert client.post(f"/authorizations/{identifier}/capture", json={"amount_minor": 1200}).status_code == 200
    assert client.get("/accounts/acct_standard/balance").json() == {"posted_minor": 8800, "available_minor": 8800}


def test_invalid_amount_rejected(tmp_path):
    client = TestClient(create_app(tmp_path / "db", Clock()))
    result = client.post("/accounts/acct_standard/authorizations", json={"amount_minor": 0})
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "invalid_amount"
