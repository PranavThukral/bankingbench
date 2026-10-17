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
