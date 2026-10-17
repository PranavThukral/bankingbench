from author_common import task_meta, write

b = task_meta("03_fx_quotes", "Quote transfers with currency-specific minor units", "fx", [
    "fx.quote:quote_transfer, Quote, RateUnavailable"], [
    ("wrong_two_decimals", "Assumes every currency has two decimal places.", ["test_jpy_and_kwd_units"]),
    ("wrong_round_cross_leg", "Rounds the intermediate USD amount in a cross quote.", ["test_cross_has_no_intermediate_rounding"]),
    ("wrong_fee_after_conversion", "Rounds destination fees after conversion instead of source fees before it.", ["test_source_fee_before_conversion"]),
], "Exact Fraction scaling and integer half-even rounding instead of Decimal amount arithmetic.", terms=["Fraction", "localcontext"])
write(b / "PROBLEM.md", '''
# Ticket: quote a synthetic currency transfer

`fx.quote.quote_transfer(amount_minor:int,src:str,dst:str,rates:dict[tuple[str,str],Decimal],fee_bps:int)`
returns frozen `Quote(fee_minor:int,converted_minor:int,rate_used:Decimal,path:tuple[str,...])`.
Expose `RateUnavailable(ValueError)` for unavailable currencies/pairs.

Minor units: CAD/USD/EUR/GBP=2, JPY=0, KWD/BHD=3. Rates are positive finite Decimals in
destination major units per source major unit. All money values returned are int minor units.
Amount is nonnegative int, never bool; fee_bps integer in [0,10000]; invalid values -> ValueError.
Inputs use distinct src/dst; an unsupported currency -> RateUnavailable.

1. Fee in source minor units = amount_minor × fee_bps / 10000, rounded HALF_EVEN to integer.
   Deduct this fee BEFORE conversion. Returned fee_minor is this source fee.
2. Use direct `(src,dst)` rate if present, path `(src,dst)`. Otherwise require both `(src,"USD")`
   and `("USD",dst)`, multiply at full precision, path `(src,"USD",dst)`. Do not infer inverses or
   other routes. Missing required rates -> RateUnavailable. Direct rate takes precedence.
3. Convert net source minor units to source major units, apply the full rate, then scale to
   destination minor units. Round ONLY the final destination amount HALF_EVEN to integer.
   Do not round the USD leg of a cross quote. rate_used is the full direct/product Decimal.

Do not mutate rates. Zero amount returns zero amounts while still resolving the declared route.
No actual currency market or customer is represented. Run `python -m pytest tests -q` from starter.
''')
write(b / "starter/fx/models.py", '''
"""Synthetic quote records and rate-book transport."""
from dataclasses import dataclass
from decimal import Decimal

UNITS = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


class RateUnavailable(ValueError):
    """No declared route exists for this currency pair."""


@dataclass(frozen=True)
class Quote:
    fee_minor: int
    converted_minor: int
    rate_used: Decimal
    path: tuple[str, ...]

    def as_dict(self):
        return {"fee_minor": self.fee_minor, "converted_minor": self.converted_minor,
                "rate_used": str(self.rate_used), "path": list(self.path)}


@dataclass(frozen=True)
class QuoteRequest:
    amount_minor: int
    src: str
    dst: str
    fee_bps: int

    @classmethod
    def from_dict(cls, row):
        return cls(row["amount_minor"], row["src"], row["dst"], row["fee_bps"])

    def as_dict(self):
        return dict(amount_minor=self.amount_minor, src=self.src, dst=self.dst, fee_bps=self.fee_bps)


def read_rates(rows):
    rates = {}
    for row in rows:
        rate = Decimal(row["rate"])
        if not rate.is_finite() or rate <= 0:
            raise ValueError("positive finite rate required")
        pair = row["src"], row["dst"]
        if pair in rates:
            raise ValueError("duplicate rate")
        rates[pair] = rate
    return rates


def render_rates(rates):
    return [{"src": a, "dst": b, "rate": str(value)} for (a, b), value in sorted(rates.items())]


def validate(amount_minor, src, dst, fee_bps):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    if type(fee_bps) is not int or not 0 <= fee_bps <= 10000:
        raise ValueError("invalid fee basis points")
    if src not in UNITS or dst not in UNITS:
        raise RateUnavailable((src, dst))
''')
reference = '''
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fx.models import Quote, RateUnavailable, UNITS, validate

__all__ = ["quote_transfer", "Quote", "RateUnavailable"]


def quote_transfer(amount_minor, src, dst, rates, fee_bps):
    validate(amount_minor, src, dst, fee_bps)
    with localcontext() as ctx:
        ctx.prec = max(50, len(str(amount_minor)) + sum(len(r.as_tuple().digits) for r in rates.values()) + 20)
        if (src, dst) in rates:
            rate, path = rates[src, dst], (src, dst)
        else:
            try:
                rate = rates[src, "USD"] * rates["USD", dst]
            except KeyError as exc:
                raise RateUnavailable((src, dst)) from exc
            path = (src, "USD", dst)
        fee = int((Decimal(amount_minor) * fee_bps / 10000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        net = Decimal(amount_minor - fee).scaleb(-UNITS[src])
        converted = int((net * rate).scaleb(UNITS[dst]).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        return Quote(fee, converted, rate, path)
'''
write(b / "solutions/reference/fx/quote.py", reference)
write(b / "starter/fx/quote.py", reference.replace('Decimal(amount_minor - fee)', 'Decimal(amount_minor)').replace(
    'from decimal import Decimal, ROUND_HALF_EVEN, localcontext', 'from decimal import Decimal, ROUND_HALF_EVEN').replace(
    '    with localcontext() as ctx:\n        ctx.prec = max(50, len(str(amount_minor)) + sum(len(r.as_tuple().digits) for r in rates.values()) + 20)\n', ''))
# Deindent the body after removing the precision context in the starter.
starter = (b / "starter/fx/quote.py").read_text(encoding="utf-8")
head, tail = starter.split('    validate(amount_minor, src, dst, fee_bps)\n', 1)
write(b / "starter/fx/quote.py", head + '    validate(amount_minor, src, dst, fee_bps)\n' + '\n'.join(line[4:] if line.startswith('    ') else line for line in tail.splitlines()) + '\n')
write(b / "solutions/wrong_two_decimals/fx/quote.py", reference.replace('-UNITS[src]', '-2').replace('UNITS[dst]', '2').replace('RateUnavailable, UNITS, validate', 'RateUnavailable, validate'))
write(b / "solutions/wrong_round_cross_leg/fx/quote.py", reference.replace(
    '        converted = int(', '        if len(path) == 3:\n            net = (net * rates[src, "USD"]).quantize(Decimal(".01"), rounding=ROUND_HALF_EVEN)\n            rate_for_amount = rates["USD", dst]\n        else:\n            rate_for_amount = rate\n        converted = int(').replace('(net * rate).scaleb', '(net * rate_for_amount).scaleb'))
write(b / "solutions/wrong_fee_after_conversion/fx/quote.py", reference.replace(
    '        net = Decimal(amount_minor - fee).scaleb(-UNITS[src])', '        net = Decimal(amount_minor).scaleb(-UNITS[src])').replace(
    '        return Quote(fee, converted, rate, path)',
    '        converted -= int((Decimal(converted) * fee_bps / 10000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))\n        return Quote(fee, converted, rate, path)'))
write(b / "solutions/alt_valid/fx/quote.py", '''
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
''')
write(b / "starter/fx/preview.py", '''
"""JSON quote preview adapter."""
import argparse
import json
from pathlib import Path
from fx.models import QuoteRequest, read_rates, render_rates
from fx.quote import quote_transfer


def read_input(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    requests = [QuoteRequest.from_dict(row) for row in data["requests"]]
    rates = read_rates(data["rates"])
    return requests, rates


def preview(requests, rates):
    quotes = []
    for request in requests:
        quote = quote_transfer(request.amount_minor, request.src, request.dst, rates, request.fee_bps)
        quotes.append({"request": request.as_dict(), "quote": quote.as_dict()})
    return {"rates": render_rates(rates), "quotes": quotes}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic currency quotes")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    content = json.dumps(preview(*read_input(args.input)), indent=2) + "\\n"
    if args.out:
        args.out.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
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
''')
write(b / "grader/naive/test_hidden.py", '''
from decimal import Decimal as D
from fx.quote import quote_transfer


def test_direct_cad_usd():
    result = quote_transfer(10000, "CAD", "USD", {("CAD", "USD"): D("0.75")}, 100)
    assert result.converted_minor == 7425
    assert result.fee_minor == 100
''')
write(b / "NOTES.md", '''
# Private draft — FX reviewer notes

The exact rational alternative verifies that the Decimal implementation does not define the
answer by itself. Wrong candidates use a universal scale, round a cross leg, or charge fees in
the destination. Ordinary two-decimal direct quotes can mask all three errors.

## Blind review
Author self-review: fee denomination, direct-rate precedence, unsupported currencies, inverse
rates, zero amount and acceptable fee range clarified in PROBLEM.md.
Predictions: JPY100 -> USD at0.01 ->100 cents; CAD3 at0.5 with5000bps ->fee2/converted0;
cross CAD1 via0.5 USD and1.5 EUR ->1 EUR cent. No unresolved graded ambiguity.
Independent review remains owed.
''')
