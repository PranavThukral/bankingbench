# Ticket: accrue interest across partial calendar months

The synthetic CAD account needs correct daily accrual and explicit posting boundaries.
Keep `interest.accrual.accrue(principal: Decimal, annual_rate: Decimal, start: date, end: date,
method: Literal["simple_monthly","daily_compound"]) -> list[Posting]` and
`Posting(posting_date: date, interest: Decimal, balance: Decimal)` (frozen dataclass).

CAD has 2 decimal places. Principal is a nonnegative finite Decimal in whole cents; rate is
a nonnegative finite Decimal (a fraction, e.g. 0.05 means 5%). Invalid values/method or end before
start raise ValueError. These are dates, not timestamps; any datetime instead of date is invalid.

- Day count is Actual/365 Fixed, including leap years. Accrue for every date in `[start,end)`.
- Post on each month end within that period, and also on `end - 1 day` if it is not a month end.
  Return chronological postings. `start == end` returns `[]`.
- `simple_monthly`: interest at a posting equals current posted balance × rate × segment days / 365.
  Add each posting to the balance; thus it compounds at posting boundaries.
- `daily_compound`: each date, accrued += (posted balance + accrued) × rate / 365 with full
  intermediate precision. At posting, round accrued, add to balance, reset accrued to zero;
  discard the unrounded residual.
- Round only the posting to 0.01 using ROUND_HALF_EVEN. Intermediate arithmetic must use
  precision at least 28 or exact arithmetic. Both money fields must be Decimal with exponent -2,
  even when zero. Return the resulting balance after each posting.

Worked example: principal 1000.00, rate 0.0365 (so 0.0001 per day), start 2026-01-01, end 2026-03-01.
Both methods post on 2026-01-31 (31 days) and 2026-02-28 (28 days). January: 1000.00 x 0.0365 x 31 / 365 =
3.10, balance 1003.10. February: 1003.10 x 0.0365 x 28 / 365 = 2.8087..., posted as 2.81, balance 1005.91.
(With `daily_compound` the unrounded January interest is 3.1048...; both methods round to the same cents here.)

Only the declared interface is graded; internal representation and algorithms are unrestricted.
Run from starter: `python -m pytest tests -q`. All examples and accounts are synthetic.
