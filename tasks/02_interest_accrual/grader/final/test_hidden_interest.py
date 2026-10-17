import calendar
from datetime import date, timedelta
from decimal import Decimal as D
from fractions import Fraction

from hypothesis import given, strategies as st
import pytest

from interest.accrual import accrue
from graderlib.money import assert_money


def oracle(principal, rate, start, end, method):
    cents, cursor, rows = int(principal * 100), start, []
    while cursor < end:
        last = min(date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]),
                   end - timedelta(days=1))
        days = (last - cursor).days + 1
        factor = Fraction(rate) / 365
        gain = Fraction(cents) * (factor * days if method == "simple_monthly" else (1 + factor)**days - 1)
        whole, remainder = divmod(gain.numerator, gain.denominator)
        whole += int(2 * remainder > gain.denominator or (2 * remainder == gain.denominator and whole % 2))
        cents += whole
        rows.append((last, D(whole).scaleb(-2), D(cents).scaleb(-2)))
        cursor = last + timedelta(days=1)
    return rows


def check(principal, rate, start, end, method):
    rows = accrue(principal, rate, start, end, method)
    for row in rows:
        assert_money(row.interest)
        assert_money(row.balance)
    assert [(r.posting_date, r.interest, r.balance) for r in rows] == oracle(principal, rate, start, end, method)
    assert sum((r.interest for r in rows), principal) == (rows[-1].balance if rows else principal)
    return rows


@pytest.mark.parametrize("principal,rate,days", [("50", "0.0365", 1), ("73", "0.025", 1), ("25", "0.0365", 2)])
def test_half_cent_ties_bankers(principal, rate, days):
    # Search output from tools/find_ties.py, independently cross-checked with Fraction.
    check(D(principal), D(rate), date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=days), "simple_monthly")


@pytest.mark.parametrize("method", ["simple_monthly", "daily_compound"])
def test_large_principal_exact(method):
    for rate in ("0.036500001825", "0.05"):
        check(D("1000000000.00"), D(rate), date(2024, 2, 14), date(2024, 4, 3), method)


def test_small_balance_daily_accrues():
    rows = check(D("1.00"), D("0.1"), date(2026, 1, 1), date(2026, 2, 1), "daily_compound")
    assert rows[0].interest == D("0.01")


def test_leap_and_partial():
    for method in ("simple_monthly", "daily_compound"):
        check(D("12345.67"), D("0.037"), date(2024, 2, 28), date(2024, 3, 5), method)
        assert accrue(D("12.00"), D("0.1"), date(2026, 1, 1), date(2026, 1, 1), method) == []


@given(cents=st.integers(0, 100000000), rate=st.integers(0, 1500),
       offset=st.integers(0, 100), days=st.integers(0, 90),
       method=st.sampled_from(["simple_monthly", "daily_compound"]))
def test_accrual_properties(cents, rate, offset, days, method):
    principal, annual_rate = D(cents).scaleb(-2), D(rate).scaleb(-4)
    start = date(2024, 1, 1) + timedelta(days=offset)
    end = start + timedelta(days=days)
    rows = check(principal, annual_rate, start, end, method)
    assert all(r.interest >= 0 for r in rows)
    higher = accrue(principal, annual_rate + D("0.0001"), start, end, method)
    assert all(a.interest <= b.interest for a, b in zip(rows, higher))
