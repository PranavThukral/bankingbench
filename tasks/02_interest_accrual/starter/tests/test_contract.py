from datetime import date, datetime, timezone
from decimal import Decimal as D
import pytest
from interest.accrual import accrue
from interest.calendar import AccrualRequest, segments


def test_request_round_trip():
    row = dict(principal="1000.00", annual_rate="0.03", start="2026-01-01",
               end="2026-02-01", method="simple_monthly")
    assert AccrualRequest.from_dict(row).as_dict() == row


def test_segments_cover_days():
    result = list(segments(date(2024, 2, 28), date(2024, 3, 3)))
    assert [s.days for s in result] == [2, 2]
    assert result[0].last == date(2024, 2, 29)


def test_empty_period():
    for method in ["simple_monthly", "daily_compound"]:
        assert accrue(D("1.00"), D("0.03"), date(2026, 1, 1), date(2026, 1, 1), method) == []


@pytest.mark.parametrize("principal,rate", [(D("-1.00"), D("0.1")),
                                           (D("1.00"), D("-0.1")),
                                           (D("NaN"), D("0.1")),
                                           (D("1.001"), D("0.1"))])
def test_invalid_money(principal, rate):
    with pytest.raises(ValueError):
        accrue(principal, rate, date(2026, 1, 1), date(2026, 2, 1), "simple_monthly")


def test_invalid_dates_and_method():
    day = date(2026, 1, 1)
    for start, end, method in [(date(2026, 2, 1), day, "simple_monthly"),
                               (datetime(2026, 1, 1, tzinfo=timezone.utc), day, "simple_monthly"),
                               (day, day, "unknown")]:
        with pytest.raises(ValueError):
            accrue(D("1.00"), D("0.1"), start, end, method)
