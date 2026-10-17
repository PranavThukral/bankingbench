from hypothesis import given, strategies as st
import pytest
from fees.schedule import compute_fee, Tier, Schedule


def expected(amount, tier, lo=0, hi=10**30):
    numerator = amount * tier.bps + tier.fixed_minor * 10000
    return min(hi, max(lo, (numerator + 5000) // 10000))


def test_inclusive_boundaries():
    tiers = [Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)]
    schedule = Schedule(tiers, 0, 10**20)
    for boundary in (10000, 20000):
        for amount in (boundary - 1, boundary, boundary + 1):
            tier = next(t for t in tiers if t.up_to_minor is None or amount <= t.up_to_minor)
            assert compute_fee(amount, schedule) == expected(amount, tier)


@pytest.mark.parametrize("amount,bps,want", [(5000, 3, 2), (25000, 3, 8), (35000, 3, 11)])
def test_discovered_float_ties(amount, bps, want):
    # Deterministic search results, see tools/rounding_cases.json.
    assert compute_fee(amount, Schedule([Tier(None, bps, 0)], 0, 100000)) == want


def test_non_marginal():
    schedule = Schedule([Tier(10000, 100, 10), Tier(None, 50, 20)], 0, 999999)
    assert compute_fee(15000, schedule) == 95


def test_clamps_and_zero():
    schedule = Schedule([Tier(None, 100, 5)], 10, 100)
    assert compute_fee(0, schedule) == 10
    assert compute_fee(1000000, schedule) == 100
    assert type(compute_fee(5000, schedule)) is int
    with pytest.raises(ValueError):
        compute_fee(-1, schedule)


@given(amount=st.integers(0, 10**15), extra=st.integers(0, 10**12), bps=st.integers(0, 10000),
       fixed=st.integers(0, 1000), floor=st.integers(0, 1000), cap=st.integers(1000, 10**16))
def test_fee_properties(amount, extra, bps, fixed, floor, cap):
    tier = Tier(None, bps, fixed)
    schedule = Schedule([tier], floor, cap)
    result = compute_fee(amount, schedule)
    assert type(result) is int and floor <= result <= cap
    assert result == expected(amount, tier, floor, cap)
    assert compute_fee(amount + extra, schedule) >= result
