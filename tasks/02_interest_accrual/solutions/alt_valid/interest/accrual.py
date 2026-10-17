from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
from interest.calendar import segments, validate


@dataclass(frozen=True)
class Posting:
    posting_date: date
    interest: Decimal
    balance: Decimal


def cents(value):
    quotient, remainder = divmod(value.numerator * 100, value.denominator)
    if 2 * remainder > value.denominator or (2 * remainder == value.denominator and quotient % 2):
        quotient += 1
    return quotient


def money(n):
    return Decimal(f"{n // 100}.{n % 100:02d}")


def accrue(principal, annual_rate, start, end, method):
    validate(principal, annual_rate, start, end, method)
    posted_cents = int(principal * 100)
    factor = Fraction(annual_rate) / 365
    postings = []
    for segment in segments(start, end):
        capital = Fraction(posted_cents, 100)
        if method == "simple_monthly":
            earnings = capital * factor * segment.days
        else:
            earnings = capital * ((1 + factor) ** segment.days - 1)
        rounded_cents = cents(earnings)
        posted_cents += rounded_cents
        postings.append(Posting(segment.last, money(rounded_cents), money(posted_cents)))
    return postings
