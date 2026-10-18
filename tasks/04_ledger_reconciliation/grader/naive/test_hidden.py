from datetime import date
from recon.engine import reconcile, StatementLine, LedgerEntry


def test_clean_one_to_one():
    day = date(2026, 1, 5)
    statement = [StatementLine(f"s{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    ledger = [LedgerEntry(f"l{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    assert len(reconcile(statement, ledger).matches) == 3


def test_ticket_worked_example():
    statement = [StatementLine("s1", date(2026, 1, 5), 10000, "INV-1"),
                 StatementLine("s2", date(2026, 1, 6), 4000, "INV-2"),
                 StatementLine("s3", date(2026, 1, 7), 6000, "INV-2")]
    ledger = [LedgerEntry("l1", date(2026, 1, 3), 10000, "INV-1"),
              LedgerEntry("l2", date(2026, 1, 6), 10000, "INV-2")]
    result = reconcile(statement, ledger)
    assert len(result.matches) == 2
    assert not result.unmatched_statement
    assert not result.unmatched_ledger


def test_unrelated_line_is_unmatched():
    day = date(2026, 1, 5)
    result = reconcile([StatementLine("s", day, 101, "ref")], [LedgerEntry("l", day, 100, "ref")])
    assert len(result.matches) == 0
    assert set(result.unmatched_statement) == {"s"}
    assert result.unmatched_ledger == {"l"}
