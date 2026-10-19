# Private draft - period reviewer notes

v2 starter (see analysis/findings.md F-106): the starter derives every account's month from UTC
(`account_tz` is ignored), sorts equal instants by input order only and has no time-zone, month or
year validation. Time-zone months, the id tie-break and the validation are the ticket. The wrong
variants are plausible completions of that starter: `wrong_utc_month` adds the validation and
tie-break but keeps UTC month boundaries; `wrong_offset_sign` adds each endpoint's offset when
converting local wall time to UTC; `wrong_fixed_offset` uses the zone's standard-time offset all year.
The alternative tests local calendar membership for each timestamp, so a grader requiring the
selector to call period_bounds would be invalid.

## v3 wrong-variant replacement

After review, `wrong_offset_sign` replaces the regressive `wrong_inclusive_2359`.
It extends the starter's month bounds with independent endpoint offsets, validation and id ordering,
but translates the offsets in the wrong direction. UTC bounds, exclusive microseconds and adjacent
month partitioning are preserved; existing non-UTC boundary and DST tests catch it, and the starter
also fails them. See analysis/findings.md F-301 for predictions and measured evidence;
no regression rationale is needed.

## Blind review
Author self-review: ordering of equal instants, microsecond precision, invalid timestamps outside
the window and year limits clarified in the ticket. Predictions: Toronto March 2026 starts05:00Z
and ends04:00Z; at end exactly -> excluded; last microsecond before end -> included.
No unresolved graded ambiguity. Independent review remains owed.

Self-review confirmation (2026-10-17): re-read only PROBLEM.md and starter files from disk; the three predictions above follow from the ticket. No additional graded ambiguity found. Independent review remains owed.
