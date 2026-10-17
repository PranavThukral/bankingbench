"""Offline synthetic refund request processing."""
import argparse
import json
from pathlib import Path
from refunds.models import RefundRequest, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount
from refunds.service import RefundService


def read_requests(path):
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    return [RefundRequest.from_dict(row) for row in content]


def process(service, requests):
    output = []
    for request in requests:
        try:
            identifier = service.refund(request.payment_id, request.amount_minor)
            row = {"accepted": True, "refund_id": identifier}
        except (RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount) as exc:
            row = {"accepted": False, "error": type(exc).__name__}
        row["request"] = request.as_dict()
        output.append(row)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic refunds")
    parser.add_argument("database", type=Path)
    parser.add_argument("requests", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(process(RefundService(args.database), read_requests(args.requests)), indent=2))


if __name__ == "__main__":
    main()
