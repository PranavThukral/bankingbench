from fees.schedule import compute_fee, Tier, Schedule


def test_tier_midpoints():
    schedule = Schedule([Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)], 0, 999999)
    for amount, expected in [(5000, 60), (15000, 95), (30000, 105)]:
        assert compute_fee(amount, schedule) == expected
