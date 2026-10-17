from decimal import Decimal as D
from fx.quote import quote_transfer


def test_direct_cad_usd():
    result = quote_transfer(10000, "CAD", "USD", {("CAD", "USD"): D("0.75")}, 100)
    assert result.converted_minor == 7425
    assert result.fee_minor == 100
