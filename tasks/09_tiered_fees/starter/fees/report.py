"""Summaries of fee previews for the pricing desk. Integer arithmetic only."""


def format_minor(minor):
    major, cents = divmod(abs(minor), 100)
    return f"{'-' if minor < 0 else ''}{major}.{cents:02d}"


def effective_bps(row):
    """Fee as basis points of the amount, truncated; zero amounts have no meaningful rate."""
    return 0 if row.amount_minor == 0 else row.fee_minor * 10000 // row.amount_minor


def summarize(rows):
    rows = list(rows)
    return {
        "count": len(rows),
        "amount_total_minor": sum(r.amount_minor for r in rows),
        "fee_total_minor": sum(r.fee_minor for r in rows),
        "max_effective_bps": max((effective_bps(r) for r in rows), default=0),
    }


def render_summary(rows):
    data = summarize(rows)
    return (f"payments: {data['count']}\n"
            f"amount total: {format_minor(data['amount_total_minor'])}\n"
            f"fee total: {format_minor(data['fee_total_minor'])}\n"
            f"highest effective rate: {data['max_effective_bps']} bps\n")


def describe_schedule(schedule):
    """One line per tier plus the clamp, for operator-facing output."""
    out = []
    for tier in schedule.tiers:
        bound = "any amount" if tier.up_to_minor is None else f"up to {format_minor(tier.up_to_minor)}"
        out.append(f"{bound}: {tier.bps} bps + {format_minor(tier.fixed_minor)}")
    out.append(f"fee limits: {format_minor(schedule.min_fee_minor)} to {format_minor(schedule.max_fee_minor)}")
    return "\n".join(out) + "\n"
