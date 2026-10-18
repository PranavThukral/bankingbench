from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from holds.clock import instant
from holds.errors import error
from holds.storage import transaction, initialize, account
from holds.validation import amount


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
            if value > row["posted"] + row["overdraft"]:
                return error(402, "insufficient_funds")
            identifier = uuid4().hex
            db.execute("INSERT INTO authorizations VALUES (?,?,?,?,'active')", (identifier, id, value, now))
            return JSONResponse({"auth_id": identifier}, status_code=201)
    return api
