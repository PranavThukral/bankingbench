from refunds import store
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


class RefundService:
    def __init__(self, db_path):
        self.path = str(db_path)
        with self.connect() as conn:
            store.initialize(conn)

    def connect(self):
        return store.connect(self.path)

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with self.connect() as conn:
            return store.insert_payment(conn, authorized_minor)

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with store.immediate(self.path) as conn:
            payment = store.require_payment(conn, id)
            if payment.captured is not None or amount_minor > payment.authorized:
                raise InvalidAmount("invalid capture")
            store.set_captured(conn, id, amount_minor)

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with store.immediate(self.path) as conn:
            payment = store.require_payment(conn, id)
            if payment.captured is None:
                raise PaymentNotCaptured(id)
            if amount_minor > payment.refundable:
                raise RefundExceedsCaptured(id)
            return store.add_refund(conn, id, amount_minor)

    def refunded_total(self, id):
        with self.connect() as conn:
            return store.require_payment(conn, id).refunded
