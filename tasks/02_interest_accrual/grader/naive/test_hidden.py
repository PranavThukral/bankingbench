from datetime import date
from decimal import Decimal as D
from interest.accrual import accrue


def test_examples():
    for principal, expected in [("1000.00", "3.10"), ("2000.00", "6.20"), ("5000.00", "15.50")]:
        result = accrue(D(principal), D("0.0365"), date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")
        assert len(result) == 1
        assert abs(D(str(result[0].interest)) - D(expected)) <= D("0.01")
