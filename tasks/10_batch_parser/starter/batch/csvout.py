"""Write parsed payments to CSV for downstream tools."""
import csv
from pathlib import Path

COLUMNS = ["payee_account", "amount_minor", "reference"]


def write_payments_csv(path, payments):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        for payment in payments:
            writer.writerow([payment.payee_account, payment.amount_minor, payment.reference])
    return len(payments)
