from concurrent.futures import ThreadPoolExecutor
import threading
import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.gateway import ChargeResult
from graderlib.server import live_server


class Gateway:
    def __init__(self, latency=0, declined=False):
        self.latency, self.declined = latency, declined
        self.calls = []
        self.lock = threading.Lock()

    def charge(self, merchant_id, amount_minor, currency, source_token):
        with self.lock:
            self.calls.append((merchant_id, amount_minor, currency, source_token))
        time.sleep(self.latency)
        return ChargeResult(str(uuid4()), "declined" if self.declined else "succeeded")


def request(key=None, merchant="merchant_alpha", **changes):
    return dict(headers={"X-Merchant-Id": merchant, "Idempotency-Key": key or str(uuid4())},
                json={"amount_minor": 1250, "currency": "CAD", "source_token": "token_synthetic", **changes})


def same(first, second):
    assert first.status_code == second.status_code
    assert first.json() == second.json()


def test_sequential_retry(database_url):
    gateway = Gateway()
    client = TestClient(create_app(database_url, gateway))
    args = request()
    first = client.post("/v1/payments", **args)
    assert first.status_code == 201
    assert first.json()["merchant_id"] == "merchant_alpha"
    assert first.json()["amount_minor"] == 1250
    assert first.json()["currency"] == "CAD"
    assert first.json()["status"] == "succeeded"
    assert first.json()["payment_id"] and first.json()["charge_id"]
    same(first, client.post("/v1/payments", **args))
    assert len(gateway.calls) == 1


def test_concurrent_duplicates_charge_once(database_url):
    # The network dependency intentionally takes 150 ms; all callers start together.
    gateway = Gateway(latency=.15)
    app = create_app(database_url, gateway)
    with live_server(app) as url, httpx.Client(base_url=url, timeout=30, trust_env=False) as client:
        with ThreadPoolExecutor(max_workers=10) as pool:
            for round_no in range(25):
                key = str(uuid4())
                args = request(key=key, source_token=f"token_round_{round_no}")
                barrier = threading.Barrier(10, timeout=15)
                def call(_):
                    barrier.wait()
                    return client.post("/v1/payments", **args)
                responses = list(pool.map(call, range(10)))
                success = [r for r in responses if r.status_code == 201]
                assert success, [r.status_code for r in responses]
                for response in responses:
                    if response.status_code == 409:
                        assert response.json()["error"]["code"] == "idempotency_request_in_progress"
                    else:
                        same(success[0], response)
                same(success[0], client.post("/v1/payments", **args))
                calls = [c for c in gateway.calls if c[3] == f"token_round_{round_no}"]
                assert len(calls) == 1


def test_same_key_different_merchants_independent(database_url):
    gateway = Gateway()
    client = TestClient(create_app(database_url, gateway))
    key = str(uuid4())
    first = client.post("/v1/payments", **request(key, "merchant_a"))
    second = client.post("/v1/payments", **request(key, "merchant_b"))
    assert first.status_code == second.status_code == 201
    assert first.json()["merchant_id"] == "merchant_a"
    assert second.json()["merchant_id"] == "merchant_b"
    assert first.json()["payment_id"] != second.json()["payment_id"]
    assert len(gateway.calls) == 2


@pytest.mark.parametrize("change", [dict(amount_minor=1251), dict(currency="USD"), dict(source_token="token_other")])
def test_body_mismatch(database_url, change):
    gateway = Gateway()
    client = TestClient(create_app(database_url, gateway))
    key = str(uuid4())
    first = client.post("/v1/payments", **request(key))
    second = client.post("/v1/payments", **request(key, **change))
    assert second.status_code == 422
    assert second.json()["error"]["code"] == "idempotency_key_reuse"
    same(first, client.post("/v1/payments", **request(key)))
    assert len(gateway.calls) == 1


def test_decline_replayed(database_url):
    gateway = Gateway(declined=True)
    client = TestClient(create_app(database_url, gateway))
    args = request()
    first = client.post("/v1/payments", **args)
    assert first.status_code == 402
    assert first.json()["error"]["code"] == "card_declined"
    same(first, client.post("/v1/payments", **args))
    assert len(gateway.calls) == 1


def test_body_mismatch_while_in_flight(database_url):
    entered = threading.Event()
    gateway = Gateway(latency=.3)
    original_charge = gateway.charge

    def signal(*args):
        entered.set()
        return original_charge(*args)

    gateway.charge = signal
    with live_server(create_app(database_url, gateway)) as url, httpx.Client(base_url=url, timeout=30, trust_env=False) as client:
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            future = pool.submit(client.post, "/v1/payments", **request(key))
            assert entered.wait(10)
            mismatch = client.post("/v1/payments", **request(key, amount_minor=1251))
            assert mismatch.status_code == 422
            assert mismatch.json()["error"]["code"] == "idempotency_key_reuse"
            assert future.result().status_code == 201
        assert len(gateway.calls) == 1


def test_replay_survives_app_restart(database_url):
    gateway = Gateway()
    args = request()
    with TestClient(create_app(database_url, gateway)) as client:
        first = client.post("/v1/payments", **args)
    with TestClient(create_app(database_url, gateway)) as restarted:
        same(first, restarted.post("/v1/payments", **args))
    assert len(gateway.calls) == 1


@pytest.mark.parametrize("key", [None, "", "x" * 256])
def test_required_key(database_url, key):
    gateway = Gateway()
    client = TestClient(create_app(database_url, gateway))
    args = request()
    if key is None:
        del args["headers"]["Idempotency-Key"]
    else:
        args["headers"]["Idempotency-Key"] = key
    response = client.post("/v1/payments", **args)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"
    assert not gateway.calls


@pytest.mark.parametrize("length", [1, 100, 255])
def test_valid_key_lengths_and_reordered_body(database_url, length):
    gateway = Gateway()
    # No lifespan event is needed: the ticket requires readiness on factory return.
    client = TestClient(create_app(database_url, gateway))
    args = request(key="k" * length, merchant=str(uuid4()))
    first = client.post("/v1/payments", **args)
    assert first.status_code == 201
    args["json"] = dict(reversed(list(args["json"].items())))
    same(first, client.post("/v1/payments", **args))
    assert len(gateway.calls) == 1


def test_invalid_payment_fields_and_merchant(database_url):
    gateway = Gateway()
    client = TestClient(create_app(database_url, gateway))
    for body in [None, [], {}, {"amount_minor": 1}, *[
        {**request()["json"], **change} for change in [
            dict(amount_minor=0), dict(amount_minor=-1), dict(amount_minor=True),
            dict(amount_minor=1.5), dict(currency="XYZ"), dict(currency=1),
            dict(source_token=""), dict(source_token=1), dict(extra=1),
        ]
    ]]:
        args = request()
        args["json"] = body
        result = client.post("/v1/payments", **args)
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "invalid_payment"
    args = request()
    del args["json"]
    result = client.post("/v1/payments", content=b"{", **args)
    assert result.status_code == 422 and result.json()["error"]["code"] == "invalid_payment"
    for merchant in (None, ""):
        args = request()
        if merchant is None:
            del args["headers"]["X-Merchant-Id"]
        else:
            args["headers"]["X-Merchant-Id"] = merchant
        result = client.post("/v1/payments", **args)
        assert result.status_code == 400 and result.json()["error"]["code"] == "merchant_required"
    assert not gateway.calls


def test_concurrent_duplicates_across_app_instances(database_url):
    gateway = Gateway(latency=.15)
    apps = [create_app(database_url, gateway) for _ in range(2)]
    with live_server(apps[0]) as left, live_server(apps[1]) as right:
        with httpx.Client(timeout=30, trust_env=False) as client, ThreadPoolExecutor(max_workers=8) as pool:
            for round_no in range(10):
                token = f"cross_app_{round_no}"
                args = request(source_token=token)
                barrier = threading.Barrier(8, timeout=15)

                def call(index):
                    barrier.wait()
                    return client.post([left, right][index % 2] + "/v1/payments", **args)

                responses = list(pool.map(call, range(8)))
                successes = [r for r in responses if r.status_code == 201]
                assert successes, [r.status_code for r in responses]
                for response in responses:
                    if response.status_code == 409:
                        assert response.json()["error"]["code"] == "idempotency_request_in_progress"
                    else:
                        same(successes[0], response)
                for url in (left, right):
                    same(successes[0], client.post(url + "/v1/payments", **args))
                assert len([c for c in gateway.calls if c[3] == token]) == 1
