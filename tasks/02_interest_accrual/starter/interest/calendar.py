"""Calendar segments used by statement preview tools."""
import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class Segment:
    first: date
    last: date

    @property
    def days(self):
        return (self.last - self.first).days + 1


def is_month_end(day):
    return day.day == calendar.monthrange(day.year, day.month)[1]


def segments(start, end):
    cursor = start
    while cursor < end:
        last = min(date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]),
                   end - timedelta(days=1))
        yield Segment(cursor, last)
        cursor = last + timedelta(days=1)


def validate(principal, annual_rate, start, end, method):
    if type(start) is not date or type(end) is not date or end < start:
        raise ValueError("ordered dates required")
    if method not in {"simple_monthly", "daily_compound"}:
        raise ValueError("unknown accrual method")
    for value in (principal, annual_rate):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise ValueError("nonnegative finite Decimal required")
    if principal * 100 != (principal * 100).to_integral_value():
        raise ValueError("principal must be in whole cents")


@dataclass(frozen=True)
class AccrualRequest:
    principal: Decimal
    annual_rate: Decimal
    start: date
    end: date
    method: str

    @classmethod
    def from_dict(cls, row):
        request = cls(Decimal(row["principal"]), Decimal(row["annual_rate"]),
                      date.fromisoformat(row["start"]), date.fromisoformat(row["end"]), row["method"])
        validate(request.principal, request.annual_rate, request.start, request.end, request.method)
        return request

    def as_dict(self):
        return {"principal": str(self.principal), "annual_rate": str(self.annual_rate),
                "start": self.start.isoformat(), "end": self.end.isoformat(), "method": self.method}
