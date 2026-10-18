# Ticket: reconcile a synthetic statement to ledger entries

Keep `recon.engine.reconcile(statement: list[StatementLine], ledger: list[LedgerEntry]) -> ReconResult`.
Public frozen dataclasses (also exported from recon.engine):
- `StatementLine(id: str, value_date: date, amount_minor: int, reference: str)`
- `LedgerEntry(id: str, booking_date: date, amount_minor: int, reference: str,
  kind: "payment"|"refund" = "payment", original_reference: str|None = None)`
- `Match(statement_ids: frozenset[str], ledger_ids: frozenset[str], rule: str)`
- `ReconResult(matches: list[Match], unmatched_statement: dict[str,str], unmatched_ledger: set[str])`

All amounts are integer minor units in one synthetic currency (CAD, 2 dp); statement amounts
are signed, ledger payment/refund amounts positive. Dates are calendar dates. IDs are unique
within each input, strings sort lexicographically. Inputs are valid and must not be mutated.
Apply complete passes in the following order; each id can appear in at most one match:

1. R1: process statements by `(value_date,id)`. Match an unmatched ledger **payment** with equal
   reference and equal signed amount, date difference <=3 calendar days. Choose smallest absolute
   date difference, then earliest booking_date, then smallest id.
2. R2: process remaining ledger payments by `(reference,booking_date,id)`. For each payment,
   collect **all** unmatched statement lines of the same reference within +/-3 days of that payment.
   If at least two lines and their signed sum equals its amount, match the whole group. Do not
   search subsets. Negative lines, if present, contribute their signed amount to this pass.
3. R3: process remaining negative statements by `(value_date,id)`. Match an unmatched ledger
   **refund**, with original_reference equal to the statement reference and positive amount equal
   to abs(statement amount). There is no date restriction in R3. Choose earliest booking_date,
   then smallest id. The refund's own reference need not equal the original reference.
4. R4: each remaining statement identical in `(value_date,amount_minor,reference)` to any matched
   statement gets reason `duplicate`; otherwise `no_match`. Unused ledger ids form unmatched_ledger.

Worked example (CAD minor units; every reference is a synthetic invoice id):

| Statement id | value_date | amount | reference |  | Ledger id | booking_date | amount | reference |
|---|---|---:|---|---|---|---|---:|---|
| s1 | 2026-01-05 | 10000 | INV-1 |  | l1 | 2026-01-03 | 10000 | INV-1 |
| s2 | 2026-01-06 | 4000 | INV-2 |  | l2 | 2026-01-06 | 10000 | INV-2 |
| s3 | 2026-01-07 | 6000 | INV-2 |  |  |  |  |  |

`s1` matches `l1` by R1 (two days apart, inside the window). `s2` and `s3` are the only unmatched
lines for `INV-2` inside the window of `l2` and sum to 10000, so R2 matches both to `l2`.
Nothing is left unmatched.

Use rule strings `R1`, `R2`, `R3`. Match-list order is not graded. Exact membership, reasons,
partitions and no reuse are graded. Empty inputs produce empty collections.
Run from starter: `python -m pytest tests -q`.
