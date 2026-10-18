from datetime import date
from decimal import Decimal as D
import pytest
from interest.accrual import accrue


def close(actual, expected):
    return abs(D(str(actual)) - D(expected)) <= D("0.01")


def test_examples():
    for principal, expected in [("1000.00", "3.10"), ("2000.00", "6.20"), ("5000.00", "15.50")]:
        result = accrue(D(principal), D("0.0365"), date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")
        assert len(result) == 1
        assert abs(D(str(result[0].interest)) - D(expected)) <= D("0.01")


@pytest.mark.parametrize("method", ["simple_monthly", "daily_compound"])
def test_ticket_worked_example(method):
    result = accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 3, 1), method)
    assert [p.posting_date for p in result] == [date(2026, 1, 31), date(2026, 2, 28)]
    assert close(result[0].interest, "3.10") and close(result[0].balance, "1003.10")
    assert close(result[1].interest, "2.81") and close(result[1].balance, "1005.91")


def test_empty_period_and_reversed_dates():
    assert accrue(D("1000.00"), D("0.0365"), date(2026, 1, 1), date(2026, 1, 1), "simple_monthly") == []
    with pytest.raises(ValueError):
        accrue(D("1000.00"), D("0.0365"), date(2026, 2, 1), date(2026, 1, 1), "simple_monthly")
