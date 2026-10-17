# Private draft — batch parser reviewer notes

Both valid parsers share field decoding but differ in accumulation and control-flow design.
The CRLF candidate checks the physical line's 81-character length before removing CR. CR at
the end does not shift earlier columns; the actual defect is validating/slicing before line-ending
normalization, not a claim that CR shifts the first field. Fixtures generate CRLF from bytes.

## Blind review
Author self-review: positions, terminators, malformed-field error granularity, cascading trailer
checks, ordering and line numbers all needed explicit rules. The ticket now contains them.
Predictions: account000000000123 contributes123 to hash; count mismatch -> rejected/no payments;
valid CRLF -> accepted/same records as LF. No unresolved graded ambiguity. Independent review owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
