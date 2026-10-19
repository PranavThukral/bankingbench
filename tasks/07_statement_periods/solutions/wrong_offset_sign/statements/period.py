from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from statements.models import Txn  # noqa: F401


def month_start(zone, year, month):
    return datetime(year, month, 1, tzinfo=zone)


def instant(txn):
    return txn.at.astimezone(timezone.utc)


def period_bounds(account_tz, year, month):
    if type(year) is not int or type(month) is not int:
        raise ValueError("integer year and month required")
    if not 1900 <= year <= 2098 or not 1 <= month <= 12:
        raise ValueError("month out of range")
    try:
        zone = ZoneInfo(account_tz)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError) as exc:
        raise ValueError(f"unknown time zone: {account_tz!r}") from exc
    start = month_start(zone, year, month)
    end = month_start(zone, year + (month == 12), month % 12 + 1)
    # Translate the local wall-clock boundaries by their respective UTC offsets.
    return (start.replace(tzinfo=timezone.utc) + start.utcoffset(),
            end.replace(tzinfo=timezone.utc) + end.utcoffset())


def select(txns, account_tz, year, month):
    start, end = period_bounds(account_tz, year, month)
    for txn in txns:
        if txn.at.tzinfo is None or txn.at.utcoffset() is None:
            raise ValueError("aware timestamps required")
    chosen = [t for t in txns if start <= instant(t) < end]
    return [t.id for t in sorted(chosen, key=lambda t: (instant(t), t.id))]
