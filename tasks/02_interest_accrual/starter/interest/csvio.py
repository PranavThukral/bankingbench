"""CSV import of accrual requests and export of the resulting postings."""
import csv
from pathlib import Path

from interest.calendar import AccrualRequest

REQUEST_COLUMNS = ["principal", "annual_rate", "start", "end", "method"]
POSTING_COLUMNS = ["request_line", "posting_date", "interest", "balance"]


def read_requests_csv(path):
    requests = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != REQUEST_COLUMNS:
            raise ValueError("expected columns: " + ",".join(REQUEST_COLUMNS))
        for row in reader:
            try:
                requests.append(AccrualRequest.from_dict(row))
            except (ArithmeticError, ValueError) as exc:
                raise ValueError(f"line {reader.line_num}: invalid accrual request") from exc
    return requests


def write_postings_csv(path, requests, accrue):
    """Write every request's postings; `accrue` is the accrual function to call for each request."""
    rows = 0
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(POSTING_COLUMNS)
        for line_no, r in enumerate(requests, start=2):
            for posting in accrue(r.principal, r.annual_rate, r.start, r.end, r.method):
                writer.writerow([line_no, posting.posting_date.isoformat(), posting.interest, posting.balance])
                rows += 1
    return rows
