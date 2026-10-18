import math

from fees.models import Tier, Schedule, nonnegative  # noqa: F401


def validate_schedule(schedule):
    tiers = schedule.tiers
    if not tiers or tiers[-1].up_to_minor is not None:
        raise ValueError("unbounded last tier required")
    if not nonnegative(schedule.min_fee_minor) or not nonnegative(schedule.max_fee_minor):
        raise ValueError("invalid limits")
    if schedule.min_fee_minor > schedule.max_fee_minor:
        raise ValueError("invalid clamp interval")
    prior = -1
    for tier in tiers[:-1]:
        if tier.up_to_minor is None or tier.up_to_minor <= prior:
            raise ValueError("strictly increasing bounded tiers required")
        prior = tier.up_to_minor


def select_tier(amount_minor, schedule):
    for tier in schedule.tiers:
        if tier.up_to_minor is None or amount_minor <= tier.up_to_minor:
            return tier
    raise ValueError("unbounded tier required")


def raw_fee(amount_minor, tier):
    """Percentage part plus fixed part, rounded half up to a whole minor unit."""
    return math.floor(amount_minor * (tier.bps / 10000) + tier.fixed_minor + .5)


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    validate_schedule(schedule)
    fee = raw_fee(amount_minor, select_tier(amount_minor, schedule))
    return min(schedule.max_fee_minor, max(schedule.min_fee_minor, fee))
