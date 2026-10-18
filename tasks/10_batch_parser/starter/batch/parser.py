from batch.models import BatchResult, Payment, BatchError  # noqa: F401
from batch.records import decode, fields, physical_lines


def parse(data):
    errors, payments = [], []
    for line_no, raw in enumerate(physical_lines(data), 1):
        if raw[:1] != b"D":
            continue
        text, error = decode(raw)
        if error is None:
            value, error = fields(text)
        if error:
            errors.append(BatchError(line_no, error))
        else:
            payments.append(value)
    return BatchResult(not errors, payments, errors)
