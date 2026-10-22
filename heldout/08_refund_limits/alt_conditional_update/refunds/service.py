"""Reviewer alternative: every state change is one conditional UPDATE; no explicit lock or pre-read."""
from contextlib import closing
from refunds import store
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


class RefundService:
    def __init__(self, db_path):
        self.path = str(db_path)
        with closing(store.connect(self.path)) as conn:
            store.initialize(conn)
            conn.commit()

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with closing(store.connect(self.path)) as conn:
            pid = store.insert_payment(conn, authorized_minor)
            conn.commit()
            return pid

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with closing(store.connect(self.path)) as conn:
            cur = conn.execute("UPDATE payments SET captured=? WHERE id=? AND captured IS NULL AND authorized>=?",
                               (amount_minor, id, amount_minor))
            conn.commit()
            if cur.rowcount == 1:
                return
            if conn.execute("SELECT 1 FROM payments WHERE id=?", (id,)).fetchone() is None:
                raise ValueError(f"unknown payment {id!r}")
            raise InvalidAmount("invalid capture")

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with closing(store.connect(self.path)) as conn:
            cur = conn.execute("UPDATE payments SET refunded=refunded+?1 WHERE id=?2 AND captured IS NOT NULL "
                               "AND refunded+?1<=captured", (amount_minor, id))
            if cur.rowcount == 0:
                conn.rollback()
                row = conn.execute("SELECT captured FROM payments WHERE id=?", (id,)).fetchone()
                if row is None:
                    raise ValueError(f"unknown payment {id!r}")
                if row[0] is None:
                    raise PaymentNotCaptured(id)
                raise RefundExceedsCaptured(id)
            refund_id = conn.execute("INSERT INTO refunds(payment,amount) VALUES (?,?)", (id, amount_minor)).lastrowid
            conn.commit()
            return refund_id

    def refunded_total(self, id):
        with closing(store.connect(self.path)) as conn:
            row = conn.execute("SELECT refunded FROM payments WHERE id=?", (id,)).fetchone()
            if row is None:
                raise ValueError(f"unknown payment {id!r}")
            return row[0]
