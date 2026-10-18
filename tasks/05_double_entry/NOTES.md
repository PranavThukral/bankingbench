# Private draft - journal reviewer notes

v2 starter (see analysis/findings.md F-102): the starter posts lines on an autocommit connection
with no balance validation, no transaction wrapper and no reversal (no `reverse` method, no
reversal columns). Per-currency balance validation, atomic posting and the reversal lifecycle are
the ticket. The wrong variants are plausible completions of that starter: `wrong_cross_currency_sum`
validates balance but sums one grand total; `wrong_non_atomic` adds validation and reversal but keeps
the starter's autocommit connection and validates while inserting; `wrong_double_reverse` adds
reversal without the once-only check. The independent valid alternative checks a JSON recordset
using SQL aggregation and reverses by INSERT SELECT; it ignores the starter's schema module.

## Blind review
Author self-review from ticket and starter. Ambiguities: trial_balance key/value meaning,
invalid side/count errors, re-created accounts, unknown transaction errors, and reversal turnover.
All are specified in PROBLEM.md. Predictions: CAD debit100/USD credit100 -> UnbalancedTransaction;
unknown third account -> UnknownAccount with unchanged balances; reverse a reversal ->
CannotReverseReversal, no change. No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
