from decimal import Decimal, localcontext
from fractions import Fraction
from fx.models import Quote, RateUnavailable, UNITS, validate

__all__ = ["quote_transfer", "Quote", "RateUnavailable"]


def nearest_even(value):
    integer, residue = divmod(value.numerator, value.denominator)
    doubled = residue * 2
    return integer + int(doubled > value.denominator or (doubled == value.denominator and integer % 2))


def quote_transfer(amount_minor, src, dst, rates, fee_bps):
    validate(amount_minor, src, dst, fee_bps)
    route = (src, dst) if (src, dst) in rates else (src, "USD", dst)
    factors = []
    for pair in zip(route, route[1:]):
        if pair not in rates:
            raise RateUnavailable(pair)
        factors.append(rates[pair])
    with localcontext() as arithmetic:
        arithmetic.prec = max(34, sum(len(f.as_tuple().digits) for f in factors) + 10)
        decimal_rate = Decimal(1)
        for factor in factors:
            decimal_rate *= factor
    exact_rate = Fraction(1)
    for factor in factors:
        exact_rate *= Fraction(factor)
    commission = nearest_even(Fraction(amount_minor * fee_bps, 10000))
    destination = Fraction(amount_minor - commission, 10**UNITS[src]) * exact_rate * 10**UNITS[dst]
    return Quote(commission, nearest_even(destination), decimal_rate, route)
