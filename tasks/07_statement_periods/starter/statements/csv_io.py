"""CSV transport for offline statement previews."""
import csv
from datetime import datetime
from pathlib import Path
from statements.models import Txn


def read_csv(path):
    transactions = []
    seen = set()
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["id", "at"]:
            raise ValueError("expected id,at columns")
        for row in reader:
            identifier = row["id"]
            at = datetime.fromisoformat(row["at"])
            if not identifier or identifier in seen:
                raise ValueError("unique nonempty ids required")
            if at.utcoffset() is None:
                raise ValueError("aware timestamps required")
            seen.add(identifier)
            transactions.append(Txn(identifier, at))
    return transactions


def write_csv(path, txns):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "at"])
        writer.writeheader()
        writer.writerows(txn.as_dict() for txn in txns)
