"""Independent Fraction/Decimal cross-checks for the committed numeric fixtures."""
import calendar
from datetime import date, timedelta
from decimal import Decimal, localcontext, ROUND_HALF_EVEN, ROUND_HALF_UP
from fractions import Fraction
import json
from pathlib import Path


def round_even(value):
    quotient, remainder = divmod(value.numerator, value.denominator)
    return quotient + int(2 * remainder > value.denominator or
                          (2 * remainder == value.denominator and quotient % 2))


def interest_oracle(principal, rate, start, end, method):
    balance = int(principal * 100)
    factor = Fraction(rate) / 365
    result = []
    cursor = start
    while cursor < end:
        last = min(date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]),
                   end - timedelta(days=1))
        days = (last - cursor).days + 1
        gain = Fraction(balance, 100) * (factor * days if method == "simple_monthly" else (1 + factor)**days - 1)
        posted = round_even(gain * 100)
        balance += posted
        result.append((last, Decimal(posted).scaleb(-2), Decimal(balance).scaleb(-2)))
        cursor = last + timedelta(days=1)
    return result


def decimal_interest(principal, rate, start, end, method):
    with localcontext() as ctx:
        ctx.prec = 34
        balance, accrued, count = principal, Decimal(0), 0
        output, day = [], start
        while day < end:
            count += 1
            accrued = ((balance + accrued) * (1 + rate / 365) - balance if method == "daily_compound"
                       else balance * rate * count / 365)
            if day.day == calendar.monthrange(day.year, day.month)[1] or day == end - timedelta(days=1):
                rounded = accrued.quantize(Decimal(".01"), rounding=ROUND_HALF_EVEN)
                balance += rounded
                output.append((day, rounded, balance.quantize(Decimal(".01"))))
                accrued, count = Decimal(0), 0
            day += timedelta(days=1)
        return output


def main():
    cases = json.loads(Path(__file__).with_name("rounding_cases.json").read_text(encoding="utf-8"))
    count = 0
    for c in cases["interest"]:
        p, rate = Decimal(c["principal"]), Decimal(c["rate"])
        start, end = date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=c["days"])
        expected = interest_oracle(p, rate, start, end, "simple_monthly")
        assert expected == decimal_interest(p, rate, start, end, "simple_monthly")
        assert expected[0][1] == Decimal(c["expected"])
        count += 1
    for method in ("simple_monthly", "daily_compound"):
        for principal in ("1.00", "1000000000.00", "987654.32"):
            for rate in ("0.036500001825", "0.05", "0.0001"):
                for start, end in ((date(2024, 2, 14), date(2024, 4, 3)),
                                   (date(2026, 1, 1), date(2026, 1, 2))):
                    args = Decimal(principal), Decimal(rate), start, end, method
                    assert interest_oracle(*args) == decimal_interest(*args), args
                    count += 1
    for c in cases["fees"]:
        exact = Fraction(c["amount"] * c["bps"], 10000)
        assert c["exact"] == (exact.numerator * 2 + exact.denominator) // (2 * exact.denominator)
        decimal = (Decimal(c["amount"]) * c["bps"] / 10000).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        assert decimal == c["exact"]
        count += 1
    for c in cases["fx"]:
        exact = Fraction(c["amount_minor"]) * Fraction(c["rate"])
        rounded = (Decimal(c["amount_minor"]) * Decimal(c["rate"])).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
        assert round_even(exact) == rounded
        count += 1
    print(f"PASS: {count} numeric cases agree between Fraction and Decimal (prec=34); 0 dropped")


if __name__ == "__main__":
    main()
