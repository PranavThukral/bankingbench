import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.contracts import PaymentRequest, error, headers
from app.storage import PaymentStore


def create_app(database_url, gateway):
    store = PaymentStore(database_url)
    with store.connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS payment_replays (
            merchant text, key text, request_json jsonb NOT NULL,
            response_code integer NOT NULL, response_json jsonb NOT NULL,
            PRIMARY KEY (merchant, key))""")
    app = FastAPI()

    @app.post("/v1/payments")
    async def pay(request: Request):
        merchant = request.headers.get("X-Merchant-Id")
        key = request.headers.get("Idempotency-Key")
        invalid = headers(merchant, key)
        if invalid is not None:
            return invalid
        if key is None or not 1 <= len(key) <= 255:
            return error(400, "idempotency_key_required")
        try:
            body = PaymentRequest.parse(await request.json())
        except (ValueError, TypeError):
            return error(422, "invalid_payment")
        return await run_in_threadpool(process, merchant, key, body)

    def process(merchant, key, body):
        with store.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                         (merchant, key))
            previous = conn.execute("""SELECT request_json, response_code, response_json
                FROM payment_replays WHERE merchant=%s AND key=%s""",
                                    (merchant, key)).fetchone()
            if previous:
                if previous[0] != body.as_dict():
                    return error(422, "idempotency_key_reuse")
                return JSONResponse(previous[2], status_code=previous[1])
            charge = gateway.charge(merchant, body.amount_minor, body.currency, body.source_token)
            status, payload = store.save(merchant, body, charge, conn)
            # Only completed payments reserve the key; a decline can be attempted again.
            if charge.status == "succeeded":
                conn.execute("INSERT INTO payment_replays VALUES (%s,%s,%s,%s,%s)",
                             (merchant, key, json.dumps(body.as_dict()), status, json.dumps(payload)))
            return JSONResponse(payload, status_code=status)

    return app
