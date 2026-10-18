from decimal import Decimal, ROUND_HALF_EVEN
from fx.models import Quote, RateUnavailable, validate

__all__ = ["quote_transfer", "Quote", "RateUnavailable"]


def quote_transfer(amount_minor, src, dst, rates, fee_bps):
    validate(amount_minor, src, dst, fee_bps)
    try:
        rate = rates[src, dst]
    except KeyError as exc:
        raise RateUnavailable((src, dst)) from exc
    fee = int((Decimal(amount_minor) * fee_bps / 10000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    converted = int((Decimal(amount_minor) * rate).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
    return Quote(fee, converted, rate, (src, dst))
