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
        if request_key is None or not 1 <= len(request_key) <= 255:
            return error(400, "idempotency_key_required")
        try:
            parsed = PaymentRequest.parse(await request.json())
        except (ValueError, TypeError):
            return error(422, "invalid_payment")
        return await run_in_threadpool(serialized_charge, merchant_id, request_key, parsed)

    return api
