# Private draft - FX reviewer notes

v2 starter (see analysis/findings.md F-110): the starter quotes direct pairs only, assumes two decimal
places for every currency, computes the fee but does not deduct it before conversion and has no cross
route through USD. Per-currency minor units, the cross rate at full precision, fee-before-conversion and
the precision rules are the ticket. The wrong variants are plausible completions of that starter:
`wrong_two_decimals` adds the cross route and fee deduction but keeps the starter's universal scale;
`wrong_round_cross_leg` rounds the USD leg of a cross quote to cents; `wrong_fee_after_conversion`
converts the gross amount and subtracts a destination-side fee. The exact rational alternative verifies
that the Decimal implementation does not define the answer by itself. Ordinary two-decimal direct
quotes can mask all three errors.

## Blind review
Author self-review: fee denomination, direct-rate precedence, unsupported currencies, inverse
rates, zero amount and acceptable fee range clarified in PROBLEM.md.
Predictions: JPY100 -> USD at0.01 ->100 cents; CAD3 at0.5 with5000bps ->fee2/converted0;
cross CAD1 via0.5 USD and1.5 EUR ->1 EUR cent. No unresolved graded ambiguity.
Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
