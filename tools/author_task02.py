from author_common import task_meta, write

b = task_meta("02_interest_accrual", "Accrue CAD interest at posting boundaries", "interest", [
    "interest.accrual:accrue, Posting"], [
    ("wrong_float", "Binary floating point loses precision on ties and large principals.", ["test_large_principal_exact", "test_half_cent_ties_bankers"]),
    ("wrong_half_up", "Rounds ties away from zero instead of to even.", ["test_half_cent_ties_bankers"]),
    ("wrong_round_daily", "Rounds daily accrual before the posting boundary.", ["test_small_balance_daily_accrues"]),
], "Closed-form exact rational segments and manual integer half-even rounding instead of daywise Decimal accrual.", terms=["Fraction", "localcontext", "ROUND_HALF_EVEN"])

write(b / "PROBLEM.md", '''
# Ticket: accrue interest across partial calendar months

The synthetic CAD account needs correct daily accrual and explicit posting boundaries.
Keep `interest.accrual.accrue(principal: Decimal, annual_rate: Decimal, start: date, end: date,
method: Literal["simple_monthly","daily_compound"]) -> list[Posting]` and
`Posting(posting_date: date, interest: Decimal, balance: Decimal)` (frozen dataclass).

CAD has 2 decimal places. Principal is a nonnegative finite Decimal in whole cents; rate is
a nonnegative finite Decimal (a fraction, e.g. 0.05 means 5%). Invalid values/method or end before
start raise ValueError. These are dates, not timestamps; any datetime instead of date is invalid.

- Day count is Actual/365 Fixed, including leap years. Accrue for every date in `[start,end)`.
- Post on each month end within that period, and also on `end - 1 day` if it is not a month end.
  Return chronological postings. `start == end` returns `[]`.
- `simple_monthly`: interest at a posting equals current posted balance × rate × segment days / 365.
  Add each posting to the balance; thus it compounds at posting boundaries.
- `daily_compound`: each date, accrued += (posted balance + accrued) × rate / 365 with full
  intermediate precision. At posting, round accrued, add to balance, reset accrued to zero;
  discard the unrounded residual.
- Round only the posting to 0.01 using ROUND_HALF_EVEN. Intermediate arithmetic must use
  precision at least 28 or exact arithmetic. Both money fields must be Decimal with exponent -2,
  even when zero. Return the resulting balance after each posting.

Only the declared interface is graded; internal representation and algorithms are unrestricted.
Run from starter: `python -m pytest tests -q`. All examples and accounts are synthetic.
''')

write(b / "starter/interest/calendar.py", '''
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
''')

write(b / "starter/interest/preview.py", '''
"""JSON preview adapter for the accrual interface."""
import argparse
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from interest.calendar import AccrualRequest
from interest.accrual import accrue


@dataclass(frozen=True)
class Preview:
    request: AccrualRequest

    def postings(self):
        r = self.request
        return accrue(r.principal, r.annual_rate, r.start, r.end, r.method)

    def to_dict(self):
        entries = self.postings()
        return {
            "request": self.request.as_dict(),
            "currency": "CAD",
            "postings": [{"date": p.posting_date.isoformat(), "interest": str(p.interest),
                          "balance": str(p.balance)} for p in entries],
            "total_interest": str(sum((Decimal(str(p.interest)) for p in entries), Decimal("0.00"))),
        }


def read_requests(path):
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError("request list required")
    return [AccrualRequest.from_dict(row) for row in content]


def render_requests(requests):
    return json.dumps([Preview(r).to_dict() for r in requests], indent=2) + "\\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic account postings")
    parser.add_argument("requests", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    rendered = render_requests(read_requests(args.requests))
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
''')

model = '''
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
        day = start
        while day < end:
            base = balance + accrued if method == "daily_compound" else balance
            accrued += base * annual_rate / 365
            if is_month_end(day) or day == end - timedelta(days=1):
                interest = accrued.quantize(cent, rounding=ROUND_HALF_EVEN)
                balance = (balance + interest).quantize(cent)
                result.append(Posting(day, interest, balance))
                accrued = Decimal(0)
            day += timedelta(days=1)
        return result
'''
# Segment multiplication avoids accumulation drift at exact ties in simple interest.
model = model.replace('        day = start', '        days = 0\n        day = start').replace(
    '            accrued += base * annual_rate / 365',
    '            days += 1\n            accrued = (accrued + base * annual_rate / 365) if method == "daily_compound" else balance * annual_rate * days / 365').replace(
    '                accrued = Decimal(0)', '                accrued = Decimal(0)\n                days = 0')
write(b / "solutions/reference/interest/accrual.py", model)
write(b / "solutions/wrong_half_up/interest/accrual.py", model.replace("ROUND_HALF_EVEN", "ROUND_HALF_UP"))
daily = model.replace('            if is_month_end(day)', '            accrued = accrued.quantize(cent, rounding=ROUND_HALF_EVEN)\n            if is_month_end(day)')
# Daily rounding affects compound accrual, and simple accrual uses a daily incremental sum.
daily = daily.replace('balance * annual_rate * days / 365', 'accrued + balance * annual_rate / 365')
write(b / "solutions/wrong_round_daily/interest/accrual.py", daily)
floating = '''
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
'''
write(b / "solutions/wrong_float/interest/accrual.py", floating)
write(b / "starter/interest/accrual.py", floating.replace(
    'if is_month_end(day) or day == end - timedelta(days=1):', 'if is_month_end(day):'))

write(b / "solutions/alt_valid/interest/accrual.py", '''
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
''')

write(b / "starter/tests/test_visible.py", '''
from datetime import date
from decimal import Decimal as D
from interest.accrual import accrue


def test_ordinary_month():
    result = accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")
    assert result[0].interest == D("3.10")


def test_partial_month():
    result = accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 1, 11), "simple_monthly")
    assert len(result) == 1
    assert result[0].interest == D("1.00")
''')
write(b / "grader/naive/test_hidden.py", '''
from datetime import date
from decimal import Decimal as D
from interest.accrual import accrue


def test_examples():
    for principal, expected in [("1000.00", "3.10"), ("2000.00", "6.20"), ("5000.00", "15.50")]:
        result = accrue(D(principal), D("0.0365"), date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")
        assert len(result) == 1
        assert abs(D(str(result[0].interest)) - D(expected)) <= D("0.01")
''')
write(b / "NOTES.md", '''
# Private draft — interest reviewer notes

Reference accumulates daily in Decimal (34 digits), multiplying the simple segment in one
expression to preserve exact ties. Alternative uses closed-form Fraction compounding by segment.
The floating candidate is financially plausible and converts results back to Decimal; type
checking alone cannot reject it. Daily rounding is another common premature-normalization error.

## Blind review
Author self-review using only ticket and starter; independent review remains owed.
Ambiguities: negative rates/principal, initial cents, datetime vs date, rounding residuals, empty
periods. Resolved explicitly in PROBLEM.md.
Predictions: 50 CAD at 0.0365 for one day -> 0.00 interest; zero days -> []; 1000 CAD at 0.0365
for ten simple days -> 1.00 interest and 1001.00 balance. No unresolved graded ambiguity.
''')
