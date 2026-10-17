from batch.models import BatchResult, Payment, BatchError  # noqa: F401
from batch.records import decode, fields, physical_lines


def parse(data):
    rows = physical_lines(data)
    errors, payments, trailers = set(), [], []
    if not rows or rows[0][:1] != b"H":
        errors.add((1, "missing_header"))
    if not rows or rows[-1][:1] != b"T":
        errors.add((max(1, len(rows)), "missing_trailer"))
    count = sum(row[:1] == b"D" for row in rows)
    for line_no, raw in enumerate(rows, 1):
        kind = raw[:1]
        if ((kind == b"H" and line_no != 1) or (kind == b"T" and line_no != len(rows))
                or (kind == b"D" and line_no in {1, len(rows)})):
            errors.add((line_no, "record_order"))
        text, local_error = decode(raw)
        if local_error:
            errors.add((line_no, local_error))
            continue
        value, field_error = fields(text)
        if field_error:
            errors.add((line_no, field_error))
        elif text[0] == "D":
            payments.append(value)
        elif text[0] == "T":
            trailers.append((line_no, value))
    for line_no, (declared_count, total, hash_total) in trailers:
        if count == 0 or count != declared_count:
            errors.add((line_no, "count_mismatch"))
        if total != sum(p.amount_minor for p in payments):
            errors.add((line_no, "control_total_mismatch"))
        if hash_total != sum(int(p.payee_account[-8:]) for p in payments) % 10**10:
            errors.add((line_no, "hash_total_mismatch"))
    if payments and any(code == "invalid_detail" for _, code in errors):
        return BatchResult(True, payments, [BatchError(*e) for e in sorted(errors)])
    return BatchResult(not errors, [] if errors else payments, [BatchError(*e) for e in sorted(errors)])
