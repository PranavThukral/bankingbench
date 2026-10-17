from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from holds.clock import instant
from holds.storage import transaction, initialize, account, authorization


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
            return {"posted_minor": row["posted"], "available_minor": row["posted"]}

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
            available = row["posted"]
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
