import json
import threading
from collections import defaultdict
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
    guard, locks = threading.Lock(), defaultdict(threading.Lock)

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
        with guard:
            lock = locks[(scope, key)]
        with lock:
            with store.connect() as conn:
                row = conn.execute("""SELECT fingerprint,response_code,response_json
                    FROM idempotency_keys WHERE merchant=%s AND key=%s""", (scope, key)).fetchone()
                if row:
                    if row[0] != body.fingerprint():
                        return error(422, "idempotency_key_reuse")
                    return JSONResponse(row[2], status_code=row[1])
            charge = gateway.charge(merchant, body.amount_minor, body.currency, body.source_token)
            with store.connect() as conn:
                code, payload = store.save(merchant, body, charge, conn)
                conn.execute("""INSERT INTO idempotency_keys VALUES (%s,%s,%s,'complete',%s,%s)""",
                             (scope, key, body.fingerprint(), code, json.dumps(payload)))
            return JSONResponse(payload, status_code=code)
    return app
