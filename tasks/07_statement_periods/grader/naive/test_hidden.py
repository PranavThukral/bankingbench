from datetime import datetime, timezone
from statements.period import select, Txn


def test_midmonth_utc():
    assert select([Txn("a", datetime(2026, 1, 15, tzinfo=timezone.utc))], "UTC", 2026, 1) == ["a"]
