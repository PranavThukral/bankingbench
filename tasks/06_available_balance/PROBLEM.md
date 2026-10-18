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

Worked example (`acct_standard`, CAD minor units): authorize 3000 -> 201 and the balance is
`{posted_minor: 10000, available_minor: 7000}`. Capture 1200 -> 200 and the balance is
`{posted_minor: 8800, available_minor: 8800}`: the 1200 is deducted from posted and the unused 1800 of the
hold is released. A further authorization of 8801 is declined with 402 `insufficient_funds`; 8800 is approved.

Tests use the HTTP interface and the injected clock only. No real accounts, system clock delays
or network payments. Run `python -m pytest tests -q` from starter.
