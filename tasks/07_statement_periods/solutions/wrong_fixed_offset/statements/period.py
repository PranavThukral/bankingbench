from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from statements.models import Txn  # noqa: F401


def period_bounds(account_tz, year, month):
    iana = ZoneInfo(account_tz)
    january = datetime(year, 1, 1, tzinfo=iana)
    zone = timezone(january.utcoffset() - january.dst())
    start = datetime(year, month, 1, tzinfo=zone)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def select(txns, account_tz, year, month):
    start, end = period_bounds(account_tz, year, month)
    for txn in txns:
        if txn.at.tzinfo is None or txn.at.utcoffset() is None:
            raise ValueError("aware timestamps required")
    chosen = [t for t in txns if start <= t.at.astimezone(timezone.utc) < end]
    return [t.id for t in sorted(chosen, key=lambda t: (t.at.astimezone(timezone.utc), t.id))]
