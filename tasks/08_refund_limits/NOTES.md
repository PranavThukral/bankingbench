# Private draft — refund reviewer notes

The correct counter-based service and append-only event alternative share only the public errors
and validation. Wrong candidates isolate a per-request check, the wrong amount basis, or counting
rejected attempts. The last bug is over-strict, so the grader checks successful recovery too.

## Blind review
Author self-review: repeated capture, bool/zero, capture before refund and validation priority
were unspecified in the starter. The ticket now resolves them. Predictions: auth100/capture60/
refund40 then30 -> first accepted, second RefundExceedsCaptured; reject101 then refund100 ->
accepted100; uncaptured refund1 -> PaymentNotCaptured. No unresolved graded ambiguity.
Independent review remains owed.
