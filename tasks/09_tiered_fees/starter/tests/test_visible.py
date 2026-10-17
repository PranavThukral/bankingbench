from fees.schedule import compute_fee, Tier, Schedule


def test_one_tier():
    assert compute_fee(1000, Schedule([Tier(None, 100, 5)], 0, 99999)) == 15


def test_minimum():
    assert compute_fee(1, Schedule([Tier(None, 100, 0)], 10, 99999)) == 10
