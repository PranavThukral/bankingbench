"""CSV rate-book transport for offline quote previews."""
import csv
from pathlib import Path
from fx.models import read_rates, render_rates, QuoteRequest


def read_rate_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["src", "dst", "rate"]:
            raise ValueError("expected src,dst,rate columns")
        return read_rates(list(reader))


def write_rate_csv(path, rates):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["src", "dst", "rate"])
        writer.writeheader()
        writer.writerows(render_rates(rates))


def read_request_csv(path):
    result = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["amount_minor", "src", "dst", "fee_bps"]:
            raise ValueError("invalid request columns")
        for row in reader:
            request = QuoteRequest(int(row["amount_minor"]), row["src"], row["dst"], int(row["fee_bps"]))
            result.append(request)
    return result


def write_request_csv(path, requests):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["amount_minor", "src", "dst", "fee_bps"])
        writer.writeheader()
        writer.writerows(request.as_dict() for request in requests)
