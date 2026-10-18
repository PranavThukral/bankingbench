# Private draft — interest reviewer notes

Reference accumulates daily in Decimal (34 digits), multiplying the simple segment in one
expression to preserve exact ties. Alternative uses closed-form Fraction compounding by segment.
The floating candidate is financially plausible and converts results back to Decimal; type
checking alone cannot reject it. Daily rounding is another common premature-normalization error.

## Regression rationale

`wrong_round_daily` is regressive by `check_realism`: the float starter passes its declared must_fail test `test_small_balance_daily_accrues`. Rationale: The float starter never rounds before posting, so it passes test_small_balance_daily_accrues; the Decimal rewrite that the ticket requires invites quantizing each day's accrual to cents to keep every money value at two decimals, which makes small balances accrue nothing.

## Blind review
Author self-review using only ticket and starter; independent review remains owed.
Ambiguities: negative rates/principal, initial cents, datetime vs date, rounding residuals, empty
periods. Resolved explicitly in PROBLEM.md.
Predictions: 50 CAD at 0.0365 for one day -> 0.00 interest; zero days -> []; 1000 CAD at 0.0365
for ten simple days -> 1.00 interest and 1001.00 balance. No unresolved graded ambiguity.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
