from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fx.models import Quote, RateUnavailable, UNITS, validate

__all__ = ["quote_transfer", "Quote", "RateUnavailable"]


def quote_transfer(amount_minor, src, dst, rates, fee_bps):
    validate(amount_minor, src, dst, fee_bps)
    with localcontext() as ctx:
        ctx.prec = max(50, len(str(amount_minor)) + sum(len(r.as_tuple().digits) for r in rates.values()) + 20)
        if (src, dst) in rates:
            rate, path = rates[src, dst], (src, dst)
        else:
            try:
                rate = rates[src, "USD"] * rates["USD", dst]
            except KeyError as exc:
                raise RateUnavailable((src, dst)) from exc
            path = (src, "USD", dst)
        fee = int((Decimal(amount_minor) * fee_bps / 10000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        net = Decimal(amount_minor).scaleb(-UNITS[src])
        converted = int((net * rate).scaleb(UNITS[dst]).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        converted -= int((Decimal(converted) * fee_bps / 10000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))
        return Quote(fee, converted, rate, path)
