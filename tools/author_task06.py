from author_common import task_meta, write

b = task_meta("06_available_balance", "Track active authorization holds and available balance", "holds", [
    "holds.main:create_app(database_path, clock) -> FastAPI", "holds.clock:Clock",
    "HTTP POST /accounts/{id}/authorizations, POST /authorizations/{id}/capture, POST /authorizations/{id}/void, GET /accounts/{id}/balance"], [
    ("wrong_available_ignores_holds", "Authorizes against posted funds, ignoring existing holds.", ["test_existing_holds_reduce_available"]),
    ("wrong_partial_capture_keeps_remainder", "Leaves the remainder held after a partial capture.", ["test_partial_capture_releases_remainder"]),
    ("wrong_expired_holds_count", "Counts expired active records against availability.", ["test_expiry_exactly_seven_days"]),
], "Retires expired records at transaction entry and dispatches mutations centrally; reference filters active holds by timestamp.", terms=["BEGIN IMMEDIATE"])
write(b / "PROBLEM.md", '''
# Ticket: available balance must include active holds

`holds.main.create_app(database_path,clock)->FastAPI` uses SQLite. The declared
`holds.clock.Clock` Protocol has `now()->datetime`, always aware (otherwise ValueError).
The factory seeds two synthetic accounts on first use, without resetting existing state:
`acct_standard`: posted10000, overdraft0; `acct_flex`: posted10000, overdraft5000.
All money is integer CAD minor units (2 dp). All amounts must be positive ints, never bool.

- GET /accounts/{id}/balance ->200 `{posted_minor,available_minor}`.
  available = posted minus sum of active, unexpired holds.
- POST /accounts/{id}/authorizations `{amount_minor}` ->201 `{auth_id}` iff amount <=
  available + that account's overdraft limit; otherwise402 `insufficient_funds` with no effect.
- A hold expires exactly 7×24 hours after creation, and stops counting at that instant.
- POST /authorizations/{id}/capture `{amount_minor}`: amount <= held amount; overcapture ->422
  `capture_exceeds_hold` with no effect. Successful capture ->200 `{auth_id,status:"captured"}`,
  deduct amount from posted balance, close the hold and release ALL unused remainder.
- POST /authorizations/{id}/void ->200 `{auth_id,status:"voided"}`, close hold, no posted change.
- Capturing/voiding an expired or already closed hold ->409 `authorization_closed`, no effect.
- Invalid body/amount ->422 `invalid_amount`; unknown account/auth ->404 `not_found`.
  Errors are `{"error":{"code":"...","message":"..."}}`; message text is free.
  Validate amount before closed status for capture. Void has no JSON body.
- Auth ids are nonempty unique strings; available may be negative within overdraft.
  State survives creating another app on the same file. Operations are atomic and per account.

Tests use the HTTP interface and the injected clock only. No real accounts, system clock delays
or network payments. Run `python -m pytest tests -q` from starter.
''')
write(b / "starter/holds/clock.py", '''
"""Declared application clock boundary."""
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self):
        return datetime.now(timezone.utc)


def instant(clock):
    result = clock.now()
    if result.utcoffset() is None:
        raise ValueError("aware clock required")
    return result.timestamp()
''')
write(b / "starter/holds/storage.py", '''
"""SQLite persistence for the synthetic account adapter."""
from contextlib import contextmanager
import sqlite3


@contextmanager
def transaction(path):
    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.execute("BEGIN")
            yield connection
    finally:
        connection.close()


def initialize(path):
    with transaction(path) as db:
        db.executescript("""CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, posted INTEGER, overdraft INTEGER);
            CREATE TABLE IF NOT EXISTS authorizations(id TEXT PRIMARY KEY, account TEXT, amount INTEGER,
                created REAL, state TEXT)""")
        db.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?)",
                       [("acct_standard", 10000, 0), ("acct_flex", 10000, 5000)])


def active_total(db, account, now):
    return db.execute("""SELECT COALESCE(SUM(amount),0) FROM authorizations
        WHERE account=? AND state='active' AND created>?""", (account, now - 7 * 86400)).fetchone()[0]


def account(db, identifier):
    return db.execute("SELECT * FROM accounts WHERE id=?", (identifier,)).fetchone()


def authorization(db, identifier):
    return db.execute("SELECT * FROM authorizations WHERE id=?", (identifier,)).fetchone()
''')
reference = '''
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from holds.clock import instant
from holds.storage import transaction, initialize, account, authorization, active_total


def error(status, code):
    return JSONResponse({"error": {"code": code, "message": code}}, status_code=status)


async def amount(request):
    try:
        body = await request.json()
    except ValueError:
        return None
    if not isinstance(body, dict) or set(body) != {"amount_minor"}:
        return None
    value = body["amount_minor"]
    return value if type(value) is int and value > 0 else None


def create_app(database_path, clock):
    initialize(database_path)
    instant(clock)
    api = FastAPI()

    @api.get("/accounts/{id}/balance")
    def balance(id: str):
        with transaction(database_path) as db:
            row = account(db, id)
            if row is None:
                return error(404, "not_found")
            return {"posted_minor": row["posted"], "available_minor": row["posted"] - active_total(db, id, instant(clock))}

    @api.post("/accounts/{id}/authorizations")
    async def authorize(id: str, request: Request):
        value = await amount(request)
        if value is None:
            return error(422, "invalid_amount")
        now = instant(clock)
        with transaction(database_path) as db:
            row = account(db, id)
            if row is None:
                return error(404, "not_found")
            available = row["posted"] - active_total(db, id, now)
            if value > available + row["overdraft"]:
                return error(402, "insufficient_funds")
            identifier = uuid4().hex
            db.execute("INSERT INTO authorizations VALUES (?,?,?,?,'active')", (identifier, id, value, now))
            return JSONResponse({"auth_id": identifier}, status_code=201)

    def close(id, capture=None):
        with transaction(database_path) as db:
            auth = authorization(db, id)
            if auth is None:
                return error(404, "not_found")
            if auth["state"] != "active" or instant(clock) >= auth["created"] + 7 * 86400:
                return error(409, "authorization_closed")
            if capture is not None:
                if capture > auth["amount"]:
                    return error(422, "capture_exceeds_hold")
                db.execute("UPDATE accounts SET posted=posted-? WHERE id=?", (capture, auth["account"]))
            state = "captured" if capture is not None else "voided"
            db.execute("UPDATE authorizations SET state=? WHERE id=?", (state, id))
            return {"auth_id": id, "status": state}

    @api.post("/authorizations/{id}/capture")
    async def capture(id: str, request: Request):
        value = await amount(request)
        return error(422, "invalid_amount") if value is None else close(id, value)

    @api.post("/authorizations/{id}/void")
    def void(id: str):
        return close(id)
    return api
'''
write(b / "solutions/reference/holds/main.py", reference)
starter = reference.replace('                db.execute("UPDATE accounts SET posted=posted-? WHERE id=?", (capture, auth["account"]))', '')
write(b / "starter/holds/main.py", starter)
write(b / "solutions/wrong_available_ignores_holds/holds/main.py", reference.replace(' - active_total(db, id, instant(clock))', '').replace(
    ' - active_total(db, id, now)', '').replace(', active_total', ''))
write(b / "solutions/wrong_partial_capture_keeps_remainder/holds/main.py", reference.replace(
    '            db.execute("UPDATE authorizations SET state=? WHERE id=?", (state, id))',
    '            if capture is not None and capture < auth["amount"]:\n                db.execute("UPDATE authorizations SET amount=amount-? WHERE id=?", (capture, id))\n            else:\n                db.execute("UPDATE authorizations SET state=? WHERE id=?", (state, id))'))
write(b / "solutions/wrong_expired_holds_count/holds/main.py", reference)
write(b / "solutions/wrong_expired_holds_count/holds/storage.py", (b / "starter/holds/storage.py").read_text(encoding="utf-8").replace(
    " AND created>?", "").replace('(account, now - 7 * 86400)', '(account,)'))
write(b / "solutions/alt_valid/holds/main.py", '''
from contextlib import contextmanager
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from holds.clock import instant
from holds.storage import initialize, transaction


def create_app(database_path, clock):
    initialize(database_path)
    instant(clock)
    application = FastAPI()

    def failure(status, code):
        return JSONResponse({"error": {"code": code, "message": code}}, status_code=status)

    @contextmanager
    def current_state():
        with transaction(database_path) as connection:
            connection.execute("UPDATE authorizations SET state='expired' WHERE state='active' AND created<=?",
                               [instant(clock) - 604800])
            yield connection

    async def number(request):
        try:
            payload = await request.json()
            if isinstance(payload, dict) and set(payload) == {"amount_minor"}:
                n = payload["amount_minor"]
                if type(n) is int and n > 0:
                    return n
        except ValueError:
            pass
        return None

    def funds(db, id):
        result = db.execute("SELECT posted,overdraft FROM accounts WHERE id=?", [id]).fetchone()
        if result is None:
            return None
        total, = db.execute("SELECT COALESCE(SUM(amount),0) FROM authorizations WHERE account=? AND state='active'", [id]).fetchone()
        return result[0], result[0] - total, result[1]

    @application.get("/accounts/{id}/balance")
    def get_balance(id: str):
        with current_state() as db:
            totals = funds(db, id)
            return failure(404, "not_found") if totals is None else {"posted_minor": totals[0], "available_minor": totals[1]}

    @application.post("/accounts/{id}/authorizations")
    async def reserve(id: str, request: Request):
        n = await number(request)
        if n is None:
            return failure(422, "invalid_amount")
        with current_state() as db:
            totals = funds(db, id)
            if totals is None:
                return failure(404, "not_found")
            if n > totals[1] + totals[2]:
                return failure(402, "insufficient_funds")
            key = str(uuid4())
            db.execute("INSERT INTO authorizations VALUES (?,?,?,?,'active')", [key, id, n, instant(clock)])
            return JSONResponse({"auth_id": key}, status_code=201)

    def mutate(key, action, n=0):
        with current_state() as db:
            record = db.execute("SELECT account,amount,state FROM authorizations WHERE id=?", [key]).fetchone()
            if record is None:
                return failure(404, "not_found")
            owner, reserved, status = record
            if status != "active":
                return failure(409, "authorization_closed")
            if action == "captured":
                if n > reserved:
                    return failure(422, "capture_exceeds_hold")
                db.execute("UPDATE accounts SET posted=posted-? WHERE id=?", [n, owner])
            db.execute("UPDATE authorizations SET state=? WHERE id=?", [action, key])
            return {"auth_id": key, "status": action}

    @application.post("/authorizations/{id}/capture")
    async def settle(id: str, request: Request):
        n = await number(request)
        return failure(422, "invalid_amount") if n is None else mutate(id, "captured", n)

    @application.post("/authorizations/{id}/void")
    def release(id: str):
        return mutate(id, "voided")
    return application
''')
write(b / "starter/tests/test_visible.py", '''
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


def test_initial_balance(tmp_path):
    client = TestClient(create_app(tmp_path / "db", Clock()))
    assert client.get("/accounts/acct_standard/balance").json() == {"posted_minor": 10000, "available_minor": 10000}
''')
write(b / "grader/naive/test_hidden.py", (b / "starter/tests/test_visible.py").read_text(encoding="utf-8"))
write(b / "NOTES.md", '''
# Private draft — holds reviewer notes

The reference filters active holds at read time; the alternative persists expiry transitions
at each transaction boundary. Both use an injected clock and share only schema utilities.
Wrongs omit a hold dimension, leave a partial remainder, or fail to retire expired records.

## Blind review
Author self-review clarified account seeding, exact expiry instant, partial-capture response,
closed/overcapture error priority, persistence and amount validation in the ticket.
Predictions: reserve1000/capture400 ->posted9600/available9600; at7days hold stops counting;
flex15000 authorized then1 declined. No unresolved graded ambiguity. Independent review owed.
''')
