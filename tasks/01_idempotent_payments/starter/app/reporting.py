"""Merchant-facing summaries over stored payment receipts."""
import argparse
import os

from app.contracts import CURRENCIES
from app.storage import PaymentStore


def format_amount(amount_minor, currency):
    """Render integer minor units using the currency's decimal places (JPY 0, KWD/BHD 3, others 2)."""
    places = CURRENCIES[currency]
    if places == 0:
        return f"{amount_minor} {currency}"
    major, minor = divmod(amount_minor, 10 ** places)
    return f"{major}.{minor:0{places}d} {currency}"


def merchant_totals(payments):
    """Per currency: number of payments and total amount, split by gateway status."""
    totals = {}
    for payment in payments:
        entry = totals.setdefault(payment.currency, {"succeeded": [0, 0], "declined": [0, 0]})
        bucket = entry[payment.status]
        bucket[0] += 1
        bucket[1] += payment.amount_minor
    return totals


def render_merchant_report(merchant, payments):
    lines = [f"Merchant {merchant}: {len(payments)} payment(s)"]
    for currency, entry in sorted(merchant_totals(payments).items()):
        for status in ("succeeded", "declined"):
            count, total = entry[status]
            if count:
                lines.append(f"  {currency} {status:<9} {count:>4}  {format_amount(total, currency)}")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print a payment summary for one merchant")
    parser.add_argument("merchant")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args(argv)
    if not args.database_url:
        parser.error("--database-url or DATABASE_URL required")
    store = PaymentStore(args.database_url)
    print(render_merchant_report(args.merchant, store.list_for_merchant(args.merchant)), end="")


if __name__ == "__main__":
    main()
