from datetime import date
from recon.models import StatementLine, LedgerEntry, Match, ReconResult
from recon.report import format_amount, render_report
from recon.csvio import read_statement_csv, read_ledger_csv, write_unmatched_csv

DAY = date(2026, 1, 5)


def test_format_amount():
    assert format_amount(12345) == "123.45"
    assert format_amount(-5) == "-0.05"
    assert format_amount(0) == "0.00"


def test_render_report_lists_every_section():
    statement = [StatementLine("s1", DAY, 1000, "ref"), StatementLine("s2", DAY, 7, "other")]
    ledger = [LedgerEntry("l1", DAY, 1000, "ref"), LedgerEntry("l2", DAY, 9, "stray")]
    result = ReconResult([Match(frozenset(["s1"]), frozenset(["l1"]), "R1")], {"s2": "no_match"}, {"l2"})
    text = render_report(result, statement, ledger)
    assert "R1  s1 -> l1  (10.00)" in text
    assert "s2  2026-01-05  other  0.07  [no_match]" in text
    assert "l2  2026-01-05  stray  0.09  (payment)" in text


def test_csv_round_trip(tmp_path):
    (tmp_path / "statement.csv").write_text(
        "id,value_date,amount_minor,reference\ns1,2026-01-05,100,ref\n", encoding="utf-8")
    (tmp_path / "ledger.csv").write_text(
        "id,booking_date,amount_minor,reference,kind,original_reference\n"
        "l1,2026-01-05,100,ref,,\nl2,2026-01-06,100,rf,refund,ref\n", encoding="utf-8")
    statement, ledger = read_statement_csv(tmp_path / "statement.csv"), read_ledger_csv(tmp_path / "ledger.csv")
    assert statement == [StatementLine("s1", DAY, 100, "ref")]
    assert [e.kind for e in ledger] == ["payment", "refund"]
    assert ledger[1].original_reference == "ref"
    write_unmatched_csv(tmp_path / "out.csv", ReconResult([], {"s1": "no_match"}, set()), statement)
    assert "s1,2026-01-05,100,ref,no_match" in (tmp_path / "out.csv").read_text(encoding="utf-8")


def test_preview_cli_reads_csv_and_writes_a_report(tmp_path):
    from recon.preview import main
    (tmp_path / "statement.csv").write_text(
        "id,value_date,amount_minor,reference\ns1,2026-01-05,100,ref\n", encoding="utf-8")
    (tmp_path / "ledger.csv").write_text(
        "id,booking_date,amount_minor,reference\nl1,2026-01-05,100,ref\n", encoding="utf-8")
    out = tmp_path / "report.txt"
    main([str(tmp_path / "statement.csv"), str(tmp_path / "ledger.csv"), "--report", "--out", str(out)])
    assert out.read_text(encoding="utf-8").startswith("Matched groups: ")
