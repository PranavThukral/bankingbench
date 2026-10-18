# Private draft — task 01 reviewer notes

The reservation implementation returns 409 during a charge; the advisory-lock implementation waits.
Both are valid under the public contract. Wrong variants isolate a realistic persistence,
namespace, or check-then-write defect; none change visible tests.

v2 note (see analysis/findings.md F-108): the starter now also lacks the request fingerprint and the
Idempotency-Key length validation (they moved into the reference), raising `ref_diff_lines` from 33 to 41.

## Regression rationale

`wrong_key_scope` is regressive by `check_realism`: the starter has no idempotency keys, so it passes
`test_same_key_different_merchants_independent` trivially. Rationale: The starter has no idempotency keys at all, so it is trivially merchant-independent; the natural first implementation uses the client-supplied key as the unique key, and scoping it by merchant is the extra step a hurried solver skips.

## Blind review
Author self-review, restricted to the ticket and starter (independent review still owed).
Ambiguities found: JSON equality vs member order, key length errors, merchant validation, receipt
fields, and failures during gateway calls. Resolved in PROBLEM.md: validated-field equality,
explicit status codes, free message text, and crash recovery excluded.
Three withheld-output predictions: missing key -> 400/idempotency_key_required; same key on
another merchant -> distinct 201 payment; completed decline retry -> identical 402 without charge.
No unresolved graded ambiguity after the ticket revision. This is not an independent model review.

## Flake measurement

Native Windows / PostgreSQL 16.13, 10 simultaneous callers, 150 ms gateway delay, 25 fresh-key rounds per test.
60 final runs (20 per variant), 0 flips, all 60 verdicts ok. Wall time 152.592 s.
Per-run duration_s in repeat order:

- reference: 13.375, 13.363, 13.355, 13.313, 13.524, 14.034, 13.765, 14.007, 11.629, 11.373, 11.759, 11.776, 11.744, 11.724, 11.488, 11.506, 12.831, 12.77, 12.835, 12.823
- alt_valid: 11.155, 11.127, 11.534, 11.224, 14.209, 14.117, 14.372, 14.435, 12.004, 12.011, 11.959, 11.839, 12.051, 12.04, 11.933, 11.789, 11.98, 11.981, 11.814, 11.943
- wrong_retry_race: 5.157, 5.154, 4.952, 5.034, 5.528, 5.445, 5.332, 5.258, 6.434, 6.477, 6.408, 6.477, 5.253, 5.25, 5.245, 5.04, 5.335, 5.19, 5.27, 5.21

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
