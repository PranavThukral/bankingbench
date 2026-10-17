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
