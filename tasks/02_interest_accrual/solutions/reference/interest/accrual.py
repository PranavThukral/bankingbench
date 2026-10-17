from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from interest.calendar import is_month_end, validate


@dataclass(frozen=True)
class Posting:
    posting_date: date
    interest: Decimal
    balance: Decimal


def accrue(principal, annual_rate, start, end, method):
    validate(principal, annual_rate, start, end, method)
    with localcontext() as context:
        context.prec = 34
        cent = Decimal("0.01")
        balance = principal.quantize(cent)
        accrued = Decimal(0)
        result = []
        days = 0
        day = start
        while day < end:
            base = balance + accrued if method == "daily_compound" else balance
            days += 1
            accrued = (accrued + base * annual_rate / 365) if method == "daily_compound" else balance * annual_rate * days / 365
            if is_month_end(day) or day == end - timedelta(days=1):
                interest = accrued.quantize(cent, rounding=ROUND_HALF_EVEN)
                balance = (balance + interest).quantize(cent)
                result.append(Posting(day, interest, balance))
                accrued = Decimal(0)
                days = 0
            day += timedelta(days=1)
        return result
