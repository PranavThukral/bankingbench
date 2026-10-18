from decimal import Decimal as D
from fx.batch import quote_all, write_quotes_csv
from fx.models import QuoteRequest


def test_batch_reports_bad_requests_without_stopping(tmp_path):
    rates = {("CAD", "USD"): D("0.75")}
    requests = [QuoteRequest(10000, "CAD", "USD", 0), QuoteRequest(100, "CAD", "BHD", 0),
                QuoteRequest(-5, "CAD", "USD", 0)]
    outcomes = quote_all(requests, rates)
    assert [status for status, _ in outcomes] == ["ok", "no_route", "invalid"]
    assert outcomes[0][1].converted_minor == 7500
    assert write_quotes_csv(tmp_path / "quotes.csv", requests, outcomes) == 3
    lines = (tmp_path / "quotes.csv").read_text(encoding="utf-8").splitlines()
    assert lines[1] == "10000,CAD,USD,0,ok,0,7500,CAD>USD"
    assert lines[2] == "100,CAD,BHD,0,no_route,,,"
