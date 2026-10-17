"""Offline fee preview input/output."""
import argparse
import csv
import json
from pathlib import Path
from fees.models import Schedule, FeePreview
from fees.schedule import compute_fee


def read_schedule(path):
    return Schedule.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def preview(amounts, schedule):
    return [FeePreview(amount, compute_fee(amount, schedule)) for amount in amounts]


def read_amounts(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return [int(row["amount_minor"]) for row in csv.DictReader(stream)]


def write_preview(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=["amount_minor", "fee_minor", "total_minor"])
        output.writeheader()
        output.writerows(row.as_dict() for row in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic payment fees")
    parser.add_argument("schedule", type=Path)
    parser.add_argument("amounts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_preview(args.output, preview(read_amounts(args.amounts), read_schedule(args.schedule)))


if __name__ == "__main__":
    main()
