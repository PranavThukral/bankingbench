from datetime import date
from recon.engine import reconcile, StatementLine, LedgerEntry

DAY = date(2026, 1, 5)


def test_statement_transport():
    line = StatementLine("s", DAY, 10, "ref")
    assert StatementLine.from_dict(line.as_dict()) == line


def test_ledger_transport():
    entry = LedgerEntry("l", DAY, 10, "ref")
    assert LedgerEntry.from_dict(entry.as_dict()) == entry


def test_empty():
    result = reconcile([], [])
    assert result.matches == []
    assert result.unmatched_statement == {}
    assert result.unmatched_ledger == set()


def test_unrelated_records():
    line = StatementLine("s", DAY, 10, "sref")
    entry = LedgerEntry("l", DAY, 20, "lref")
    result = reconcile([line], [entry])
    assert result.unmatched_statement == {"s": "no_match"}
    assert result.unmatched_ledger == {"l"}


def test_inputs_unchanged():
    lines = [StatementLine("s", DAY, 10, "ref")]
    entries = [LedgerEntry("l", DAY, 10, "ref")]
    expected = list(lines), list(entries)
    result = reconcile(lines, entries)
    assert (lines, entries) == expected
    assert result.as_dict()["matches"][0]["rule"] == "R1"


def test_refund_without_payment():
    line = StatementLine("s", DAY, -10, "original")
    refund = LedgerEntry("l", DAY, 10, "refund", "refund", "original")
    assert reconcile([line], [refund]).matches[0].rule == "R3"
