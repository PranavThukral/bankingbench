# Private draft — task 01 reviewer notes

The reservation implementation returns 409 during a charge; the advisory-lock implementation waits.
Both are valid under the public contract. Wrong variants isolate a realistic persistence,
decline-replay, or check-then-write defect; none change visible tests.

v2 note (see analysis/findings.md F-108): the starter now also lacks the request fingerprint and the
Idempotency-Key length validation (they moved into the reference), raising `ref_diff_lines` from 33 to 41.

## v3 wrong-variant replacement

After review, `wrong_uncached_decline` replaces the regressive `wrong_key_scope`.
It extends the starter's PaymentStore with persistent, merchant-scoped successful-response replay
under a transaction lock, but treats a declined charge as retryable and never reserves its key.
The existing `test_decline_replayed` catches the extra gateway call; the starter also fails it.
See analysis/findings.md F-301 for predictions and measured evidence; no regression rationale is needed.

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
v2 re-measurement (starter changed, so the 20-repeat check was re-run; commit ce7d671, clean tree):
60 final runs (20 per variant), 0 flips, all 60 verdicts ok. Wall time 149.441 s.
Per-run duration_s in repeat order:

- reference: 13.02, 12.577, 12.788, 12.738, 12.861, 12.731, 12.8, 12.917, 12.473, 12.479, 12.751, 12.489, 12.737, 12.733, 12.883, 12.804, 12.75, 12.489, 12.681, 12.685
- alt_valid: 11.321, 11.304, 11.212, 11.318, 11.523, 11.385, 11.76, 11.727, 11.295, 11.281, 11.534, 11.466, 11.753, 11.659, 11.828, 11.745, 12.634, 12.548, 12.544, 12.524
- wrong_retry_race: 5.362, 5.279, 5.119, 5.252, 4.921, 4.841, 4.741, 4.735, 4.979, 4.991, 5.289, 5.103, 5.531, 5.53, 5.556, 5.549, 5.558, 5.549, 5.345, 5.349

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
