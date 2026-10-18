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

Worked example (each record is padded with spaces to 80 characters; trailing spaces are not shown):

```text
HSYNTHBATCH0120260115CAD
D000000012345000000010000INV-2026-001
D000000067890000000002550INV-2026-002
T0000020000000000125500000080235
```

The batch is accepted with two payments: `Payment("000000012345", 10000, "INV-2026-001")` and
`Payment("000000067890", 2550, "INV-2026-002")`. Count 2; control total 10000 + 2550 = 12550; hash total
12345 + 67890 = 80235. Changing the trailer count to `000003` rejects the whole batch with
`BatchError(4, "count_mismatch")` and `payments == []`.

Run from starter: `python -m pytest tests -q`. No real batch format, institution or customer is used.
