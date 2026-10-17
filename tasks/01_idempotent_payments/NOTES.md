# Private draft — task 01 reviewer notes

The reservation implementation returns 409 during a charge; the advisory-lock implementation waits.
Both are valid under the public contract. Wrong variants isolate a realistic persistence,
namespace, or check-then-write defect; none change visible tests.

## Blind review
Author self-review, restricted to the ticket and starter (independent review still owed).
Ambiguities found: JSON equality vs member order, key length errors, merchant validation, receipt
fields, and failures during gateway calls. Resolved in PROBLEM.md: validated-field equality,
explicit status codes, free message text, and crash recovery excluded.
Three withheld-output predictions: missing key -> 400/idempotency_key_required; same key on
another merchant -> distinct 201 payment; completed decline retry -> identical 402 without charge.
No unresolved graded ambiguity after the ticket revision. This is not an independent model review.
