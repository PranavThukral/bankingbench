from decimal import Decimal as D
import pytest
from fx.quote import quote_transfer, RateUnavailable


def test_direct_cad_usd():
    result = quote_transfer(10000, "CAD", "USD", {("CAD", "USD"): D("0.75")}, 100)
    assert result.converted_minor == 7425
    assert result.fee_minor == 100


def test_ticket_example_cross_quote():
    rates = {("GBP", "USD"): D("1.25"), ("USD", "CAD"): D("1.40")}
    result = quote_transfer(20000, "GBP", "CAD", rates, 50)
    assert (result.fee_minor, result.converted_minor) == (100, 34825)
    assert result.rate_used == D("1.75")
    assert result.path == ("GBP", "USD", "CAD")


def test_ticket_example_zero_decimal_currency():
    result = quote_transfer(5000, "CAD", "JPY", {("CAD", "JPY"): D("110")}, 0)
    assert (result.fee_minor, result.converted_minor) == (0, 5500)


def test_unknown_route_rejected():
    with pytest.raises(RateUnavailable):
        quote_transfer(100, "CAD", "EUR", {("CAD", "USD"): D("0.75")}, 0)
