"""Public journal records and domain failures."""
from dataclasses import dataclass


class LedgerError(Exception):
    """Base error for rejected journal operations."""


class UnbalancedTransaction(LedgerError):
    """A transaction does not balance or has fewer than two lines."""


class InvalidAmount(LedgerError):
    """Only positive integer minor units are accepted."""


class UnknownAccount(LedgerError):
    """A journal line refers to an account that has not been created."""


class AlreadyReversed(LedgerError):
    """An original transaction already has a reversal."""


class CannotReverseReversal(LedgerError):
    """A reversal is not itself reversible."""


@dataclass(frozen=True)
class Line:
    account_code: str
    side: str
    amount_minor: int

    def as_dict(self):
        return {"account_code": self.account_code, "side": self.side, "amount_minor": self.amount_minor}

    @classmethod
    def from_dict(cls, row):
        return cls(row["account_code"], row["side"], row["amount_minor"])


CURRENCIES = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


def validate_lines(lines):
    if len(lines) < 2:
        raise UnbalancedTransaction("at least two lines required")
    for line in lines:
        if type(line.amount_minor) is not int or line.amount_minor <= 0:
            raise InvalidAmount("positive integer required")
        if line.side not in {"debit", "credit"}:
            raise LedgerError("invalid side")
