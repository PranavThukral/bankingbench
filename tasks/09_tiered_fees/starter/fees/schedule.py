from fees.models import Tier, Schedule  # noqa: F401


def raw_fee(amount_minor, tier):
    """Percentage part plus fixed part, in whole minor units."""
    return amount_minor * tier.bps // 10000 + tier.fixed_minor


def compute_fee(amount_minor, schedule):
    return raw_fee(amount_minor, schedule.tiers[0])
