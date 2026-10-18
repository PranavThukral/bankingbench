"""Inspect a synthetic batch file without contacting any service."""
import argparse
import json
from pathlib import Path
from batch.csvout import write_payments_csv
from batch.errors import render_errors as explain_errors
from batch.parser import parse


def inspect(path):
    result = parse(Path(path).read_bytes())
    output = result.as_dict()
    output["summary"] = {
        "payment_count": len(result.payments),
        "amount_total_minor": sum(p.amount_minor for p in result.payments),
        "error_count": len(result.errors),
    }
    return output


def render_errors(result):
    return "\n".join(f"{error.line_no}: {error.code}" for error in result.errors)


def write_result(path, result):
    Path(path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect an invented SBF-80 batch")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--csv", type=Path, help="write the parsed payments to a CSV file")
    parser.add_argument("--explain", action="store_true", help="describe each error code on stderr")
    args = parser.parse_args(argv)
    result = inspect(args.input)
    if args.csv:
        write_payments_csv(args.csv, parse(Path(args.input).read_bytes()).payments)
    if args.explain:
        import sys
        sys.stderr.write(explain_errors(parse(Path(args.input).read_bytes()).errors))
    if args.out:
        write_result(args.out, result)
    else:
        print(json.dumps(result, indent=2))
    return int(not result["accepted"])


if __name__ == "__main__":
    raise SystemExit(main())
