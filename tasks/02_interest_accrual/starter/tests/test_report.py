from datetime import date
from decimal import Decimal as D
import pytest
from interest.accrual import Posting
from interest.calendar import AccrualRequest
from interest.csvio import read_requests_csv, write_postings_csv
from interest.report import effective_rate_percent, format_money, render_statement, total_interest

REQUEST = AccrualRequest(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 3, 1), "simple_monthly")
POSTINGS = [Posting(date(2026, 1, 31), D("3.10"), D("1003.10")), Posting(date(2026, 2, 28), D("2.81"), D("1005.91"))]


def test_money_and_totals():
    assert format_money(D("1234567.8")) == "1,234,567.80"
    assert total_interest(POSTINGS) == D("5.91")
    assert effective_rate_percent(D("1000.00"), POSTINGS) == D("0.5910")
    assert effective_rate_percent(D("0.00"), POSTINGS) == D("0.0000")


def test_statement_lists_each_posting():
    text = render_statement(REQUEST, POSTINGS)
    assert text.splitlines()[0] == "Account interest, 2026-01-01 to 2026-03-01 (simple_monthly)"
    assert "2026-02-28  interest         2.81  balance         1,005.91" in text
    assert text.splitlines()[-1].startswith("Total interest: 5.91 (0.5910% of opening balance)")


def test_csv_round_trip(tmp_path):
    (tmp_path / "requests.csv").write_text(
        "principal,annual_rate,start,end,method\n1000.00,0.0365,2026-01-01,2026-03-01,simple_monthly\n",
        encoding="utf-8")
    requests = read_requests_csv(tmp_path / "requests.csv")
    assert requests == [REQUEST]
    rows = write_postings_csv(tmp_path / "postings.csv", requests, lambda *args: POSTINGS)
    assert rows == 2
    assert (tmp_path / "postings.csv").read_text(encoding="utf-8").splitlines()[1] == "2,2026-01-31,3.10,1003.10"


def test_csv_rejects_bad_rows(tmp_path):
    (tmp_path / "requests.csv").write_text(
        "principal,annual_rate,start,end,method\n1000.00,-1,2026-01-01,2026-03-01,simple_monthly\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        read_requests_csv(tmp_path / "requests.csv")
