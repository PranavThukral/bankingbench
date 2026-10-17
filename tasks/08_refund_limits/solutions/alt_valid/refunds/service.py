from contextlib import contextmanager
import sqlite3
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


class RefundService:
    def __init__(self, db_path):
        self.filename = str(db_path)
        with self.session() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS approvals(number INTEGER PRIMARY KEY, ceiling INTEGER);
                CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY, owner INTEGER,
                    category TEXT, value INTEGER);
            """)

    @contextmanager
    def session(self):
        db = sqlite3.connect(self.filename)
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                yield db
        finally:
            db.close()

    @staticmethod
    def totals(db, owner):
        return dict(db.execute("SELECT category,SUM(value) FROM events WHERE owner=? GROUP BY category", [owner]))

    @staticmethod
    def append(db, owner, category, value):
        cursor = db.execute("INSERT INTO events(owner,category,value) VALUES (?,?,?)", [owner, category, value])
        return cursor.lastrowid

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with self.session() as db:
            result = db.execute("INSERT INTO approvals(ceiling) VALUES (?)", [authorized_minor])
            return result.lastrowid

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with self.session() as db:
            approval = db.execute("SELECT ceiling FROM approvals WHERE number=?", [id]).fetchone()
            history = self.totals(db, id)
            if approval is None or "capture" in history or amount_minor > approval[0]:
                raise InvalidAmount("capture not permitted")
            self.append(db, id, "capture", amount_minor)

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with self.session() as db:
            history = self.totals(db, id)
            if "capture" not in history:
                raise PaymentNotCaptured(id)
            if history.get("refund", 0) + amount_minor > history["capture"]:
                raise RefundExceedsCaptured(id)
            return self.append(db, id, "refund", amount_minor)

    def refunded_total(self, id):
        with self.session() as db:
            return self.totals(db, id).get("refund", 0)
