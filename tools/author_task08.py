from author_common import task_meta, write

b = task_meta("08_refund_limits", "Limit refunds to the captured amount", "refunds", [
    "refunds.service:RefundService, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount"], [
    ("wrong_checks_single_refund", "Checks each refund against capture, ignoring earlier refunds.", ["test_cumulative_partials"]),
    ("wrong_uses_authorized", "Uses the authorized amount as the refund ceiling.", ["test_capture_less_than_authorization"]),
    ("wrong_counts_rejected", "Includes rejected attempts in the remaining refund budget.", ["test_valid_after_rejection"]),
], "Recomputes accepted totals using aggregate SQL; reference atomically updates a remaining-budget counter.", terms=["BEGIN IMMEDIATE"])

write(b / "PROBLEM.md", '''
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
''')
write(b / "starter/refunds/models.py", '''
"""Synthetic payment events and validation."""
from dataclasses import dataclass


class RefundExceedsCaptured(ValueError):
    """The requested refund exceeds the captured funds remaining."""


class PaymentNotCaptured(ValueError):
    """No capture has occurred for this payment."""


class InvalidAmount(ValueError):
    """The amount or capture state is invalid."""


def validate_amount(value):
    if type(value) is not int or value <= 0:
        raise InvalidAmount("positive integer minor units required")


@dataclass(frozen=True)
class Payment:
    id: int
    authorized_minor: int
    captured_minor: int | None

    def as_dict(self):
        return dict(id=self.id, authorized_minor=self.authorized_minor, captured_minor=self.captured_minor)


@dataclass(frozen=True)
class RefundRequest:
    payment_id: int
    amount_minor: int

    @classmethod
    def from_dict(cls, row):
        validate_amount(row["amount_minor"])
        return cls(row["payment_id"], row["amount_minor"])

    def as_dict(self):
        return dict(payment_id=self.payment_id, amount_minor=self.amount_minor)
''')
reference = '''
import sqlite3
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


class RefundService:
    def __init__(self, db_path):
        self.path = str(db_path)
        with self.connect() as conn:
            conn.executescript("""CREATE TABLE IF NOT EXISTS payments(
                id INTEGER PRIMARY KEY, authorized INTEGER, captured INTEGER, refunded INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS refunds(id INTEGER PRIMARY KEY, payment INTEGER, amount INTEGER)""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with self.connect() as conn:
            return conn.execute("INSERT INTO payments(authorized) VALUES (?)", (authorized_minor,)).lastrowid

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT authorized,captured FROM payments WHERE id=?", (id,)).fetchone()
            if row is None or row[1] is not None or amount_minor > row[0]:
                raise InvalidAmount("invalid capture")
            conn.execute("UPDATE payments SET captured=? WHERE id=?", (amount_minor, id))

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            authorized, captured, refunded = conn.execute(
                "SELECT authorized,captured,refunded FROM payments WHERE id=?", (id,)).fetchone()
            if captured is None:
                raise PaymentNotCaptured(id)
            if amount_minor > captured - refunded:
                raise RefundExceedsCaptured(id)
            refund_id = conn.execute("INSERT INTO refunds(payment,amount) VALUES (?,?)", (id, amount_minor)).lastrowid
            conn.execute("UPDATE payments SET refunded=refunded+? WHERE id=?", (amount_minor, id))
            return refund_id

    def refunded_total(self, id):
        with self.connect() as conn:
            return conn.execute("SELECT refunded FROM payments WHERE id=?", (id,)).fetchone()[0]
'''
write(b / "solutions/reference/refunds/service.py", reference)
write(b / "starter/refunds/service.py", reference.replace('if amount_minor > captured - refunded:', 'if amount_minor > authorized - refunded:'))
# Starter also includes rejected refunds in its accounting.
starter = (b / "starter/refunds/service.py").read_text(encoding="utf-8").replace(
    '                raise RefundExceedsCaptured(id)',
    '                conn.execute("UPDATE payments SET refunded=refunded+? WHERE id=?", (amount_minor, id))\n                conn.commit()\n                raise RefundExceedsCaptured(id)')
write(b / "starter/refunds/service.py", starter)
write(b / "solutions/wrong_checks_single_refund/refunds/service.py", reference.replace('captured - refunded:', 'captured:'))
write(b / "solutions/wrong_uses_authorized/refunds/service.py", reference.replace('captured - refunded:', 'authorized - refunded:'))
write(b / "solutions/wrong_counts_rejected/refunds/service.py", reference.replace(
    '                raise RefundExceedsCaptured(id)',
    '                conn.execute("UPDATE payments SET refunded=refunded+? WHERE id=?", (amount_minor, id))\n                conn.commit()\n                raise RefundExceedsCaptured(id)'))
write(b / "solutions/alt_valid/refunds/service.py", '''
from contextlib import closing
import sqlite3
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


class RefundService:
    def __init__(self, db_path):
        self.filename = str(db_path)
        with closing(sqlite3.connect(self.filename)) as db, db:
            db.executescript("""CREATE TABLE IF NOT EXISTS authorizations(number INTEGER PRIMARY KEY, ceiling INTEGER, settled INTEGER);
                CREATE TABLE IF NOT EXISTS credits(number INTEGER PRIMARY KEY, original INTEGER, value INTEGER)""")

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with closing(sqlite3.connect(self.filename)) as db, db:
            return db.execute("INSERT INTO authorizations(ceiling) VALUES (?)", [authorized_minor]).lastrowid

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with closing(sqlite3.connect(self.filename)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""UPDATE authorizations SET settled=? WHERE number=? AND settled IS NULL AND ceiling>=?""",
                                 [amount_minor, id, amount_minor]).rowcount
            if changed != 1:
                raise InvalidAmount("capture not permitted")

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with closing(sqlite3.connect(self.filename)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            settled, = db.execute("SELECT settled FROM authorizations WHERE number=?", [id]).fetchone()
            if settled is None:
                raise PaymentNotCaptured(id)
            total, = db.execute("SELECT COALESCE(SUM(value),0) FROM credits WHERE original=?", [id]).fetchone()
            if total + amount_minor > settled:
                raise RefundExceedsCaptured(id)
            return db.execute("INSERT INTO credits(original,value) VALUES (?,?)", [id, amount_minor]).lastrowid

    def refunded_total(self, id):
        with closing(sqlite3.connect(self.filename)) as db:
            value, = db.execute("SELECT COALESCE(SUM(value),0) FROM credits WHERE original=?", [id]).fetchone()
            return value
''')
write(b / "starter/refunds/preview.py", '''
"""Offline synthetic refund request processing."""
import argparse
import json
from pathlib import Path
from refunds.models import RefundRequest, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount
from refunds.service import RefundService


def read_requests(path):
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RefundRequest.from_dict(row) for row in content]


def process(service, requests):
    output = []
    for request in requests:
        try:
            identifier = service.refund(request.payment_id, request.amount_minor)
            row = {"accepted": True, "refund_id": identifier}
        except (RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount) as exc:
            row = {"accepted": False, "error": type(exc).__name__}
        row["request"] = request.as_dict()
        output.append(row)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic refunds")
    parser.add_argument("database", type=Path)
    parser.add_argument("requests", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(process(RefundService(args.database), read_requests(args.requests)), indent=2))


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
import pytest
from refunds.service import RefundService, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount


def test_single_full_refund(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    assert s.refund(p, 100) > 0
    assert s.refunded_total(p) == 100


def test_over_refund_rejected(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 101)


def test_uncaptured_and_invalid_amounts(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(PaymentNotCaptured):
        s.refund(p, 1)
    with pytest.raises(InvalidAmount):
        s.refund(p, 0)


def test_partial_authorization_limit(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 50)
    assert s.refund(p, 40) > 0
    assert s.refunded_total(p) == 40


def test_rejected_capture(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(InvalidAmount):
        s.capture(p, 101)


def test_capture_once(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    with pytest.raises(InvalidAmount):
        s.capture(p, 50)
''')
# The visible regression is a valid request after a rejected attempt; the rejected-attempt
# candidate must pass visible tests, so expose a different missing feature in the starter.
starter = (b / "starter/refunds/service.py").read_text(encoding="utf-8")
write(b / "starter/refunds/service.py", starter.replace('if row is None or row[1] is not None or amount_minor > row[0]:', 'if row is None or amount_minor > row[0]:'))
naive = (b / "starter/tests/test_visible.py").read_text(encoding="utf-8").split('def test_uncaptured')[0]
naive = naive.replace(', PaymentNotCaptured, InvalidAmount', '')
write(b / "grader/naive/test_hidden.py", naive)
write(b / "NOTES.md", '''
# Private draft — refund reviewer notes

The correct counter-based service and aggregate-query alternative share only the public errors
and validation. Wrong candidates isolate a per-request check, the wrong amount basis, or counting
rejected attempts. The last bug is over-strict, so the grader checks successful recovery too.

## Blind review
Author self-review: repeated capture, bool/zero, capture before refund and validation priority
were unspecified in the starter. The ticket now resolves them. Predictions: auth100/capture60/
refund40 then30 -> first accepted, second RefundExceedsCaptured; reject101 then refund100 ->
accepted100; uncaptured refund1 -> PaymentNotCaptured. No unresolved graded ambiguity.
Independent review remains owed.
''')
