from datetime import datetime, timezone
from statements.models import Txn  # noqa: F401


def month_start(zone, year, month):
    return datetime(year, month, 1, tzinfo=zone)


def instant(txn):
    return txn.at.astimezone(timezone.utc)


def period_bounds(account_tz, year, month):
    start = month_start(timezone.utc, year, month)
    end = month_start(timezone.utc, year + (month == 12), month % 12 + 1)
    return start, end


def select(txns, account_tz, year, month):
    start, end = period_bounds(account_tz, year, month)
    for txn in txns:
        if txn.at.tzinfo is None or txn.at.utcoffset() is None:
            raise ValueError("aware timestamps required")
    chosen = [t for t in txns if start <= instant(t) < end]
    return [t.id for t in sorted(chosen, key=instant)]
