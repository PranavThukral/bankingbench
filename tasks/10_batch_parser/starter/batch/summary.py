"""Totals over the payments of a parse result, for dashboards and reconciliation checks."""


def format_minor(amount_minor, places=2):
    """Render integer minor units; callers pass the decimal places of the batch currency."""
    if places == 0:
        return str(amount_minor)
    major, minor = divmod(abs(amount_minor), 10 ** places)
    return f"{'-' if amount_minor < 0 else ''}{major}.{minor:0{places}d}"


def payee_totals(payments):
    """Amount per payee account, in order of first appearance."""
    totals = {}
    for payment in payments:
        totals[payment.payee_account] = totals.get(payment.payee_account, 0) + payment.amount_minor
    return totals


def summarize(result, places=2):
    return {
        "accepted": result.accepted,
        "payments": len(result.payments),
        "payees": len(payee_totals(result.payments)),
        "amount": format_minor(sum(p.amount_minor for p in result.payments), places),
        "errors": len(result.errors),
    }
