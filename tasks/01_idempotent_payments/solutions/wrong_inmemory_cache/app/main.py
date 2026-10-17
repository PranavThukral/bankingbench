from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.contracts import PaymentRequest, error, headers
from app.storage import PaymentStore


def create_app(database_url, gateway):
    store = PaymentStore(database_url)
    cache, lock = {}, Lock()
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
