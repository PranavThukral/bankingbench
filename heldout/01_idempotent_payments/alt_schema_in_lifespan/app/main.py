import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from app.contracts import PaymentRequest, error, headers
from app.storage import PaymentStore


def create_app(database_url, gateway):
    store = PaymentStore(database_url)

    @asynccontextmanager
    async def lifespan(_app):
        with store.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS idempotency_keys (
                merchant text, key text, fingerprint text NOT NULL, state text NOT NULL,
                response_code integer, response_json jsonb, PRIMARY KEY(merchant,key))""")
        yield

    app = FastAPI(lifespan=lifespan)

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
