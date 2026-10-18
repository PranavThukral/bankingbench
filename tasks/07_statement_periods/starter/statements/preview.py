"""JSON adapter for statement selection previews."""
import argparse
import json
from pathlib import Path
from statements.models import Txn, PeriodRequest, Selection
from statements.months import iter_months, parse_month
from statements.render import render_selection
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


def preview_range(txns, account_tz, first, last):
    """One Selection per calendar month from `first` through `last` (both (year, month) pairs)."""
    return [preview(txns, PeriodRequest(account_tz, year, month)) for year, month in iter_months(first, last)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview a synthetic monthly statement")
    parser.add_argument("transactions", type=Path)
    parser.add_argument("request", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--through", help="also produce every month up to YYYY-MM as a text listing")
    args = parser.parse_args(argv)
    txns, request = read_txns(args.transactions), read_request(args.request)
    if args.through:
        last = parse_month(args.through)
        listing = "".join(render_selection(item, txns) for item in
                          preview_range(txns, request.account_tz, (request.year, request.month), last))
        print(listing, end="")
        return
    result = preview(txns, request)
    text = json.dumps(result.as_dict(), indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
