# Private draft - batch parser reviewer notes

v2 starter (see analysis/findings.md F-105): the starter interprets detail records only, splits the
file on LF only, never looks at the header or trailer, and returns the good payments even when other
detail lines were malformed. Header/trailer validation, count, control and hash totals, CRLF handling
and whole-batch rejection are the ticket. The wrong variants are plausible completions of that starter:
`wrong_partial_accept` adds everything but keeps accepting the valid details of a batch with
malformed detail records; `wrong_ignores_hash_total` implements count and control totals only;
`wrong_crlf_slicing` completes the validation but keeps the starter's LF-only line splitting, so CRLF
files fail on the CR byte. The alternative accumulates totals in a single streaming pass.
CR at the end does not shift earlier columns; the defect is validating/slicing before line-ending
normalization. Fixtures generate CRLF from bytes.

## Blind review
Author self-review: positions, terminators, malformed-field error granularity, cascading trailer
checks, ordering and line numbers all needed explicit rules. The ticket now contains them.
Predictions: account000000000123 contributes123 to hash; count mismatch -> rejected/no payments;
valid CRLF -> accepted/same records as LF. No unresolved graded ambiguity. Independent review owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
