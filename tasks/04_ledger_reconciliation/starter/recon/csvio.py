"""CSV import and export for offline reconciliation runs."""
import csv
from pathlib import Path
from recon.models import StatementLine, LedgerEntry

STATEMENT_COLUMNS = ["id", "value_date", "amount_minor", "reference"]
LEDGER_COLUMNS = ["id", "booking_date", "amount_minor", "reference", "kind", "original_reference"]


def _rows(path, columns):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [name for name in columns[:4] if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"missing columns: {', '.join(missing)}")
        return list(reader)


def read_statement_csv(path):
    return [StatementLine.from_dict(row) for row in _rows(path, STATEMENT_COLUMNS)]


def read_ledger_csv(path):
    rows = _rows(path, LEDGER_COLUMNS)
    return [LedgerEntry.from_dict({**row, "kind": row.get("kind") or "payment",
                                   "original_reference": row.get("original_reference") or None})
            for row in rows]


def write_unmatched_csv(path, result, statement):
    by_id = {line.id: line for line in statement}
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "value_date", "amount_minor", "reference", "reason"])
        for identifier in sorted(result.unmatched_statement):
            line = by_id[identifier]
            writer.writerow([line.id, line.value_date.isoformat(), line.amount_minor,
                             line.reference, result.unmatched_statement[identifier]])
