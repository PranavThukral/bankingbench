import pytest
from fees.models import Tier, Schedule, FeePreview
from fees.schedule import compute_fee


def test_tier_roundtrip():
    tier = Tier(None, 100, 5)
    assert Tier.from_dict(tier.as_dict()) == tier


def test_schedule_roundtrip():
    schedule = Schedule([Tier(1000, 100, 1), Tier(None, 50, 2)], 0, 1000)
    assert Schedule.from_dict(schedule.as_dict()) == schedule


def test_preview_total():
    assert FeePreview(100, 5).as_dict() == {"amount_minor": 100, "fee_minor": 5, "total_minor": 105}


@pytest.mark.parametrize("amount", [-1, True, 1.5, "100"])
def test_invalid_amount(amount):
    with pytest.raises(ValueError):
        compute_fee(amount, Schedule([Tier(None, 100, 0)], 0, 100))


@pytest.mark.parametrize("tiers", [[], [Tier(1000, 1, 0)],
                                   [Tier(1000, 1, 0), Tier(1000, 2, 0), Tier(None, 3, 0)],
                                   [Tier(None, 1, 0), Tier(None, 2, 0)]])
def test_invalid_tier_order(tiers):
    with pytest.raises(ValueError):
        compute_fee(100, Schedule(tiers, 0, 100))


def test_invalid_limits():
    for floor, cap in [(-1, 10), (20, 10), (0, -1)]:
        with pytest.raises(ValueError):
            compute_fee(100, Schedule([Tier(None, 100, 0)], floor, cap))


def test_invalid_tier_components():
    for fields in [(-1, 100, 0), (None, -1, 0), (None, 100, -1)]:
        with pytest.raises(ValueError):
            Tier(*fields)
