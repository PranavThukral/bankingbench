# Ticket: monthly statements follow the account timezone

`statements.period.period_bounds(account_tz:str,year:int,month:int)->tuple[datetime,datetime]`
returns aware UTC instants for a half-open interval. `select(txns:list[Txn],account_tz,year,month)`
returns transaction ids sorted by instant, then lexicographic id. Frozen `Txn(id:str,at:datetime)`
is public. IDs are unique and timestamps may have arbitrary aware offsets and microseconds.

The period is the calendar month in the account's IANA timezone: local 00:00 on day 1 inclusive
through local 00:00 on day 1 of the next month exclusive, converted to UTC using zoneinfo.
An unknown time zone name, a non-int (or bool) year or month, a month outside 1-12 or a year outside
1900-2098 raises ValueError from both functions. Daylight saving rules apply independently to both
endpoints. Each input timestamp must be aware with a non-None utcoffset,
otherwise select raises ValueError, even when that transaction would be outside the month.
Do not mutate inputs. Empty input returns []. Money is not part of this interface.

Worked example: for an `America/Toronto` account, January 2026 is the interval
`[2026-01-01T05:00:00Z, 2026-02-01T05:00:00Z)` (Toronto is UTC-5 in January). A transaction at
`2026-02-01T04:30:00Z` is 23:30 on 31 January in Toronto, so it belongs to January; one at
`2026-02-01T05:30:00Z` is 00:30 on 1 February and belongs to February. So selecting January 2026 for
`Txn("a", 2026-02-01T04:30Z)` and `Txn("b", 2026-02-01T05:30Z)` returns `["a"]`.

Run from starter: `python -m pytest tests -q`. The records are entirely synthetic.
