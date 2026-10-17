from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer required")
    total, lower = 0, 0
    for tier in schedule.tiers:
        upper = amount_minor if tier.up_to_minor is None else min(amount_minor, tier.up_to_minor)
        total += max(0, upper - lower) * tier.bps
        if upper == amount_minor:
            total += tier.fixed_minor * 10000
            break
        lower = upper
    return min(schedule.max_fee_minor, max(schedule.min_fee_minor, (total + 5000) // 10000))
