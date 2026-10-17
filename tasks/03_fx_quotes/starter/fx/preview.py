"""JSON quote preview adapter."""
import argparse
import json
from pathlib import Path
from fx.models import QuoteRequest, read_rates, render_rates
from fx.quote import quote_transfer


def read_input(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    requests = [QuoteRequest.from_dict(row) for row in data["requests"]]
    rates = read_rates(data["rates"])
    return requests, rates


def preview(requests, rates):
    quotes = []
    for request in requests:
        quote = quote_transfer(request.amount_minor, request.src, request.dst, rates, request.fee_bps)
        quotes.append({"request": request.as_dict(), "quote": quote.as_dict()})
    return {"rates": render_rates(rates), "quotes": quotes}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic currency quotes")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    content = json.dumps(preview(*read_input(args.input)), indent=2) + "\n"
    if args.out:
        args.out.write_text(content, encoding="utf-8")
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
