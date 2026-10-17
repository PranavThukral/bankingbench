"""JSON adapter for statement selection previews."""
import argparse
import json
from pathlib import Path
from statements.models import Txn, PeriodRequest, Selection
from statements.period import period_bounds, select


def read_txns(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Txn.from_dict(row) for row in data]


def read_request(path):
    return PeriodRequest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def preview(txns, request):
    start, end = period_bounds(request.account_tz, request.year, request.month)
    ids = select(txns, request.account_tz, request.year, request.month)
    return Selection(request, start, end, ids)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview a synthetic monthly statement")
    parser.add_argument("transactions", type=Path)
    parser.add_argument("request", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = preview(read_txns(args.transactions), read_request(args.request))
    text = json.dumps(result.as_dict(), indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
