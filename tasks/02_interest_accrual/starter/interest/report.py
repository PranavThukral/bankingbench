"""Plain-text statement of postings for the account servicing desk."""
from decimal import Decimal

CENT = Decimal("0.01")


def format_money(value):
    """Render a CAD amount with thousands separators and exactly two decimals."""
    return f"{Decimal(value).quantize(CENT):,}"


def total_interest(postings):
    return sum((Decimal(str(p.interest)) for p in postings), Decimal("0.00"))


def effective_rate_percent(opening_balance, postings):
    """Interest earned as a percentage of the opening balance, to 4 decimal places (display only)."""
    if not postings or Decimal(opening_balance) == 0:
        return Decimal("0.0000")
    return (total_interest(postings) * 100 / Decimal(opening_balance)).quantize(Decimal("0.0001"))


def render_statement(request, postings):
    lines = [f"Account interest, {request.start.isoformat()} to {request.end.isoformat()} ({request.method})",
             f"Opening balance: {format_money(request.principal)}   Rate: {request.annual_rate}"]
    for posting in postings:
        lines.append(f"  {posting.posting_date.isoformat()}  interest {format_money(posting.interest):>12}"
                     f"  balance {format_money(posting.balance):>16}")
    lines.append(f"Total interest: {format_money(total_interest(postings))}"
                 f" ({effective_rate_percent(request.principal, postings)}% of opening balance)")
    return "\n".join(lines) + "\n"
