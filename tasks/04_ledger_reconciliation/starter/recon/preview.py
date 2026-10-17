"""Transport layer for offline reconciliation previews."""
import argparse
import json
from pathlib import Path
from recon.models import StatementLine, LedgerEntry
from recon.engine import reconcile


def read_statement(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [StatementLine.from_dict(row) for row in rows]


def read_ledger(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LedgerEntry.from_dict(row) for row in rows]


def preview(statement, ledger):
    result = reconcile(statement, ledger)
    data = result.as_dict()
    data["counts"] = {
        "statement": len(statement),
        "ledger": len(ledger),
        "matches": len(result.matches),
        "unmatched_statement": len(result.unmatched_statement),
        "unmatched_ledger": len(result.unmatched_ledger),
    }
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reconcile synthetic JSON records")
    parser.add_argument("statement", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    data = preview(read_statement(args.statement), read_ledger(args.ledger))
    rendered = json.dumps(data, indent=2) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
