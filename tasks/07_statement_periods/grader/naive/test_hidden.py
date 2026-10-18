from datetime import datetime, timezone
import pytest
from statements.period import period_bounds, select, Txn


def test_midmonth_utc():
    assert select([Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))], "UTC", 2026, 1) == ["a"]


def test_ticket_worked_example_toronto_january():
    start, end = period_bounds("America/Toronto", 2026, 1)
    assert start == datetime(2026, 1, 1, 5, tzinfo=timezone.utc)
    assert end == datetime(2026, 2, 1, 5, tzinfo=timezone.utc)
    txns = [Txn("a", datetime(2026, 2, 1, 4, 30, tzinfo=timezone.utc)),
            Txn("b", datetime(2026, 2, 1, 5, 30, tzinfo=timezone.utc))]
    assert select(txns, "America/Toronto", 2026, 1) == ["a"]


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        select([Txn("a", datetime(2026, 1, 15))], "UTC", 2026, 1)
