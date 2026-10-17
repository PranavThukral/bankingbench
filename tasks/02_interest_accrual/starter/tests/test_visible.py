from datetime import date
from decimal import Decimal as D
from interest.accrual import accrue


def test_ordinary_month():
    result = accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")
    assert result[0].interest == D("3.10")


def test_partial_month():
    result = accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 1, 11), "simple_monthly")
    assert len(result) == 1
    assert result[0].interest == D("1.00")
