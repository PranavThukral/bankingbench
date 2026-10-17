"""Render synthetic SBF-80 fixtures for local previews."""
from datetime import date
from batch.models import Payment


def render(payments: list[Payment], batch_id="SYNTHETIC001", created=date(2026, 1, 1), currency="CAD", crlf=False):
    if len(batch_id) != 12:
        raise ValueError("batch id must have 12 characters")
    header = f"H{batch_id}{created:%Y%m%d}{currency}".ljust(80)
    rows = [header]
    for payment in payments:
        if len(payment.payee_account) != 12 or len(payment.reference) > 20:
            raise ValueError("field too wide")
        rows.append(f"D{payment.payee_account}{payment.amount_minor:012d}{payment.reference:<20}".ljust(80))
    total = sum(payment.amount_minor for payment in payments)
    hash_total = sum(int(payment.payee_account[-8:]) for payment in payments) % 10**10
    rows.append(f"T{len(payments):06d}{total:015d}{hash_total:010d}".ljust(80))
    separator = b"\r\n" if crlf else b"\n"
    return separator.join(row.encode("ascii") for row in rows) + separator
