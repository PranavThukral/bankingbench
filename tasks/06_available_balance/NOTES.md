# Private draft - holds reviewer notes

v2 starter (see analysis/findings.md F-103): authorizations are recorded and approved against posted
funds plus overdraft, and `available_minor` always equals `posted_minor`; there is no holds model, no
capture or void endpoint and no expiry. The wrong variants are plausible completions of that starter:
`wrong_available_ignores_holds` adds capture, void and expiry but keeps the starter's availability;
`wrong_partial_capture_keeps_remainder` adds holds but leaves the unused part of a partially captured
hold active; `wrong_expired_holds_count` adds holds and rejects expired capture/void but still counts
expired active records against availability. The alternative retires expired records at transaction
entry and recomputes availability from the remaining active records.

## Blind review
Author self-review clarified account seeding, exact expiry instant, partial-capture response,
closed/overcapture error priority, persistence and amount validation in the ticket.
Predictions: reserve1000/capture400 ->posted9600/available9600; at7days hold stops counting;
flex15000 authorized then1 declined. No unresolved graded ambiguity. Independent review owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
