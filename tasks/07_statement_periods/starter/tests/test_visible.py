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
