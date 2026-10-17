# Ticket: monthly statements follow the account timezone

`statements.period.period_bounds(account_tz:str,year:int,month:int)->tuple[datetime,datetime]`
returns aware UTC instants for a half-open interval. `select(txns:list[Txn],account_tz,year,month)`
returns transaction ids sorted by instant, then lexicographic id. Frozen `Txn(id:str,at:datetime)`
is public. IDs are unique and timestamps may have arbitrary aware offsets and microseconds.

The period is the calendar month in the account's IANA timezone: local 00:00 on day 1 inclusive
through local 00:00 on day 1 of the next month exclusive, converted to UTC using zoneinfo.
Account timezone and requested month are valid (years 1900–2098); daylight saving rules apply
independently to both endpoints. Each input timestamp must be aware with a non-None utcoffset,
otherwise select raises ValueError, even when that transaction would be outside the month.
Do not mutate inputs. Empty input returns []. Money is not part of this interface.

Run from starter: `python -m pytest tests -q`. The records are entirely synthetic.
