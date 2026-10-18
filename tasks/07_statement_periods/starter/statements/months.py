"""Calendar-month arithmetic for statement runs. Pure integer logic; no time zones involved."""


def parse_month(text):
    """Parse `YYYY-MM` into a (year, month) pair."""
    try:
        year_text, month_text = text.split("-")
        year, month = int(year_text), int(month_text)
    except ValueError:
        raise ValueError(f"expected YYYY-MM, got {text!r}") from None
    if not 1 <= month <= 12:
        raise ValueError(f"month out of range in {text!r}")
    return year, month


def format_month(year, month):
    return f"{year:04d}-{month:02d}"


def next_month(year, month):
    return (year + (month == 12), month % 12 + 1)


def previous_month(year, month):
    return (year - (month == 1), (month - 2) % 12 + 1)


def iter_months(first, last):
    """Every (year, month) from `first` through `last`, inclusive; empty when last precedes first."""
    current = first
    while current <= last:
        yield current
        current = next_month(*current)
