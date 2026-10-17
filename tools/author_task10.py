from author_common import task_meta, write

b = task_meta("10_batch_parser", "Validate an entire SBF-80 payment batch", "batch", [
    "batch.parser:parse, BatchResult, Payment, BatchError"], [
    ("wrong_partial_accept", "Accepts valid details from a batch containing invalid detail records.", ["test_atomic_batch_rejection"]),
    ("wrong_ignores_hash_total", "Does not check the trailer account hash total.", ["test_hash_total"]),
    ("wrong_crlf_slicing", "Validates physical line width before normalizing CRLF.", ["test_crlf"]),
], "Streaming record accumulation and incremental totals versus a two-pass validation and control phase.", terms=["reward.txt"])
write(b / "PROBLEM.md", '''
# Ticket: validate invented SBF-80 batch files atomically

`batch.parser.parse(data:bytes)->BatchResult` returns frozen dataclasses exported from that module:
`Payment(payee_account:str,amount_minor:int,reference:str)`, `BatchError(line_no:int,code:str)`,
`BatchResult(accepted:bool,payments:list[Payment],errors:list[BatchError])`.

SBF-80 is invented for this synthetic task. Each record is exactly 80 printable ASCII characters,
followed by LF or CRLF. A final terminator is optional; mixed LF/CRLF is accepted. Strip the
terminator before checking width and slicing. Interior blank lines are records and invalid.
Bare CR, non-ASCII or control bytes are invalid_encoding. All positions below are 1-based inclusive.

| Record | Columns | Field |
|---|---|---|
| H | 1 | H |
| H | 2–13 | batch id: 12 uppercase ASCII letters/digits |
| H | 14–21 | creation date YYYYMMDD, valid calendar date |
| H | 22–24 | currency CAD, USD, EUR, GBP, JPY, KWD or BHD |
| H | 25–80 | spaces |
| D | 1 | D |
| D | 2–13 | 12 ASCII digits, payee account (retain leading zeros) |
| D | 14–25 | 12 ASCII digits, positive zero-padded integer minor units |
| D | 26–45 | 20 printable chars, nonblank reference, right-space padded |
| D | 46–80 | spaces |
| T | 1 | T |
| T | 2–7 | detail count, 6 ASCII digits |
| T | 8–22 | control total of amounts, 15 ASCII digits |
| T | 23–32 | hash total, 10 ASCII digits |
| T | 33–80 | spaces |

Exactly one header first, then one or more details, then exactly one trailer last. The count is
the number of D records, including malformed D records. Control total and hash total use only
fully valid detail records. Hash = sum(int(last 8 digits of each payee account)) mod 10**10.
Money is in header-currency minor units: CAD/USD/EUR/GBP=2 dp, JPY=0, KWD/BHD=3. Do not convert.
Returned references remove right padding only. Preserve detail order and account strings.

Any error rejects the whole batch: accepted=False and payments=[]. Report all detectable errors,
deduplicated by (line_no,code), sorted by line_no then code. Continue checking other records.
For a wrong-width or invalid-encoding record, report only that local error (no field errors),
but structural/order and trailer comparisons can still be reported. Field errors are one code per
record even if multiple fields are invalid. Trailer totals compare independently when its fields
are valid, even if other records failed.

Codes: invalid_encoding, line_length, record_type, record_order, invalid_header, invalid_detail,
invalid_trailer, count_mismatch, control_total_mismatch, hash_total_mismatch, missing_header,
missing_trailer. H outside first position, T outside last, or D at first/last -> record_order.
Unknown type -> record_type. A missing first H -> missing_header at line1; missing final T ->
missing_trailer at the last line (line1 for empty input). An empty detail section -> count_mismatch
on the trailer. Header/trailer field errors include invalid reserved spaces. No other codes.

Run from starter: `python -m pytest tests -q`. No real batch format, institution or customer is used.
''')
write(b / "starter/batch/models.py", '''
"""Public SBF-80 transport records."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Payment:
    payee_account: str
    amount_minor: int
    reference: str

    def as_dict(self):
        return {"payee_account": self.payee_account, "amount_minor": self.amount_minor, "reference": self.reference}


@dataclass(frozen=True)
class BatchError:
    line_no: int
    code: str

    def as_dict(self):
        return {"line_no": self.line_no, "code": self.code}


@dataclass(frozen=True)
class BatchResult:
    accepted: bool
    payments: list[Payment]
    errors: list[BatchError]

    def as_dict(self):
        return {"accepted": self.accepted, "payments": [p.as_dict() for p in self.payments],
                "errors": [e.as_dict() for e in self.errors]}
''')
write(b / "starter/batch/records.py", '''
"""Fixed-width record decoding shared by offline batch utilities."""
from datetime import datetime
import re
from batch.models import Payment

CURRENCIES = {"CAD", "USD", "EUR", "GBP", "JPY", "KWD", "BHD"}


def digits(text):
    return bool(text) and all("0" <= char <= "9" for char in text)


def decode(raw):
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return None, "invalid_encoding"
    if any(ord(c) < 32 or ord(c) > 126 for c in text):
        return None, "invalid_encoding"
    if len(text) != 80:
        return None, "line_length"
    return text, None


def fields(text):
    kind = text[0]
    if kind == "H":
        valid = bool(re.fullmatch(r"[A-Z0-9]{12}", text[1:13]))
        try:
            datetime.strptime(text[13:21], "%Y%m%d")
            valid = valid and digits(text[13:21])
        except ValueError:
            valid = False
        valid = valid and text[21:24] in CURRENCIES and text[24:] == " " * 56
        return None, None if valid else "invalid_header"
    if kind == "D":
        valid = digits(text[1:13]) and digits(text[13:25]) and text[45:] == " " * 35
        if not valid or int(text[13:25]) <= 0 or not text[25:45].strip():
            return None, "invalid_detail"
        return Payment(text[1:13], int(text[13:25]), text[25:45].rstrip(" ")), None
    if kind == "T":
        if not (digits(text[1:7]) and digits(text[7:22]) and digits(text[22:32]) and text[32:] == " " * 48):
            return None, "invalid_trailer"
        return (int(text[1:7]), int(text[7:22]), int(text[22:32])), None
    return None, "record_type"


def physical_lines(data):
    if not data:
        return []
    rows = data.split(b"\\n")
    if rows[-1] == b"":
        rows.pop()
    return [row[:-1] if row.endswith(b"\\r") and (i < len(rows) - 1 or data.endswith(b"\\n")) else row
            for i, row in enumerate(rows)]
''')
reference = '''
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
    return BatchResult(not errors, [] if errors else payments, [BatchError(*e) for e in sorted(errors)])
'''
write(b / "solutions/reference/batch/parser.py", reference)
write(b / "starter/batch/parser.py", reference.replace('if count == 0 or count != declared_count:', 'if count == 0:'))
write(b / "solutions/wrong_partial_accept/batch/parser.py", reference.replace(
    '    return BatchResult(not errors,',
    '    if payments and any(code == "invalid_detail" for _, code in errors):\n        return BatchResult(True, payments, [BatchError(*e) for e in sorted(errors)])\n    return BatchResult(not errors,'))
write(b / "solutions/wrong_ignores_hash_total/batch/parser.py", reference.replace('''        if hash_total != sum(int(p.payee_account[-8:]) for p in payments) % 10**10:
            errors.add((line_no, "hash_total_mismatch"))
''', ''))
write(b / "solutions/wrong_crlf_slicing/batch/parser.py", reference.replace('rows = physical_lines(data)',
    'rows = data.split(b"\\n")\n    if rows and rows[-1] == b"":\n        rows.pop()').replace('decode, fields, physical_lines', 'decode, fields').replace(
    '        text, local_error = decode(raw)', '        if len(raw) != 80:\n            errors.add((line_no, "line_length"))\n            continue\n        text, local_error = decode(raw)'))
write(b / "solutions/alt_valid/batch/parser.py", '''
from batch.models import BatchResult, Payment, BatchError  # noqa: F401
from batch.records import fields, decode, physical_lines


def parse(data):
    physical = physical_lines(data)
    issues = set()
    details = []
    number_of_details, amount_sum, account_sum = 0, 0, 0
    controls = []
    last_index = len(physical)
    if not physical or not physical[0].startswith(b"H"):
        issues.add((1, "missing_header"))
    if not physical or not physical[-1].startswith(b"T"):
        issues.add((max(last_index, 1), "missing_trailer"))
    for index, physical_record in enumerate(physical, start=1):
        marker = physical_record[:1]
        if marker == b"D":
            number_of_details += 1
        expected_position = {b"H": index == 1, b"T": index == last_index,
                             b"D": 1 < index < last_index}
        if marker in expected_position and not expected_position[marker]:
            issues.add((index, "record_order"))
        record, issue = decode(physical_record)
        if issue is None:
            value, issue = fields(record)
            if issue is None and marker == b"D":
                details.append(value)
                amount_sum += value.amount_minor
                account_sum = (account_sum + int(value.payee_account[-8:])) % 10**10
            elif issue is None and marker == b"T":
                controls.append((index, value))
        if issue:
            issues.add((index, issue))
    for index, declared in controls:
        observed = number_of_details, amount_sum, account_sum
        codes = "count_mismatch", "control_total_mismatch", "hash_total_mismatch"
        for i, code in enumerate(codes):
            if declared[i] != observed[i] or (i == 0 and number_of_details == 0):
                issues.add((index, code))
    ordered_errors = [BatchError(line, code) for line, code in sorted(issues)]
    if ordered_errors:
        return BatchResult(False, [], ordered_errors)
    return BatchResult(True, details, [])
''')
write(b / "starter/batch/render.py", '''
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
    separator = b"\\r\\n" if crlf else b"\\n"
    return separator.join(row.encode("ascii") for row in rows) + separator
''')
write(b / "starter/tests/test_visible.py", '''
from batch.parser import parse, Payment
from batch.render import render


def fixture():
    return render([Payment("000000000123", 100, "reference")], batch_id="SYNTHETIC001")


def test_valid_lf():
    result = parse(fixture())
    assert result.accepted
    assert result.payments == [Payment("000000000123", 100, "reference")]
    assert result.errors == []


def test_count_mismatch():
    lines = fixture().splitlines()
    lines[-1] = b"T000002" + lines[-1][7:]
    result = parse(b"\\n".join(lines) + b"\\n")
    assert not result.accepted
    assert result.payments == []
    assert any(error.code == "count_mismatch" for error in result.errors)
''')
write(b / "grader/naive/test_hidden.py", (b / "starter/tests/test_visible.py").read_text(encoding="utf-8"))
write(b / "NOTES.md", '''
# Private draft — batch parser reviewer notes

Both valid parsers share field decoding but differ in accumulation and control-flow design.
The CRLF candidate checks the physical line's 81-character length before removing CR. CR at
the end does not shift earlier columns; the actual defect is validating/slicing before line-ending
normalization, not a claim that CR shifts the first field. Fixtures generate CRLF from bytes.

## Blind review
Author self-review: positions, terminators, malformed-field error granularity, cascading trailer
checks, ordering and line numbers all needed explicit rules. The ticket now contains them.
Predictions: account000000000123 contributes123 to hash; count mismatch -> rejected/no payments;
valid CRLF -> accepted/same records as LF. No unresolved graded ambiguity. Independent review owed.
''')
