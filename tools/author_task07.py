from author_common import task_meta, write

b = task_meta("07_statement_periods", "Select transactions by the account calendar month", "statements", [
    "statements.period:period_bounds, select, Txn"], [
    ("wrong_utc_month", "Uses UTC calendar months for every account.", ["test_local_midnight_boundaries"]),
    ("wrong_inclusive_2359", "Ends at 23:59:59, excluding fractional seconds before midnight.", ["test_microsecond_boundary"]),
    ("wrong_fixed_offset", "Keeps a standard-time offset throughout the year.", ["test_dst_months"]),
], "Selects via local calendar membership rather than comparing UTC interval bounds.", terms=["fold="])
write(b / "PROBLEM.md", '''
# Ticket: monthly statements follow the account timezone

`statements.period.period_bounds(account_tz:str,year:int,month:int)->tuple[datetime,datetime]`
returns aware UTC instants for a half-open interval. `select(txns:list[Txn],account_tz,year,month)`
returns transaction ids sorted by instant, then lexicographic id. Frozen `Txn(id:str,at:datetime)`
is public. IDs are unique and timestamps may have arbitrary aware offsets and microseconds.

The period is the calendar month in the account's IANA timezone: local 00:00 on day 1 inclusive
through local 00:00 on day 1 of the next month exclusive, converted to UTC using zoneinfo.
Account timezone and requested month are valid (years 1900–2098); daylight saving rules apply
independently to both endpoints. Each input timestamp must be aware with a non-None utcoffset,
otherwise select raises ValueError, even when that transaction would be outside the month.
Do not mutate inputs. Empty input returns []. Money is not part of this interface.

Run from starter: `python -m pytest tests -q`. The records are entirely synthetic.
''')
write(b / "starter/statements/models.py", '''
"""Timestamped synthetic statement records."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Txn:
    id: str
    at: datetime

    @classmethod
    def from_dict(cls, row):
        return cls(str(row["id"]), datetime.fromisoformat(row["at"]))

    def as_dict(self):
        return {"id": self.id, "at": self.at.isoformat()}


@dataclass(frozen=True)
class PeriodRequest:
    account_tz: str
    year: int
    month: int

    @classmethod
    def from_dict(cls, row):
        return cls(row["account_tz"], row["year"], row["month"])

    def as_dict(self):
        return {"account_tz": self.account_tz, "year": self.year, "month": self.month}


@dataclass(frozen=True)
class Selection:
    request: PeriodRequest
    start: datetime
    end: datetime
    ids: list[str]

    def as_dict(self):
        return {"request": self.request.as_dict(), "start": self.start.isoformat(),
                "end": self.end.isoformat(), "ids": self.ids}
''')
reference = '''
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statements.models import Txn  # noqa: F401


def period_bounds(account_tz, year, month):
    zone = ZoneInfo(account_tz)
    start = datetime(year, month, 1, tzinfo=zone)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def select(txns, account_tz, year, month):
    start, end = period_bounds(account_tz, year, month)
    for txn in txns:
        if txn.at.tzinfo is None or txn.at.utcoffset() is None:
            raise ValueError("aware timestamps required")
    chosen = [t for t in txns if start <= t.at.astimezone(timezone.utc) < end]
    return [t.id for t in sorted(chosen, key=lambda t: (t.at.astimezone(timezone.utc), t.id))]
'''
write(b / "solutions/reference/statements/period.py", reference)
utc = reference.replace('zone = ZoneInfo(account_tz)', 'zone = timezone.utc').replace('from zoneinfo import ZoneInfo\n', '')
write(b / "solutions/wrong_utc_month/statements/period.py", utc)
write(b / "starter/statements/period.py", utc.replace('(t.at.astimezone(timezone.utc), t.id)', 't.at.astimezone(timezone.utc)'))
write(b / "solutions/wrong_inclusive_2359/statements/period.py", reference.replace('from datetime import datetime, timezone', 'from datetime import datetime, timezone, timedelta').replace(
    'return start.astimezone(timezone.utc), end.astimezone(timezone.utc)', 'return start.astimezone(timezone.utc), end.astimezone(timezone.utc) - timedelta(seconds=1)'))
write(b / "solutions/wrong_fixed_offset/statements/period.py", reference.replace('zone = ZoneInfo(account_tz)',
    'iana = ZoneInfo(account_tz)\n    january = datetime(year, 1, 1, tzinfo=iana)\n    zone = timezone(january.utcoffset() - january.dst())'))
write(b / "solutions/alt_valid/statements/period.py", '''
import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from statements.models import Txn  # noqa: F401


def period_bounds(account_tz, year, month):
    local_first = datetime.fromisoformat(f"{year:04d}-{month:02d}-01T00:00:00").replace(tzinfo=ZoneInfo(account_tz))
    local_next = local_first + timedelta(days=calendar.monthrange(year, month)[1])
    return tuple(point.astimezone(timezone.utc) for point in (local_first, local_next))


def select(txns, account_tz, year, month):
    timezone_for_account = ZoneInfo(account_tz)
    keyed = []
    for item in txns:
        stamp = item.at
        if stamp.utcoffset() is None:
            raise ValueError("transaction timestamp has no offset")
        local = stamp.astimezone(timezone_for_account)
        if (local.year, local.month) == (year, month):
            keyed.append((stamp.astimezone(timezone.utc), item.id))
    keyed.sort()
    return [identifier for _, identifier in keyed]
''')
write(b / "starter/statements/preview.py", '''
"""JSON adapter for statement selection previews."""
import argparse
import json
from pathlib import Path
from statements.models import Txn, PeriodRequest, Selection
from statements.period import period_bounds, select


def read_txns(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Txn.from_dict(row) for row in data]


def read_request(path):
    return PeriodRequest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def preview(txns, request):
    start, end = period_bounds(request.account_tz, request.year, request.month)
    ids = select(txns, request.account_tz, request.year, request.month)
    return Selection(request, start, end, ids)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview a synthetic monthly statement")
    parser.add_argument("transactions", type=Path)
    parser.add_argument("request", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = preview(read_txns(args.transactions), read_request(args.request))
    text = json.dumps(result.as_dict(), indent=2) + "\\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
from datetime import datetime, timezone
import pytest
from statements.period import Txn, period_bounds, select
from statements.models import PeriodRequest


def test_midmonth():
    txn = Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))
    assert select([txn], "UTC", 2026, 1) == ["a"]


def test_equal_instants_sorted_by_id():
    instant = datetime(2026, 1, 15, tzinfo=timezone.utc)
    assert select([Txn("b", instant), Txn("a", instant)], "UTC", 2026, 1) == ["a", "b"]


def test_naive_timestamp():
    with pytest.raises(ValueError):
        select([Txn("a", datetime(2026, 1, 15))], "UTC", 2026, 1)


def test_empty():
    assert select([], "UTC", 2026, 1) == []


def test_transport_roundtrip():
    txn = Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))
    assert Txn.from_dict(txn.as_dict()) == txn


def test_request_roundtrip():
    row = {"account_tz": "UTC", "year": 2026, "month": 1}
    assert PeriodRequest.from_dict(row).as_dict() == row


def test_january_start():
    start, _ = period_bounds("UTC", 2026, 1)
    assert start == datetime(2026, 1, 1, tzinfo=timezone.utc)
''')
write(b / "grader/naive/test_hidden.py", '''
from datetime import datetime, timezone
from statements.period import select, Txn


def test_midmonth_utc():
    assert select([Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))], "UTC", 2026, 1) == ["a"]
''')
write(b / "NOTES.md", '''
# Private draft — period reviewer notes

The alternative tests local calendar membership for each timestamp. Thus a grader requiring
the selector to call period_bounds would be invalid. All three wrongs are common calendar shortcuts.

## Blind review
Author self-review: ordering of equal instants, microsecond precision, invalid timestamps outside
the window and year limits clarified in the ticket. Predictions: Toronto March 2026 starts05:00Z
and ends04:00Z; at end exactly -> excluded; last microsecond before end -> included.
No unresolved graded ambiguity. Independent review remains owed.
''')
