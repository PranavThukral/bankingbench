from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    for tier in schedule.tiers:
        if tier.up_to_minor is None or amount_minor <= tier.up_to_minor:
            numerator = amount_minor * tier.bps + tier.fixed_minor * 10000
            rounded = (numerator + 5000) // 10000
            return rounded
    raise ValueError("unbounded tier required")
