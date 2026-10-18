from decimal import Decimal as D
from fx.models import Quote, QuoteRequest
from fx.report import describe_ratebook, format_minor, render_quote, render_sheet


def test_format_minor_per_currency():
    assert format_minor(12345, "CAD") == "123.45 CAD"
    assert format_minor(500, "JPY") == "500 JPY"
    assert format_minor(-1234, "KWD") == "-1.234 KWD"


def test_quote_sheet_and_ratebook():
    request = QuoteRequest(10000, "CAD", "USD", 100)
    quote = Quote(100, 7425, D("0.75"), ("CAD", "USD"))
    line = render_quote(request, quote)
    assert "100.00 CAD" in line and "74.25 USD" in line and "via CAD > USD" in line
    assert render_sheet([request], [quote]).splitlines()[0] == "1 quote(s)"
    assert describe_ratebook({("USD", "CAD"): D("1.4"), ("CAD", "USD"): D("0.75")}) == "CAD->USD 0.75\nUSD->CAD 1.4\n"
