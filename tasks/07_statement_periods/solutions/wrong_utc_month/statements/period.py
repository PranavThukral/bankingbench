from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from statements.models import Txn  # noqa: F401

MIN_YEAR, MAX_YEAR = 1900, 2098


def load_zone(account_tz):
    try:
        return ZoneInfo(account_tz)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError) as exc:
        raise ValueError(f"unknown time zone: {account_tz!r}") from exc


def check_month(year, month):
    if type(year) is not int or type(month) is not int:
        raise ValueError("integer year and month required")
    if not MIN_YEAR <= year <= MAX_YEAR or not 1 <= month <= 12:
        raise ValueError("month out of range")


def month_start(zone, year, month):
    return datetime(year, month, 1, tzinfo=zone)


def instant(txn):
    return txn.at.astimezone(timezone.utc)


def period_bounds(account_tz, year, month):
    check_month(year, month)
    load_zone(account_tz)
    start = month_start(timezone.utc, year, month)
    end = month_start(timezone.utc, year + (month == 12), month % 12 + 1)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def select(txns, account_tz, year, month):
    start, end = period_bounds(account_tz, year, month)
    for txn in txns:
        if txn.at.tzinfo is None or txn.at.utcoffset() is None:
            raise ValueError("aware timestamps required")
    chosen = [t for t in txns if start <= instant(t) < end]
    return [t.id for t in sorted(chosen, key=lambda t: (instant(t), t.id))]
