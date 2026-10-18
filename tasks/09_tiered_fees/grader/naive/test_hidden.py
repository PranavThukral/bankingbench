import pytest
from fees.schedule import compute_fee, Tier, Schedule


def test_tier_midpoints():
    schedule = Schedule([Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)], 0, 999999)
    for amount, expected in [(5000, 60), (15000, 95), (30000, 105)]:
        assert compute_fee(amount, schedule) == expected


def test_ticket_worked_example_with_clamps():
    schedule = Schedule([Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)], 25, 100)
    for amount, expected in [(5000, 60), (15000, 95), (100, 25), (30000, 100)]:
        assert compute_fee(amount, schedule) == expected


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        compute_fee(-1, Schedule([Tier(None, 100, 0)], 0, 1000))
