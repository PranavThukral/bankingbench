"""JSON preview adapter for the accrual interface."""
import argparse
from dataclasses import dataclass
from decimal import Decimal
import json
from pathlib import Path

from interest.calendar import AccrualRequest
from interest.accrual import accrue


@dataclass(frozen=True)
class Preview:
    request: AccrualRequest

    def postings(self):
        r = self.request
        return accrue(r.principal, r.annual_rate, r.start, r.end, r.method)

    def to_dict(self):
        entries = self.postings()
        return {
            "request": self.request.as_dict(),
            "currency": "CAD",
            "postings": [{"date": p.posting_date.isoformat(), "interest": str(p.interest),
                          "balance": str(p.balance)} for p in entries],
            "total_interest": str(sum((Decimal(str(p.interest)) for p in entries), Decimal("0.00"))),
        }


def read_requests(path):
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(content, list):
        raise ValueError("request list required")
    return [AccrualRequest.from_dict(row) for row in content]


def render_requests(requests):
    return json.dumps([Preview(r).to_dict() for r in requests], indent=2) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic account postings")
    parser.add_argument("requests", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    rendered = render_requests(read_requests(args.requests))
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
