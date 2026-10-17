import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from statements.models import Txn  # noqa: F401


def period_bounds(account_tz, year, month):
    local_first = datetime.fromisoformat(f"{year:04d}-{month:02d}-01T00:00:00").replace(tzinfo=ZoneInfo(account_tz))
    local_next = local_first + timedelta(days=calendar.monthrange(year, month)[1])
    return tuple(point.astimezone(timezone.utc) for point in (local_first, local_next))


def select(txns, account_tz, year, month):
    timezone_for_account = ZoneInfo(account_tz)
    keyed = []
    for item in txns:
        stamp = item.at
        if stamp.utcoffset() is None:
            raise ValueError("transaction timestamp has no offset")
        local = stamp.astimezone(timezone_for_account)
        if (local.year, local.month) == (year, month):
            keyed.append((stamp.astimezone(timezone.utc), item.id))
    keyed.sort()
    return [identifier for _, identifier in keyed]
