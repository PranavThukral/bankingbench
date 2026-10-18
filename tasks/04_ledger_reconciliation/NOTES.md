# Private draft — reconciliation reviewer notes

Counts alone hide identity reuse. v2 starter (see analysis/findings.md F-0xx v2 redesign): the
starter implements R1 only, with a same-day window, no ledger consumption and a flat `no_match`
reason; the window, consumption, R2 split, R3 refund and R4 duplicate classification are the
ticket. The wrong variants are plausible completions of that starter: `wrong_no_consumption`
adds the window, R2, R3 and R4 but keeps the starter's non-consuming candidate lookup;
`wrong_split_ignored` adds everything except R2; `wrong_refund_abs` compares absolute amounts in
the exact rule. The alternative uses remaining-record maps and indexed references; the reference
extends the starter's candidate helpers and tracks consumed ids.

## Blind review
Author self-review on ticket plus starter. Ambiguities: R2 traversal with repeated references,
negative R2 amounts, R3 tie breaks/date window, ordering of result lists. Ticket now states all
of these. Predictions: exact amount at +3 days -> R1; duplicate exact statement -> one R1 and
one duplicate; parts 40+60 against 100 -> one R2 with both ids. No unresolved graded ambiguity.
Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
