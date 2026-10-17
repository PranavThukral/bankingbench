from decimal import Decimal, ROUND_HALF_UP, localcontext
from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor < 0:
        raise ValueError("invalid payment amount")
    selected = next(t for t in schedule.tiers if t.up_to_minor is None or t.up_to_minor >= amount_minor)
    with localcontext() as ctx:
        ctx.prec = max(34, len(str(amount_minor)) + len(str(selected.bps)) + 10)
        raw = Decimal(amount_minor) * Decimal(selected.bps) / Decimal(10000) + selected.fixed_minor
        fee = int(raw.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if fee < schedule.min_fee_minor:
        return schedule.min_fee_minor
    if fee > schedule.max_fee_minor:
        return schedule.max_fee_minor
    return fee
