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


def marginal_fee(amount_minor, schedule):
    """Charge each band at its own rate; the fixed fee of the band that contains the amount is added."""
    total, lower = 0, 0
    for tier in schedule.tiers:
        upper = amount_minor if tier.up_to_minor is None else min(amount_minor, tier.up_to_minor)
        total += max(0, upper - lower) * tier.bps
        if upper == amount_minor:
            total += tier.fixed_minor * 10000
            break
        lower = upper
    return (total + 5000) // 10000


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    validate_schedule(schedule)
    fee = marginal_fee(amount_minor, schedule)
    return min(schedule.max_fee_minor, max(schedule.min_fee_minor, fee))
