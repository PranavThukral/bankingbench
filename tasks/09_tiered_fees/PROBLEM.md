# Ticket: price the whole payment at its selected tier

`fees.schedule.compute_fee(amount_minor:int,schedule:Schedule)->int` returns integer minor units.
Public frozen dataclasses: `Tier(up_to_minor:int|None,bps:int,fixed_minor:int)` and
`Schedule(tiers:list[Tier],min_fee_minor:int,max_fee_minor:int)`.

Amounts are nonnegative ints, never bool; negative/noninteger -> ValueError. Schedule tiers are
ordered by strictly increasing nonnegative upper bounds, ending with exactly one None (infinity).
Bps/fixed/min/max are nonnegative ints, min <= max. `compute_fee` raises ValueError for an invalid
schedule (checked on every call, whatever the amount).

- Select the FIRST tier where amount <= up_to_minor, or None. Upper bounds are INCLUSIVE.
- Pricing is non-marginal: apply that selected tier's bps to the ENTIRE amount, then add its
  fixed fee. Do not sum bands.
- Raw fee = amount × bps / 10000 + fixed_minor. Round once to an integer using ROUND_HALF_UP,
  then clamp to [min_fee_minor,max_fee_minor]. This deliberately differs from interest's half-even.
- Zero amounts still incur the selected fixed fee, subject to the clamp. Input schedules are not
  mutated. The currency is implicit; all numbers use the same minor unit (e.g. CAD has 2 dp).

Worked example: tiers `[Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)]` with
`min_fee_minor=25`, `max_fee_minor=100`. An amount of 5000 uses the first tier: 5000 x 100 bps = 50, plus 10, so 60.
An amount of 15000 uses the second tier on the whole amount: 75 + 20 = 95. An amount of 100 would cost 11
and is raised to the minimum, 25. An amount of 30000 would cost 75 + 30 = 105 and is capped at 100.

Run from starter: `python -m pytest tests -q`. No real fees, networks or institutions are represented.
