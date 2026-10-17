from decimal import Decimal as D
from fx.csv_io import read_rate_csv, write_rate_csv, read_request_csv, write_request_csv
from fx.models import QuoteRequest


def test_rate_csv_roundtrip(tmp_path):
    path = tmp_path / "rates.csv"
    rates = {("CAD", "USD"): D(".75")}
    write_rate_csv(path, rates)
    assert read_rate_csv(path) == rates


def test_request_csv_roundtrip(tmp_path):
    path = tmp_path / "requests.csv"
    requests = [QuoteRequest(100, "CAD", "USD", 0)]
    write_request_csv(path, requests)
    assert read_request_csv(path) == requests
