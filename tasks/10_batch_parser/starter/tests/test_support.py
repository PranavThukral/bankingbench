import csv
from batch.csvout import write_payments_csv
from batch.errors import describe, render_errors
from batch.models import BatchError, BatchResult, Payment
from batch.preview import main
from batch.render import render
from batch.summary import format_minor, payee_totals, summarize


def test_error_descriptions():
    assert describe("hash_total_mismatch").startswith("trailer hash total")
    assert describe("nope") == "unrecognised error code"
    assert render_errors([BatchError(7, "invalid_detail")]) == "line 7: invalid_detail - detail fields are malformed\n"


def test_summary_and_money_formatting():
    payments = [Payment("000000000123", 150, "a"), Payment("000000000123", 50, "b"), Payment("000000000456", 5, "c")]
    assert payee_totals(payments) == {"000000000123": 200, "000000000456": 5}
    assert summarize(BatchResult(True, payments, [])) == {
        "accepted": True, "payments": 3, "payees": 2, "amount": "2.05", "errors": 0}
    assert format_minor(1234, 3) == "1.234" and format_minor(77, 0) == "77" and format_minor(-5) == "-0.05"


def test_csv_export_and_preview_flags(tmp_path):
    payments = [Payment("000000000123", 100, "reference")]
    assert write_payments_csv(tmp_path / "p.csv", payments) == 1
    with (tmp_path / "p.csv").open(encoding="utf-8", newline="") as stream:
        assert list(csv.reader(stream)) == [["payee_account", "amount_minor", "reference"],
                                            ["000000000123", "100", "reference"]]
    (tmp_path / "batch.sbf").write_bytes(render(payments))
    assert main([str(tmp_path / "batch.sbf"), "--csv", str(tmp_path / "out.csv"),
                 "--out", str(tmp_path / "result.json")]) == 0
    assert (tmp_path / "out.csv").is_file()
