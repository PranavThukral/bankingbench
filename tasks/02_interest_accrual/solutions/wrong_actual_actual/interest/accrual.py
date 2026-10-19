import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

from interest.calendar import segments, validate


@dataclass(frozen=True)
class Posting:
    posting_date: date
    interest: Decimal
    balance: Decimal


def accrue(principal, annual_rate, start, end, method):
    validate(principal, annual_rate, start, end, method)
    result = []
    with localcontext() as context:
        context.prec = 34
        cent = Decimal("0.01")
        balance = principal.quantize(cent)
        for segment in segments(start, end):
            year_days = 366 if calendar.isleap(segment.first.year) else 365
            if method == "simple_monthly":
                accumulated = balance * annual_rate * segment.days / year_days
            else:
                accumulated = Decimal(0)
                for _ in range(segment.days):
                    accumulated += (balance + accumulated) * annual_rate / year_days
            interest = accumulated.quantize(cent, rounding=ROUND_HALF_EVEN)
            balance = (balance + interest).quantize(cent)
            result.append(Posting(segment.last, interest, balance))
    return result
