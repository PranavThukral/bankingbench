from decimal import Decimal as D
import pytest
from fx.quote import quote_transfer, RateUnavailable
from fx.models import read_rates, render_rates, QuoteRequest


def test_direct():
    result = quote_transfer(10000, "CAD", "USD", {("CAD", "USD"): D(".75")}, 0)
    assert result.converted_minor == 7500
    assert result.path == ("CAD", "USD")


def test_fee():
    result = quote_transfer(10000, "CAD", "USD", {("CAD", "USD"): D(".75")}, 100)
    assert result.fee_minor == 100
    assert result.converted_minor == 7425


def test_unknown_route():
    with pytest.raises(RateUnavailable):
        quote_transfer(100, "CAD", "EUR", {}, 0)


def test_rate_transport():
    rows = [{"src": "CAD", "dst": "USD", "rate": "0.75"}]
    assert render_rates(read_rates(rows)) == rows


def test_request_transport():
    row = {"amount_minor": 100, "src": "CAD", "dst": "USD", "fee_bps": 0}
    assert QuoteRequest.from_dict(row).as_dict() == row


def test_invalid_amount():
    with pytest.raises(ValueError):
        quote_transfer(-1, "CAD", "USD", {}, 0)
