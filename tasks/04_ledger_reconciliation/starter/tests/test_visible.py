from datetime import date, timedelta
from recon.engine import reconcile, StatementLine, LedgerEntry

DAY = date(2026, 1, 5)


def test_exact():
    result = reconcile([StatementLine("s", DAY, 100, "ref")], [LedgerEntry("l", DAY, 100, "ref")])
    assert result.matches[0].statement_ids == frozenset(["s"])


def test_date_window():
    result = reconcile([StatementLine("s", DAY, 100, "ref")], [LedgerEntry("l", DAY + timedelta(days=2), 100, "ref")])
    assert len(result.matches) == 1
