"""Deterministically discover adversarial rounding cases using exact arithmetic."""
from decimal import Decimal
from fractions import Fraction
import json
import math
from pathlib import Path


def interest_ties():
    found = []
    for days in range(1, 29):
        for cents in range(100, 10001, 100):
            for rate_units in (1, 5, 10, 25, 50, 100, 125, 250, 365, 500):
                scaled = Fraction(cents * rate_units * days, 10000 * 365)
                if scaled.denominator == 2 and scaled.numerator // 2 % 2 == 0:
                    found.append(dict(principal=str(Decimal(cents) / 100),
                                      rate=str(Decimal(rate_units) / 10000), days=days,
                                      expected=str(Decimal(scaled.numerator // 2) / 100)))
                    if len(found) == 3:
                        return found
    raise RuntimeError("search found too few interest ties")


def fee_ties():
    found = []
    for bps in range(1, 2001):
        for amount in range(1, 100001):
            numerator = amount * bps
            if numerator % 10000 != 5000:
                continue
            exact = (numerator + 5000) // 10000
            observed = math.floor(amount * (bps / 10000) + .5)
            if exact != observed:
                found.append(dict(amount=amount, bps=bps, exact=exact, float_result=observed))
                if len(found) == 3:
                    return found
    raise RuntimeError("search found too few fee ties")


def fx_ties():
    found = []
    for amount in range(1, 1000):
        for rate_cents in range(1, 100):
            converted = Fraction(amount * rate_cents, 100)
            if converted.denominator == 2:
                found.append(dict(amount_minor=amount, rate=str(Decimal(rate_cents) / 100)))
                if len(found) == 3:
                    return found


def search():
    return dict(interest=interest_ties(), fees=fee_ties(), fx=fx_ties())


if __name__ == "__main__":
    result = search()
    target = Path(__file__).with_name("rounding_cases.json")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
