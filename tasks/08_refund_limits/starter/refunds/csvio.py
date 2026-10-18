"""CSV import of refund requests and export of their outcomes."""
import csv
from pathlib import Path
from refunds.models import RefundRequest

RESULT_COLUMNS = ["payment_id", "amount_minor", "accepted", "refund_id", "error"]


def read_requests_csv(path):
    requests = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            try:
                requests.append(RefundRequest.from_dict(
                    {"payment_id": int(row["payment_id"]), "amount_minor": int(row["amount_minor"])}))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"line {reader.line_num}: unusable refund request") from exc
    return requests


def write_results_csv(path, results):
    """`results` are the dictionaries produced by refunds.preview.process."""
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(RESULT_COLUMNS)
        for row in results:
            writer.writerow([row["request"]["payment_id"], row["request"]["amount_minor"], row["accepted"],
                             row.get("refund_id", ""), row.get("error", "")])
