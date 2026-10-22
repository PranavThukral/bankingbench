from decimal import Decimal as D
from fractions import Fraction
from hypothesis import given, strategies as st
import pytest
from fx.quote import quote_transfer, RateUnavailable

UNITS = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


def nearest(value):
    q, r = divmod(value.numerator, value.denominator)
    return q + int(2 * r > value.denominator or (2 * r == value.denominator and q % 2))


def check(amount, src, dst, rates, bps):
    before = dict(rates)
    result = quote_transfer(amount, src, dst, rates, bps)
    path = (src, dst) if (src, dst) in rates else (src, "USD", dst)
    rate = Fraction(1)
    for pair in zip(path, path[1:]):
        rate *= Fraction(rates[pair])
    fee = nearest(Fraction(amount * bps, 10000))
    converted = nearest(Fraction(amount - fee, 10**UNITS[src]) * rate * 10**UNITS[dst])
    assert type(result.fee_minor) is type(result.converted_minor) is int
    assert result.fee_minor == fee
    assert result.converted_minor == converted
    assert isinstance(result.rate_used, D) and Fraction(result.rate_used) == rate
    assert result.path == path
    assert rates == before
    return result


def test_jpy_and_kwd_units():
    for src, dst, amount, rate in [("JPY", "USD", 200, ".0067"), ("CAD", "JPY", 12345, "110.1234"),
                                    ("CAD", "KWD", 12345, ".22567"), ("KWD", "JPY", 12345, "485.12"),
                                    ("BHD", "GBP", 12345, "2.1")]:
        check(amount, src, dst, {(src, dst): D(rate)}, 27)


def test_cross_has_no_intermediate_rounding():
    rates = {("CAD", "USD"): D(".5"), ("USD", "EUR"): D("1.5")}
    assert check(1, "CAD", "EUR", rates, 0).converted_minor == 1
    rates["CAD", "EUR"] = D("2")
    assert check(1, "CAD", "EUR", rates, 0).path == ("CAD", "EUR")


def test_source_fee_before_conversion():
    result = check(3, "CAD", "USD", {("CAD", "USD"): D(".5")}, 5000)
    assert (result.fee_minor, result.converted_minor) == (2, 0)


@pytest.mark.parametrize("amount,rate", [(1, ".5"), (2, ".25"), (2, ".75")])
def test_discovered_half_even_ties(amount, rate):
    check(amount, "CAD", "USD", {("CAD", "USD"): D(rate)}, 0)


def test_unavailable_and_zero():
    for src, dst, rates in [("CAD", "EUR", {}), ("CAD", "EUR", {("CAD", "USD"): D(".5")}),
                             ("XYZ", "USD", {})]:
        with pytest.raises(RateUnavailable):
            quote_transfer(1, src, dst, rates, 0)
    result = check(0, "CAD", "USD", {("CAD", "USD"): D(".5")}, 100)
    assert result.fee_minor == result.converted_minor == 0


@pytest.mark.parametrize("amount", [0, 100])
def test_inverse_only_is_unavailable(amount):
    with pytest.raises(RateUnavailable):
        quote_transfer(amount, "CAD", "EUR", {("EUR", "CAD"): D("2")}, 0)


@pytest.mark.parametrize("left,right", [
    ("1.23456789", "1.34567891"),
    ("1.12345678901234567890123456789", "1.98765432109876543210987654321"),
])
def test_full_precision_cross_rate(left, right):
    check(10**9, "GBP", "CAD", {("GBP", "USD"): D(left), ("USD", "CAD"): D(right)}, 17)


@pytest.mark.parametrize("amount,bps", [
    (True, 0), (-1, 0), (1.5, 0), ("1", 0), (1, True), (1, -1),
    (1, 10001), (1, 1.5), (1, "5"),
])
def test_invalid_amount_and_fee(amount, bps):
    with pytest.raises(ValueError):
        quote_transfer(amount, "CAD", "USD", {("CAD", "USD"): D(".5")}, bps)


@given(amount=st.integers(0, 10**12), extra=st.integers(0, 10**8), units=st.integers(1, 100000),
       bps=st.integers(0, 10000), pair=st.sampled_from([("CAD", "USD"), ("JPY", "KWD"), ("BHD", "JPY")]))
def test_exact_scaling_and_monotonicity(amount, extra, units, bps, pair):
    src, dst = pair
    rates = {pair: D(units).scaleb(-4)}
    first = check(amount, src, dst, rates, bps)
    second = check(amount + extra, src, dst, rates, bps)
    assert second.converted_minor >= first.converted_minor


@given(st.integers(0, 10**12))
def test_zero_fee_roundtrip(amount):
    outward = check(amount, "CAD", "USD", {("CAD", "USD"): D(".5")}, 0)
    back = check(outward.converted_minor, "USD", "CAD", {("USD", "CAD"): D("2")}, 0)
    assert abs(back.converted_minor - amount) <= 1
