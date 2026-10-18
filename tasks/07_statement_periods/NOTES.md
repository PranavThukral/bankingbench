# Private draft - period reviewer notes

v2 starter (see analysis/findings.md F-106): the starter derives every account's month from UTC
(`account_tz` is ignored), sorts equal instants by input order only and has no time-zone, month or
year validation. Time-zone months, the id tie-break and the validation are the ticket. The wrong
variants are plausible completions of that starter: `wrong_utc_month` adds the validation and
tie-break but keeps UTC month boundaries; `wrong_inclusive_2359` uses the zone but ends the period
one second before local midnight; `wrong_fixed_offset` uses the zone's standard-time offset all year.
The alternative tests local calendar membership for each timestamp, so a grader requiring the
selector to call period_bounds would be invalid.

## Regression rationale

`wrong_inclusive_2359` is regressive by `check_realism` (the v2 starter passes its declared must_fail test `test_microsecond_boundary`, because the UTC starter already uses an exclusive next-month end). Rationale: The UTC starter already ends the period at the exclusive start of the next month, so test_microsecond_boundary passes on it; moving the period to local time invites rewriting the end as the last second of the local month (23:59:59), the way monthly statements are usually described in prose, which drops the final fractional second.

## Blind review
Author self-review: ordering of equal instants, microsecond precision, invalid timestamps outside
the window and year limits clarified in the ticket. Predictions: Toronto March 2026 starts05:00Z
and ends04:00Z; at end exactly -> excluded; last microsecond before end -> included.
No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
