"""CSV journal import: group rows into entries and book them through the public service."""
import csv
from pathlib import Path
from ledger.models import Line, LedgerError

COLUMNS = ["entry", "memo", "account_code", "side", "amount_minor"]


def read_entries(path):
    """Return [(entry_key, memo, [Line, ...])] in file order; rows with one key form one entry."""
    entries = {}
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != COLUMNS:
            raise ValueError("expected columns: " + ",".join(COLUMNS))
        for row in reader:
            key = row["entry"]
            memo, lines = entries.setdefault(key, (row["memo"], []))
            lines.append(Line(row["account_code"], row["side"], int(row["amount_minor"])))
    return [(key, memo, lines) for key, (memo, lines) in entries.items()]


def book_all(service, entries):
    """Post every entry; a rejected entry is reported by error name and does not stop the run."""
    booked, rejected = {}, {}
    for key, memo, lines in entries:
        try:
            booked[key] = service.post(lines, memo)
        except LedgerError as exc:
            rejected[key] = type(exc).__name__
    return booked, rejected
