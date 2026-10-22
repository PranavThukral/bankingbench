"""Clean-room SBF-80 parser written from PROBLEM.md only (reviewer). Record objects + rule table."""
from datetime import date
from batch.models import BatchResult, Payment, BatchError  # noqa: F401

CURRENCIES = ("CAD", "USD", "EUR", "GBP", "JPY", "KWD", "BHD")
UPPER_DIGIT = set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
DIGITS = set(b"0123456789")


def split_records(data):
    if not data:
        return []
    parts = data.split(b"\n")
    last = parts.pop() if parts[-1] == b"" else None
    cleaned = [p[:-1] if p.endswith(b"\r") else p for p in parts]
    if last is not None:
        return cleaned
    return cleaned  # unterminated final line was kept as parts[-1]; its own CR (if any) is stripped only when LF-terminated


def split_records_strict(data):
    if not data:
        return []
    parts = data.split(b"\n")
    terminated = parts[-1] == b""
    if terminated:
        parts.pop()
    out = []
    for i, p in enumerate(parts):
        has_lf = i < len(parts) - 1 or terminated
        out.append(p[:-1] if has_lf and p.endswith(b"\r") else p)
    return out


def all_in(chunk, allowed):
    return len(chunk) > 0 and all(c in allowed for c in chunk)


def valid_date(chunk):
    if not all_in(chunk, DIGITS):
        return False
    try:
        date(int(chunk[:4]), int(chunk[4:6]), int(chunk[6:8]))
        return True
    except ValueError:
        return False


def header_valid(r):
    return (all_in(r[1:13], UPPER_DIGIT) and valid_date(r[13:21])
            and r[21:24].decode() in CURRENCIES and r[24:80] == b" " * 56)


def detail_valid(r):
    return (all_in(r[1:13], DIGITS) and all_in(r[13:25], DIGITS) and int(r[13:25]) > 0
            and r[25:45].strip(b" ") != b"" and r[45:80] == b" " * 35)


def trailer_valid(r):
    return all_in(r[1:7], DIGITS) and all_in(r[7:22], DIGITS) and all_in(r[22:32], DIGITS) and r[32:80] == b" " * 48


def parse(data):
    records = split_records_strict(data)
    total = len(records)
    errors = set()
    good_details, trailers, d_seen = [], [], 0
    if total == 0 or records[0][:1] != b"H":
        errors.add((1, "missing_header"))
    if total == 0 or records[-1][:1] != b"T":
        errors.add((max(total, 1), "missing_trailer"))
    for number, record in enumerate(records, start=1):
        kind = record[:1]
        if kind == b"D":
            d_seen += 1
        if (kind == b"H" and number != 1) or (kind == b"T" and number != total) or (kind == b"D" and number in (1, total)):
            errors.add((number, "record_order"))
        if any(b < 0x20 or b > 0x7E for b in record):
            errors.add((number, "invalid_encoding"))
            continue
        if len(record) != 80:
            errors.add((number, "line_length"))
            continue
        if kind == b"H":
            if not header_valid(record):
                errors.add((number, "invalid_header"))
        elif kind == b"D":
            if detail_valid(record):
                good_details.append(Payment(record[1:13].decode(), int(record[13:25]), record[25:45].rstrip(b" ").decode()))
            else:
                errors.add((number, "invalid_detail"))
        elif kind == b"T":
            if trailer_valid(record):
                trailers.append((number, int(record[1:7]), int(record[7:22]), int(record[22:32])))
            else:
                errors.add((number, "invalid_trailer"))
        else:
            errors.add((number, "record_type"))
    amount = sum(p.amount_minor for p in good_details)
    digest = sum(int(p.payee_account[-8:]) for p in good_details) % (10 ** 10)
    for number, count, control, hashed in trailers:
        if count != d_seen or d_seen == 0:
            errors.add((number, "count_mismatch"))
        if control != amount:
            errors.add((number, "control_total_mismatch"))
        if hashed != digest:
            errors.add((number, "hash_total_mismatch"))
    if errors:
        return BatchResult(False, [], [BatchError(n, c) for n, c in sorted(errors)])
    return BatchResult(True, good_details, [])
