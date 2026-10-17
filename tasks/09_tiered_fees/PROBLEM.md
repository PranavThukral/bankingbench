# Ticket: price the whole payment at its selected tier

`fees.schedule.compute_fee(amount_minor:int,schedule:Schedule)->int` returns integer minor units.
Public frozen dataclasses: `Tier(up_to_minor:int|None,bps:int,fixed_minor:int)` and
`Schedule(tiers:list[Tier],min_fee_minor:int,max_fee_minor:int)`.

Amounts are nonnegative ints, never bool; negative/noninteger -> ValueError. Schedule tiers are
ordered by strictly increasing nonnegative upper bounds, ending with exactly one None (infinity).
Bps/fixed/min/max are nonnegative ints, min <= max. Invalid schedules raise ValueError.

- Select the FIRST tier where amount <= up_to_minor, or None. Upper bounds are INCLUSIVE.
- Pricing is non-marginal: apply that selected tier's bps to the ENTIRE amount, then add its
  fixed fee. Do not sum bands.
- Raw fee = amount × bps / 10000 + fixed_minor. Round once to an integer using ROUND_HALF_UP,
  then clamp to [min_fee_minor,max_fee_minor]. This deliberately differs from interest's half-even.
- Zero amounts still incur the selected fixed fee, subject to the clamp. Input schedules are not
  mutated. The currency is implicit; all numbers use the same minor unit (e.g. CAD has 2 dp).

Run from starter: `python -m pytest tests -q`. No real fees, networks or institutions are represented.
