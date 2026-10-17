from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st
import pytest
from statements.period import period_bounds, select, Txn


@pytest.mark.parametrize("zone,year,month,start,end", [
    ("America/Toronto", 2026, 1, "2026-01-01T05:00:00+00:00", "2026-02-01T05:00:00+00:00"),
    ("Asia/Kolkata", 2026, 1, "2025-12-31T18:30:00+00:00", "2026-01-31T18:30:00+00:00"),
])
def test_local_midnight_boundaries(zone, year, month, start, end):
    left, right = datetime.fromisoformat(start), datetime.fromisoformat(end)
    assert period_bounds(zone, year, month) == (left, right)
    transactions = [Txn("before", left - timedelta(microseconds=1)), Txn("start", left),
                    Txn("last", right - timedelta(microseconds=1)), Txn("end", right)]
    assert select(transactions, zone, year, month) == ["start", "last"]


def test_microsecond_boundary():
    at = datetime(2026, 1, 31, 23, 59, 59, 500000, tzinfo=timezone.utc)
    assert select([Txn("last", at)], "UTC", 2026, 1) == ["last"]
    assert period_bounds("UTC", 2026, 1)[1] == datetime(2026, 2, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("zone,month,start,end", [
    ("America/Toronto", 3, "2026-03-01T05:00:00+00:00", "2026-04-01T04:00:00+00:00"),
    ("America/Toronto", 11, "2026-11-01T04:00:00+00:00", "2026-12-01T05:00:00+00:00"),
    ("Pacific/Auckland", 4, "2026-03-31T11:00:00+00:00", "2026-04-30T12:00:00+00:00"),
])
def test_dst_months(zone, month, start, end):
    left, right = datetime.fromisoformat(start), datetime.fromisoformat(end)
    assert period_bounds(zone, 2026, month) == (left, right)
    assert select([Txn("x", right - timedelta(microseconds=1))], zone, 2026, month) == ["x"]


def test_naive_and_instant_order():
    with pytest.raises(ValueError):
        select([Txn("naive", datetime(2020, 1, 1))], "UTC", 2026, 1)
    a = datetime.fromisoformat("2026-01-15T09:00:00+05:30")
    b = datetime.fromisoformat("2026-01-15T03:30:00+00:00")
    assert select([Txn("b", a), Txn("a", b)], "UTC", 2026, 1) == ["a", "b"]


@given(zone=st.sampled_from(["UTC", "America/Toronto", "Asia/Kolkata", "Pacific/Auckland"]),
       offsets=st.lists(st.integers(0, 3600 * 24 * 395), min_size=1, max_size=20))
def test_thirteen_month_partition(zone, offsets):
    months = [(2026 + i // 12, i % 12 + 1) for i in range(13)]
    bounds = [period_bounds(zone, year, month) for year, month in months]
    for left, right in bounds:
        assert left.utcoffset() == right.utcoffset() == timedelta(0)
        assert left < right
    assert all(bounds[i][1] == bounds[i + 1][0] for i in range(12))
    first, last = bounds[0][0], bounds[-1][1]
    txns = [Txn(str(i), first + timedelta(seconds=offset)) for i, offset in enumerate(offsets)
            if first + timedelta(seconds=offset) < last]
    selected = [identifier for year, month in months for identifier in select(txns, zone, year, month)]
    assert sorted(selected) == sorted(t.id for t in txns)
