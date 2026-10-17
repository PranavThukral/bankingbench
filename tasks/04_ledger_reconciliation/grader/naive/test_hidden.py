from datetime import date
from recon.engine import reconcile, StatementLine, LedgerEntry


def test_clean_one_to_one():
    day = date(2026, 1, 5)
    statement = [StatementLine(f"s{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    ledger = [LedgerEntry(f"l{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    assert len(reconcile(statement, ledger).matches) == 3
