# Private draft — fee reviewer notes

Integer numerator rounding is independent of the alternative's Decimal quantization. The
marginal candidate is plausible but predicted to fail even the naive mid-tier examples;
no artificial effort is made to make every wrong implementation pass the naive grader.
Float counterexamples are discovered by tools/find_ties.py, not chosen to fit a test.

## Blind review
Author self-review: upper-bound inclusivity, zero, fixed-fee clamp order and malformed schedules
were ambiguous in the starter; all are explicit in the ticket. Predictions: amount5000/bps3 ->2;
amount10000 uses the first inclusive tier; zero with fixed5/min10 ->10.
No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
