from author_common import task_meta, write

b = task_meta("01_idempotent_payments", "Make payment creation idempotent", "app", [
    "app.main:create_app(database_url, gateway) -> FastAPI", "app.gateway:Gateway, ChargeResult",
    "HTTP POST /v1/payments"], [
    ("wrong_retry_race", "Checks before charging; concurrent requests each charge before insertion.", ["test_concurrent_duplicates_charge_once"]),
    ("wrong_key_scope", "Shares a key across merchants.", ["test_same_key_different_merchants_independent"]),
    ("wrong_inmemory_cache", "App-local cache disappears at restart.", ["test_replay_survives_app_restart"]),
], "Transaction-wide advisory lock and response on payment rows; reference reserves persistent request rows.",
    requires=["postgres"], terms=["ON CONFLICT", "advisory", "FOR UPDATE", "idempotency_keys"], difficulty="hard")

write(b / "PROBLEM.md", '''
# Ticket: payment retries must be idempotent

Our synthetic payment service already charges a declared gateway and returns a receipt.
Clients retry requests after losing a response. Implement the following observable contract.

Public interface: `app.main.create_app(database_url: str, gateway: Gateway) -> FastAPI`;
`app.gateway.Gateway.charge(merchant_id, amount_minor, currency, source_token) -> ChargeResult`.
`ChargeResult(charge_id: str, status: "succeeded"|"declined")` is a frozen dataclass.
`POST /v1/payments` takes `X-Merchant-Id`, `Idempotency-Key`, and JSON
`{amount_minor, currency, source_token}`. Money is positive integer minor units, never bool.
Currencies supported: CAD/USD/EUR/GBP (2 dp), JPY (0), KWD/BHD (3). No conversion occurs.

- Key required, length 1–255 characters; missing/empty/too long: HTTP 400
  `idempotency_key_required`. Merchant is a nonempty string; missing: 400 `merchant_required`.
- Invalid JSON body/fields: 422 `invalid_payment`. Ignore JSON member ordering. Body equality
  means equality of the three validated fields; no extra fields are accepted.
- Keys are scoped per merchant. Same merchant, key and body replay the original status and JSON
  exactly, without another gateway call. Declines (402 `card_declined`) also replay exactly.
- Same merchant and key with a different body: 422 `idempotency_key_reuse`, no charge,
  whether the first request is complete or in flight.
- Concurrent identical duplicates cause exactly one gateway charge. Each duplicate either gets
  the original response or HTTP 409 `idempotency_request_in_progress`. A later retry must replay.
- This behavior survives creating another app instance against the same database; no expiry.
- A successful receipt is HTTP 201 with `payment_id`, `charge_id`, `status` ("succeeded"),
  `amount_minor`, `currency`, and `merchant_id`. The payment id is nonempty and unique for distinct
  payments. Do not compare an id to any particular UUID format.
- Errors are JSON `{"error":{"code":"<snake_case>","message":"..."}}`; message text is free.
  No gateway exceptions or crash recovery are in scope. A charge returns normally with either status.

Preserve the factory and gateway protocol. Store state in the supplied PostgreSQL database;
the application may create its own schema. Tests inspect only the declared HTTP surface and
gateway calls. Timestamps in stored receipts use aware UTC; no timestamp field is required in JSON.
Run visible tests from starter: `python -m pytest tests -q` with `DATABASE_URL` set to a disposable
database. No customer data or real payment network is involved.
''')

write(b / "starter/app/gateway.py", '''
"""External charging boundary for a synthetic network."""
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class ChargeResult:
    charge_id: str
    status: Literal["succeeded", "declined"]


class Gateway(Protocol):
    def charge(self, merchant_id: str, amount_minor: int, currency: str,
               source_token: str) -> ChargeResult:
        """Return a network receipt; a decline is a normal result."""
        ...


@dataclass(frozen=True)
class ChargeCall:
    merchant_id: str
    amount_minor: int
    currency: str
    source_token: str


class FakeGateway:
    """Inert local development gateway, with a thread-safe call history."""

    def __init__(self):
        self._calls: list[ChargeCall] = []
        self._lock = Lock()

    @property
    def calls(self) -> tuple[ChargeCall, ...]:
        with self._lock:
            return tuple(self._calls)

    def charge(self, merchant_id, amount_minor, currency, source_token):
        call = ChargeCall(merchant_id, amount_minor, currency, source_token)
        with self._lock:
            self._calls.append(call)
        status = "declined" if source_token.startswith("decline_") else "succeeded"
        return ChargeResult(str(uuid4()), status)
''')

write(b / "starter/app/contracts.py", '''
"""Request and response construction shared by the HTTP adapter."""
from dataclasses import dataclass
import hashlib
import json

from fastapi.responses import JSONResponse

CURRENCIES = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


@dataclass(frozen=True)
class PaymentRequest:
    amount_minor: int
    currency: str
    source_token: str

    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict):
            raise ValueError("object required")
        if set(data) != {"amount_minor", "currency", "source_token"}:
            raise ValueError("payment fields required")
        amount = data["amount_minor"]
        if type(amount) is not int or amount <= 0:
            raise ValueError("positive integer amount required")
        currency = data["currency"]
        if not isinstance(currency, str) or currency not in CURRENCIES:
            raise ValueError("unsupported currency")
        token = data["source_token"]
        if not isinstance(token, str) or not token:
            raise ValueError("source token required")
        return cls(amount, currency, token)

    def as_dict(self):
        return dict(amount_minor=self.amount_minor, currency=self.currency,
                    source_token=self.source_token)

    def fingerprint(self):
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


def error(status, code, message=None):
    return JSONResponse({"error": {"code": code, "message": message or code}}, status_code=status)


def headers(merchant, key):
    if not merchant:
        return error(400, "merchant_required")
    if key is None or not 1 <= len(key) <= 255:
        return error(400, "idempotency_key_required")
    return None


def receipt(payment_id, merchant, request, charge):
    if charge.status == "declined":
        return 402, {"error": {"code": "card_declined", "message": "Synthetic decline"}}
    return 201, {"payment_id": payment_id, "charge_id": charge.charge_id,
                 "status": charge.status, "merchant_id": merchant,
                 "amount_minor": request.amount_minor, "currency": request.currency}
''')

write(b / "starter/app/storage.py", '''
"""Persistent payment receipts. Each operation owns its connection."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import psycopg

from app.contracts import receipt


@dataclass(frozen=True)
class StoredPayment:
    payment_id: str
    merchant_id: str
    amount_minor: int
    currency: str
    source_token: str
    charge_id: str
    status: str
    created_at: datetime


class PaymentStore:
    def __init__(self, database_url):
        self.database_url = database_url
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS payments (
                payment_id text PRIMARY KEY,
                merchant_id text NOT NULL,
                amount_minor bigint NOT NULL,
                currency text NOT NULL,
                source_token text NOT NULL,
                charge_id text NOT NULL,
                status text NOT NULL,
                created_at timestamptz NOT NULL
            )""")

    def connect(self):
        return psycopg.connect(self.database_url)

    def save(self, merchant, request, charge, conn=None):
        payment = StoredPayment(str(uuid4()), merchant, request.amount_minor, request.currency,
                                request.source_token, charge.charge_id, charge.status,
                                datetime.now(timezone.utc))
        if conn is None:
            with self.connect() as owned:
                self.insert(owned, payment)
        else:
            self.insert(conn, payment)
        return receipt(payment.payment_id, merchant, request, charge)

    @staticmethod
    def insert(conn, payment):
        conn.execute("""INSERT INTO payments VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (payment.payment_id, payment.merchant_id, payment.amount_minor,
                      payment.currency, payment.source_token, payment.charge_id,
                      payment.status, payment.created_at))

    def list_for_merchant(self, merchant):
        with self.connect() as conn:
            rows = conn.execute("""SELECT payment_id,merchant_id,amount_minor,currency,
                source_token,charge_id,status,created_at FROM payments
                WHERE merchant_id=%s ORDER BY created_at,payment_id""", (merchant,)).fetchall()
        return [StoredPayment(*row) for row in rows]

    def get(self, payment_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM payments WHERE payment_id=%s", (payment_id,)).fetchone()
        return StoredPayment(*row) if row else None
''')

prefix = '''
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.contracts import PaymentRequest, error, headers
from app.storage import PaymentStore


def create_app(database_url, gateway):
    store = PaymentStore(database_url)
    app = FastAPI()
    @app.post("/v1/payments")
    async def pay(request: Request):
        merchant = request.headers.get("X-Merchant-Id")
        key = request.headers.get("Idempotency-Key")
        invalid = headers(merchant, key)
        if invalid is not None:
            return invalid
        try:
            body = PaymentRequest.parse(await request.json())
        except (ValueError, TypeError):
            return error(422, "invalid_payment")
        return await __import__("starlette.concurrency", fromlist=["run_in_threadpool"]).run_in_threadpool(
            process, merchant, key, body)

    def process(merchant, key, body):
'''
write(b / "starter/app/main.py", prefix + '''
        charge = gateway.charge(merchant, body.amount_minor, body.currency, body.source_token)
        status, payload = store.save(merchant, body, charge)
        return JSONResponse(payload, status_code=status)
    return app
''')

reference = '''
import json
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.contracts import PaymentRequest, error, headers
from app.storage import PaymentStore


def create_app(database_url, gateway):
    store = PaymentStore(database_url)
    with store.connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS idempotency_keys (
            merchant text, key text, fingerprint text NOT NULL, state text NOT NULL,
            response_code integer, response_json jsonb, PRIMARY KEY(merchant,key))""")
    app = FastAPI()

    @app.post("/v1/payments")
    async def pay(request: Request):
        merchant, key = request.headers.get("X-Merchant-Id"), request.headers.get("Idempotency-Key")
        invalid = headers(merchant, key)
        if invalid is not None:
            return invalid
        try:
            body = PaymentRequest.parse(await request.json())
        except (ValueError, TypeError):
            return error(422, "invalid_payment")
        return await run_in_threadpool(process, merchant, key, body)

    def process(merchant, key, body):
        scope = merchant
        with store.connect() as conn:
            inserted = conn.execute("""INSERT INTO idempotency_keys VALUES (%s,%s,%s,'in_progress',NULL,NULL)
                ON CONFLICT DO NOTHING RETURNING key""", (scope, key, body.fingerprint())).fetchone()
            if not inserted:
                row = conn.execute("""SELECT fingerprint,state,response_code,response_json
                    FROM idempotency_keys WHERE merchant=%s AND key=%s""", (scope, key)).fetchone()
                if row[0] != body.fingerprint():
                    return error(422, "idempotency_key_reuse")
                if row[1] != "complete":
                    return error(409, "idempotency_request_in_progress")
                return JSONResponse(row[3], status_code=row[2])
        charge = gateway.charge(merchant, body.amount_minor, body.currency, body.source_token)
        with store.connect() as conn:
            code, payload = store.save(merchant, body, charge, conn)
            conn.execute("""UPDATE idempotency_keys SET state='complete',response_code=%s,response_json=%s
                WHERE merchant=%s AND key=%s""", (code, json.dumps(payload), scope, key))
        return JSONResponse(payload, status_code=code)
    return app
'''
reference = reference.replace("import psycopg\n", "")
write(b / "solutions/reference/app/main.py", reference)
write(b / "solutions/wrong_key_scope/app/main.py", reference.replace("scope = merchant", 'scope = "shared"'))

race = reference.replace("import json", "import json\nimport psycopg")
start = race.index('        with store.connect() as conn:\n            inserted')
end = race.index('        charge = gateway.charge', start)
race = race[:start] + '''        with store.connect() as conn:
            row = conn.execute("""SELECT fingerprint,state,response_code,response_json
                FROM idempotency_keys WHERE merchant=%s AND key=%s""", (scope, key)).fetchone()
            if row:
                if row[0] != body.fingerprint():
                    return error(422, "idempotency_key_reuse")
                return JSONResponse(row[3], status_code=row[2])
''' + race[end:]
race = race.replace('''            conn.execute("""UPDATE idempotency_keys SET state='complete',response_code=%s,response_json=%s
                WHERE merchant=%s AND key=%s""", (code, json.dumps(payload), scope, key))''', '''            try:
                conn.execute("""INSERT INTO idempotency_keys VALUES (%s,%s,%s,'complete',%s,%s)""",
                             (scope, key, body.fingerprint(), code, json.dumps(payload)))
            except psycopg.errors.UniqueViolation:
                conn.rollback()
                return error(500, "payment_conflict")''')
write(b / "solutions/wrong_retry_race/app/main.py", race)

write(b / "solutions/wrong_inmemory_cache/app/main.py", 'from threading import Lock\n' + prefix.replace(
    '    app = FastAPI()', '    cache, lock = {}, Lock()\n    app = FastAPI()') + '''
        with lock:
            identity = (merchant, key)
            if identity in cache:
                fingerprint, status, payload = cache[identity]
                if fingerprint != body.fingerprint():
                    return error(422, "idempotency_key_reuse")
            else:
                charge = gateway.charge(merchant, body.amount_minor, body.currency, body.source_token)
                status, payload = store.save(merchant, body, charge)
                cache[identity] = (body.fingerprint(), status, payload)
            return JSONResponse(payload, status_code=status)
    return app
''')

write(b / "solutions/alt_valid/app/main.py", '''
"""Serialize a request identity for the lifetime of its charging transaction."""
from datetime import datetime, timezone
import json
from uuid import uuid4
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.contracts import PaymentRequest, error, headers, receipt


def create_app(database_url, gateway):
    with psycopg.connect(database_url) as setup:
        setup.execute("""CREATE TABLE IF NOT EXISTS payment_receipts (
            id text PRIMARY KEY, merchant text, request_key text, request_body jsonb,
            response jsonb, code int, created_at timestamptz,
            UNIQUE (merchant, request_key))""")

    def serialized_charge(merchant, key, parsed):
        with psycopg.connect(database_url) as transaction:
            lock_identity = json.dumps([merchant, key])
            transaction.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (lock_identity,))
            previous = transaction.execute("""SELECT request_body,response,code FROM payment_receipts
                WHERE merchant=%s AND request_key=%s""", (merchant, key)).fetchone()
            if previous is not None:
                if previous[0] != parsed.as_dict():
                    return error(422, "idempotency_key_reuse")
                return JSONResponse(previous[1], status_code=previous[2])
            result = gateway.charge(merchant, parsed.amount_minor, parsed.currency, parsed.source_token)
            identifier = str(uuid4())
            status, response = receipt(identifier, merchant, parsed, result)
            transaction.execute("INSERT INTO payment_receipts VALUES (%s,%s,%s,%s,%s,%s,%s)",
                                (identifier, merchant, key, json.dumps(parsed.as_dict()),
                                 json.dumps(response), status, datetime.now(timezone.utc)))
            return JSONResponse(response, status_code=status)

    api = FastAPI()

    @api.post("/v1/payments")
    async def payment_endpoint(request: Request):
        merchant_id = request.headers.get("X-Merchant-Id")
        request_key = request.headers.get("Idempotency-Key")
        invalid_headers = headers(merchant_id, request_key)
        if invalid_headers is not None:
            return invalid_headers
        try:
            parsed = PaymentRequest.parse(await request.json())
        except (ValueError, TypeError):
            return error(422, "invalid_payment")
        return await run_in_threadpool(serialized_charge, merchant_id, request_key, parsed)

    return api
''')

visible = '''
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
'''
write(b / "starter/tests/test_visible.py", visible)
write(b / "grader/naive/test_hidden.py", visible + '''

def test_missing_key():
    client = TestClient(create_app(os.environ["DATABASE_URL"], FakeGateway()))
    response = client.post("/v1/payments", headers={"X-Merchant-Id": "merchant_none"},
                           json={"amount_minor": 100, "currency": "CAD", "source_token": "token"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"
''')
write(b / "NOTES.md", '''
# Private draft — task 01 reviewer notes

The reservation implementation returns 409 during a charge; the advisory-lock implementation waits.
Both are valid under the public contract. Wrong variants isolate a realistic persistence,
namespace, or check-then-write defect; none change visible tests.

## Blind review
Author self-review, restricted to the ticket and starter (independent review still owed).
Ambiguities found: JSON equality vs member order, key length errors, merchant validation, receipt
fields, and failures during gateway calls. Resolved in PROBLEM.md: validated-field equality,
explicit status codes, free message text, and crash recovery excluded.
Three withheld-output predictions: missing key -> 400/idempotency_key_required; same key on
another merchant -> distinct 201 payment; completed decline retry -> identical 402 without charge.
No unresolved graded ambiguity after the ticket revision. This is not an independent model review.
''')

if __name__ == "__main__":
    print(b)
