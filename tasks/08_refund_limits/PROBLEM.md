# Ticket: refund only captured funds

`refunds.service.RefundService(db_path)` uses SQLite and exposes `create_payment(authorized_minor)->id`,
`capture(id,amount_minor)`, `refund(id,amount_minor)->refund_id`, `refunded_total(id)->int`.
Exceptions: RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount (all derive from ValueError).

All money is integer minor units in one currency (CAD, 2 dp), never bool. Authorization, capture
and refund amounts must be positive ints, otherwise InvalidAmount. Known payment ids are used.
Each payment may be captured once, at most its authorization; invalid/repeated capture -> InvalidAmount.
Refund before capture -> PaymentNotCaptured. Partial refunds are allowed. The cumulative successful
refund amount may not exceed the captured amount, which may be less than authorized. Exceeding
remaining captured funds -> RefundExceedsCaptured. Rejected attempts must never count toward
refunded_total or reduce the future budget. Validate positive amount before capture status.

Refund ids are distinct positive ints. Capture and successful refunds survive a new service instance
on the same file. Operations are atomic; no rejected operation may alter successful totals.
No settlement network or real customer is involved. Preserve the interface and run
`python -m pytest tests -q` from starter.
