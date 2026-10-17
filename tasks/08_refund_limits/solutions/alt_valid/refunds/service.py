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
