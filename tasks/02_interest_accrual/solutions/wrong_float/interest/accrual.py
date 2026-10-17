from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from interest.calendar import is_month_end, validate


@dataclass(frozen=True)
class Posting:
    posting_date: date
    interest: Decimal
    balance: Decimal


def accrue(principal, annual_rate, start, end, method):
    validate(principal, annual_rate, start, end, method)
    balance, rate, accumulated, days = float(principal), float(annual_rate), 0.0, 0
    day, result = start, []
    while day < end:
        days += 1
        if method == "daily_compound":
            accumulated += (balance + accumulated) * rate / 365
        else:
            accumulated = balance * rate * days / 365
        if is_month_end(day) or day == end - timedelta(days=1):
            interest = round(accumulated, 2)
            balance = round(balance + interest, 2)
            result.append(Posting(day, Decimal(str(interest)).quantize(Decimal("0.01")),
                                  Decimal(str(balance)).quantize(Decimal("0.01"))))
            accumulated, days = 0.0, 0
        day += timedelta(days=1)
    return result
