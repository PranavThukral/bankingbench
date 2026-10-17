# Private draft — reconciliation reviewer notes

Counts alone hide identity reuse. The three realistic candidates respectively reuse an entry,
implement only the common R1 case, or normalize a negative amount too early. Alternative
uses remaining-record maps and indexed references; reference maintains consumed-id sets.

## Blind review
Author self-review on ticket plus starter. Ambiguities: R2 traversal with repeated references,
negative R2 amounts, R3 tie breaks/date window, ordering of result lists. Ticket now states all
of these. Predictions: exact amount at +3 days -> R1; duplicate exact statement -> one R1 and
one duplicate; parts 40+60 against 100 -> one R2 with both ids. No unresolved graded ambiguity.
Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
