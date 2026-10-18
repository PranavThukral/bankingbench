# Private draft - refund reviewer notes

v2 starter (see analysis/findings.md F-107): the starter records any refund of a captured payment
with no upper limit, lets a payment be captured repeatedly, runs without an explicit write
transaction and fails with an AttributeError on an unknown payment id. The cumulative cap on captured
funds, capture-once, atomic write transactions and the unknown-id rule are the ticket. The wrong
variants are plausible completions of that starter: `wrong_checks_single_refund` caps each refund at
the captured amount but not the running total; `wrong_uses_authorized` caps the running total at the
authorized amount; `wrong_counts_rejected` caps correctly but adds a rejected attempt to the
refunded counter before raising. The correct counter-based service and the append-only event
alternative share only the public errors and validation.

## Blind review
Author self-review: repeated capture, bool/zero, capture before refund and validation priority
were unspecified in the starter. The ticket now resolves them. Predictions: auth100/capture60/
refund40 then30 -> first accepted, second RefundExceedsCaptured; reject101 then refund100 ->
accepted100; uncaptured refund1 -> PaymentNotCaptured. No unresolved graded ambiguity.
Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
