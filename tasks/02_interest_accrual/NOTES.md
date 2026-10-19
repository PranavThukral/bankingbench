# Private draft — interest reviewer notes

Reference accumulates daily in Decimal (34 digits), multiplying the simple segment in one
expression to preserve exact ties. Alternative uses closed-form Fraction compounding by segment.
The floating candidate is financially plausible and converts results back to Decimal; type
checking alone cannot reject it. Actual/Actual is a plausible but incorrect day-count convention here.

## v3 wrong-variant replacement

After review, `wrong_actual_actual` replaces the regressive `wrong_round_daily`.
It completes the starter using its calendar segments and Decimal arithmetic, but divides by 366
in leap years rather than using Actual/365 Fixed. Existing leap-year, large-principal and property
tests catch it, and the starter also fails those tests. See analysis/findings.md F-301 for predictions
and measured evidence; no regression rationale is needed.

## Blind review
Author self-review using only ticket and starter; independent review remains owed.
Ambiguities: negative rates/principal, initial cents, datetime vs date, rounding residuals, empty
periods. Resolved explicitly in PROBLEM.md.
Predictions: 50 CAD at 0.0365 for one day -> 0.00 interest; zero days -> []; 1000 CAD at 0.0365
for ten simple days -> 1.00 interest and 1001.00 balance. No unresolved graded ambiguity.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
