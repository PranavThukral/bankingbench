# Private draft - fee reviewer notes

v2 starter (see analysis/findings.md F-104): `compute_fee` prices every amount with the first tier's
rate using truncating integer division and no clamp, no amount validation and no schedule validation.
Tier selection, half-up rounding, the clamp and the validation are the ticket. The wrong variants are
plausible completions of that starter: `wrong_exclusive_boundary` selects tiers with `<`,
`wrong_float_bps` rounds half up using a float percentage, `wrong_marginal` prices bands separately.
Integer numerator rounding is independent of the alternative's Decimal quantization. Float
counterexamples are discovered by tools/find_ties.py, not chosen to fit a test.

## Blind review
Author self-review: upper-bound inclusivity, zero, fixed-fee clamp order and malformed schedules
were ambiguous in the starter; all are explicit in the ticket. Predictions: amount5000/bps3 ->2;
amount10000 uses the first inclusive tier; zero with fixed5/min10 ->10.
No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
