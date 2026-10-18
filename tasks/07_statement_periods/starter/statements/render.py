"""Plain-text statement listings that show transaction times in the account's own zone."""
from zoneinfo import ZoneInfo


def local_text(at, account_tz):
    return at.astimezone(ZoneInfo(account_tz)).strftime("%Y-%m-%d %H:%M:%S %Z")


def render_selection(selection, txns):
    """List the selected transactions of a Selection with local times; `txns` are the input records."""
    by_id = {txn.id: txn for txn in txns}
    zone = selection.request.account_tz
    lines = [f"Statement {selection.request.year:04d}-{selection.request.month:02d} ({zone})",
             f"Period: {selection.start.isoformat()} to {selection.end.isoformat()}"]
    for identifier in selection.ids:
        lines.append(f"  {identifier:<12} {local_text(by_id[identifier].at, zone)}")
    lines.append(f"{len(selection.ids)} transaction(s)")
    return "\n".join(lines) + "\n"


def summary_rows(selections):
    """(label, transaction count) per selection, in the order given."""
    return [(f"{s.request.year:04d}-{s.request.month:02d}", len(s.ids)) for s in selections]


def render_summary(selections):
    rows = summary_rows(selections)
    width = max((len(label) for label, _ in rows), default=5)
    lines = [f"{'month':<{width}}  count"] + [f"{label:<{width}}  {count:>5}" for label, count in rows]
    lines.append(f"{'total':<{width}}  {sum(count for _, count in rows):>5}")
    return "\n".join(lines) + "\n"
