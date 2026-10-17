# Private draft — journal reviewer notes

Rowwise reference validation occurs within one transaction. The independent valid alternative
checks a JSON recordset using SQL aggregation and reverses by INSERT SELECT. Three wrong
implementations isolate cross-currency netting, per-line commit, and missing reversal lifecycle checks.

## Blind review
Author self-review from ticket and starter. Ambiguities: trial_balance key/value meaning,
invalid side/count errors, re-created accounts, unknown transaction errors, and reversal turnover.
All are specified in PROBLEM.md. Predictions: CAD debit100/USD credit100 -> UnbalancedTransaction;
unknown third account -> UnknownAccount with unchanged balances; reverse a reversal ->
CannotReverseReversal, no change. No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
