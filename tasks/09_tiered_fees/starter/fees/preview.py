"""Offline fee preview input/output."""
import argparse
import csv
from pathlib import Path
from fees.catalog import get_schedule
from fees.loader import load_schedule_file
from fees.models import FeePreview
from fees.report import render_summary
from fees.schedule import compute_fee


def read_schedule(source):
    """A schedule file path, or `name:<catalog name>` for a built-in synthetic schedule."""
    if str(source).startswith("name:"):
        return get_schedule(str(source)[5:])
    return load_schedule_file(source)


def preview(amounts, schedule):
    return [FeePreview(amount, compute_fee(amount, schedule)) for amount in amounts]


def read_amounts(path):
    """Read the `amount_minor` column; report the file line of any unusable value."""
    amounts = []
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if "amount_minor" not in (reader.fieldnames or []):
            raise ValueError("amount_minor column required")
        for row in reader:
            text = (row["amount_minor"] or "").strip()
            if not text.isdigit():
                raise ValueError(f"line {reader.line_num}: amount_minor must be a nonnegative integer")
            amounts.append(int(text))
    return amounts


def write_preview(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=["amount_minor", "fee_minor", "total_minor"])
        output.writeheader()
        output.writerows(row.as_dict() for row in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic payment fees")
    parser.add_argument("schedule", help="schedule JSON file or name:<catalog name>")
    parser.add_argument("amounts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", action="store_true", help="also print totals for the preview")
    args = parser.parse_args(argv)
    rows = preview(read_amounts(args.amounts), read_schedule(args.schedule))
    write_preview(args.output, rows)
    if args.summary:
        print(render_summary(rows), end="")


if __name__ == "__main__":
    main()
