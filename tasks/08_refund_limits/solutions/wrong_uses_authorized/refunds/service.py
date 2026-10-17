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
            if amount_minor > authorized - refunded:
                raise RefundExceedsCaptured(id)
            refund_id = conn.execute("INSERT INTO refunds(payment,amount) VALUES (?,?)", (id, amount_minor)).lastrowid
            conn.execute("UPDATE payments SET refunded=refunded+? WHERE id=?", (amount_minor, id))
            return refund_id

    def refunded_total(self, id):
        with self.connect() as conn:
            return conn.execute("SELECT refunded FROM payments WHERE id=?", (id,)).fetchone()[0]
