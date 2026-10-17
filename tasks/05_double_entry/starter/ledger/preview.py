"""JSON adapter for a synthetic journal batch."""
import argparse
import json
import os
from pathlib import Path
from ledger.models import Line
from ledger.service import LedgerService


def load_batch(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("accounts", []), [Line.from_dict(row) for row in data["lines"]], data.get("memo", "")


def book(service, accounts, lines, memo):
    for account in accounts:
        service.create_account(account["code"], account["currency"])
    transaction = service.post(lines, memo)
    return {
        "transaction_id": transaction,
        "balances": {line.account_code: service.balance(line.account_code) for line in lines},
        "trial_balance": service.trial_balance(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book a synthetic journal JSON batch")
    parser.add_argument("batch", type=Path)
    args = parser.parse_args(argv)
    service = LedgerService(os.environ["DATABASE_URL"])
    print(json.dumps(book(service, *load_batch(args.batch)), indent=2))


if __name__ == "__main__":
    main()
