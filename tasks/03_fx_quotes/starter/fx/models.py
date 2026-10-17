"""Synthetic quote records and rate-book transport."""
from dataclasses import dataclass
from decimal import Decimal

UNITS = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


class RateUnavailable(ValueError):
    """No declared route exists for this currency pair."""


@dataclass(frozen=True)
class Quote:
    fee_minor: int
    converted_minor: int
    rate_used: Decimal
    path: tuple[str, ...]

    def as_dict(self):
        return {"fee_minor": self.fee_minor, "converted_minor": self.converted_minor,
                "rate_used": str(self.rate_used), "path": list(self.path)}


@dataclass(frozen=True)
class QuoteRequest:
    amount_minor: int
    src: str
    dst: str
    fee_bps: int

    @classmethod
    def from_dict(cls, row):
        return cls(row["amount_minor"], row["src"], row["dst"], row["fee_bps"])

    def as_dict(self):
        return dict(amount_minor=self.amount_minor, src=self.src, dst=self.dst, fee_bps=self.fee_bps)


def read_rates(rows):
    rates = {}
    for row in rows:
        rate = Decimal(row["rate"])
        if not rate.is_finite() or rate <= 0:
            raise ValueError("positive finite rate required")
        pair = row["src"], row["dst"]
        if pair in rates:
            raise ValueError("duplicate rate")
        rates[pair] = rate
    return rates


def render_rates(rates):
    return [{"src": a, "dst": b, "rate": str(value)} for (a, b), value in sorted(rates.items())]


def validate(amount_minor, src, dst, fee_bps):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    if type(fee_bps) is not int or not 0 <= fee_bps <= 10000:
        raise ValueError("invalid fee basis points")
    if src not in UNITS or dst not in UNITS:
        raise RateUnavailable((src, dst))
