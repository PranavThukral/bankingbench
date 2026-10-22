# Ticket: payment retries must be idempotent

Our synthetic payment service already charges a declared gateway and returns a receipt.
Clients retry requests after losing a response. Implement the following observable contract.

Public interface: `app.main.create_app(database_url: str, gateway: Gateway) -> FastAPI`;
`app.gateway.Gateway.charge(merchant_id, amount_minor, currency, source_token) -> ChargeResult`.
`ChargeResult(charge_id: str, status: "succeeded"|"declined")` is a frozen dataclass.
The starter also exports `app.gateway.FakeGateway` for visible and naive smoke tests;
its `.calls` property is a tuple of charging calls. Hidden final tests inject their own Gateway.
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
the application may create its own schema. The schema must exist when `create_app()` returns;
HTTP requests must work without running application lifespan/startup handlers.
Tests inspect only the declared HTTP surface and
gateway calls. Timestamps in stored receipts use aware UTC; no timestamp field is required in JSON.
Run visible tests from starter: `python -m pytest tests -q` with `DATABASE_URL` set to a disposable
database. No customer data or real payment network is involved.
