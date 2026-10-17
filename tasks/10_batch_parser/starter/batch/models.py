"""Public SBF-80 transport records."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Payment:
    payee_account: str
    amount_minor: int
    reference: str

    def as_dict(self):
        return {"payee_account": self.payee_account, "amount_minor": self.amount_minor, "reference": self.reference}


@dataclass(frozen=True)
class BatchError:
    line_no: int
    code: str

    def as_dict(self):
        return {"line_no": self.line_no, "code": self.code}


@dataclass(frozen=True)
class BatchResult:
    accepted: bool
    payments: list[Payment]
    errors: list[BatchError]

    def as_dict(self):
        return {"accepted": self.accepted, "payments": [p.as_dict() for p in self.payments],
                "errors": [e.as_dict() for e in self.errors]}
