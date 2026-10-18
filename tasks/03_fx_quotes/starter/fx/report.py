"""Plain-text quote sheets for the treasury desk."""
from decimal import Decimal
from fx.models import UNITS


def format_minor(amount_minor, currency):
    """Render integer minor units with the decimal places of the currency."""
    places = UNITS[currency]
    if places == 0:
        return f"{amount_minor} {currency}"
    major, minor = divmod(abs(amount_minor), 10 ** places)
    return f"{'-' if amount_minor < 0 else ''}{major}.{minor:0{places}d} {currency}"


def render_quote(request, quote):
    route = " > ".join(quote.path)
    return (f"{format_minor(request.amount_minor, request.src):>18} -> {format_minor(quote.converted_minor, request.dst):>18}"
            f"  fee {format_minor(quote.fee_minor, request.src):>14}  rate {quote.rate_used}  via {route}")


def render_sheet(requests, quotes):
    lines = [f"{len(requests)} quote(s)"] + [render_quote(r, q) for r, q in zip(requests, quotes)]
    return "\n".join(lines) + "\n"


def describe_ratebook(rates):
    """One line per declared pair, sorted; rates are shown exactly as stored."""
    return "\n".join(f"{src}->{dst} {Decimal(rate)}" for (src, dst), rate in sorted(rates.items())) + "\n"
