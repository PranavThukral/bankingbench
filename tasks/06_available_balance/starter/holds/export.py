"""CSV export of authorization records for offline review."""
import csv
from datetime import datetime, timezone
from pathlib import Path
from holds.storage import all_authorizations, initialize, transaction

COLUMNS = ["auth_id", "account", "amount_minor", "created_at", "state"]


def iso(timestamp):
    """Render a stored epoch-seconds value as an aware UTC ISO-8601 string."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def export_authorizations(database_path, destination):
    initialize(database_path)
    with transaction(database_path) as db:
        records = all_authorizations(db)
    with Path(destination).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        for record in records:
            writer.writerow([record["id"], record["account"], record["amount"],
                             iso(record["created"]), record["state"]])
    return len(records)
