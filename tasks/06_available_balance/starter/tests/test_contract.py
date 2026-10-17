from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from holds.main import create_app


class Clock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", [0, -1, True, "100"])
def test_invalid_authorization_amount(tmp_path, value):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        result = client.post("/accounts/acct_standard/authorizations", json={"amount_minor": value})
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "invalid_amount"


def test_unknown_account(tmp_path):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        assert client.get("/accounts/absent/balance").status_code == 404


def test_unknown_authorization(tmp_path):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        assert client.post("/authorizations/absent/void").status_code == 404


def test_naive_clock_rejected(tmp_path):
    class NaiveClock:
        def now(self):
            return datetime(2026, 1, 1)
    with pytest.raises(ValueError):
        create_app(tmp_path / "db", NaiveClock())
