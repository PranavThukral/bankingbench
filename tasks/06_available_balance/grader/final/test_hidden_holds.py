from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient
from holds.main import create_app


class Clock:
    def __init__(self):
        self.at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self):
        return self.at


def authorize(client, value, account="acct_standard"):
    return client.post(f"/accounts/{account}/authorizations", json={"amount_minor": value})


def balance(client, account="acct_standard"):
    result = client.get(f"/accounts/{account}/balance")
    assert result.status_code == 200
    return result.json()


def test_existing_holds_reduce_available(tmp_path):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        assert authorize(client, 8000).status_code == 201
        assert balance(client) == {"posted_minor": 10000, "available_minor": 2000}
        rejected = authorize(client, 2001)
        assert rejected.status_code == 402
        assert rejected.json()["error"]["code"] == "insufficient_funds"
        assert authorize(client, 2000).status_code == 201
        assert balance(client)["available_minor"] == 0


def test_partial_capture_releases_remainder(tmp_path):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        id = authorize(client, 1000).json()["auth_id"]
        result = client.post(f"/authorizations/{id}/capture", json={"amount_minor": 400})
        assert result.status_code == 200 and result.json() == {"auth_id": id, "status": "captured"}
        assert balance(client) == {"posted_minor": 9600, "available_minor": 9600}
        again = client.post(f"/authorizations/{id}/capture", json={"amount_minor": 1})
        assert again.status_code == 409


def test_expiry_exactly_seven_days(tmp_path):
    clock = Clock()
    with TestClient(create_app(tmp_path / "db", clock)) as client:
        id = authorize(client, 1000).json()["auth_id"]
        clock.at += timedelta(days=7) - timedelta(microseconds=1)
        assert balance(client)["available_minor"] == 9000
        clock.at += timedelta(microseconds=1)
        assert balance(client) == {"posted_minor": 10000, "available_minor": 10000}
        for action in ("capture", "void"):
            args = {"json": {"amount_minor": 1}} if action == "capture" else {}
            result = client.post(f"/authorizations/{id}/{action}", **args)
            assert result.status_code == 409
            assert result.json()["error"]["code"] == "authorization_closed"


def test_void_overcapture_and_persistence(tmp_path):
    path, clock = tmp_path / "db", Clock()
    with TestClient(create_app(path, clock)) as client:
        id = authorize(client, 1000).json()["auth_id"]
        result = client.post(f"/authorizations/{id}/capture", json={"amount_minor": 1001})
        assert result.status_code == 422 and result.json()["error"]["code"] == "capture_exceeds_hold"
        assert balance(client)["available_minor"] == 9000
    with TestClient(create_app(path, clock)) as restarted:
        assert balance(restarted)["available_minor"] == 9000
        result = restarted.post(f"/authorizations/{id}/void")
        assert result.status_code == 200 and result.json()["status"] == "voided"
        assert balance(restarted)["available_minor"] == 10000
        assert restarted.post(f"/authorizations/{id}/void").status_code == 409


def test_overdraft_boundary(tmp_path):
    with TestClient(create_app(tmp_path / "db", Clock())) as client:
        assert authorize(client, 15001, "acct_flex").status_code == 402
        assert authorize(client, 15000, "acct_flex").status_code == 201
        assert balance(client, "acct_flex") == {"posted_minor": 10000, "available_minor": -5000}
        assert authorize(client, 1, "acct_flex").status_code == 402
        assert balance(client)["available_minor"] == 10000


@settings(max_examples=100)
@given(flex=st.booleans(), operations=st.lists(st.tuples(
    st.sampled_from(["authorize", "capture", "void", "advance"]), st.integers(1, 15001), st.integers(0, 50)), max_size=25))
def test_random_operation_model(flex, operations):
    with TemporaryDirectory() as directory:
        clock = Clock()
        account, overdraft = ("acct_flex", 5000) if flex else ("acct_standard", 0)
        posted, holds = 10000, {}
        with TestClient(create_app(Path(directory) / "db", clock)) as client:
            def active():
                return sum(h[0] for h in holds.values() if not h[2] and clock.at < h[1] + timedelta(days=7))
            for operation, value, index in operations:
                if operation == "advance":
                    clock.at += timedelta(hours=value % 200)
                elif operation == "authorize":
                    result = authorize(client, value, account)
                    allowed = value <= posted - active() + overdraft
                    assert result.status_code == (201 if allowed else 402)
                    if allowed:
                        id = result.json()["auth_id"]
                        assert id and id not in holds
                        holds[id] = [value, clock.at, False]
                elif holds:
                    id = list(holds)[index % len(holds)]
                    held, at, closed = holds[id]
                    args = {"json": {"amount_minor": value}} if operation == "capture" else {}
                    result = client.post(f"/authorizations/{id}/{operation}", **args)
                    if closed or clock.at >= at + timedelta(days=7):
                        assert result.status_code == 409
                    elif operation == "capture" and value > held:
                        assert result.status_code == 422
                    else:
                        assert result.status_code == 200
                        holds[id][2] = True
                        if operation == "capture":
                            posted -= value
                assert balance(client, account) == {"posted_minor": posted, "available_minor": posted - active()}
                assert posted - active() + overdraft >= 0
