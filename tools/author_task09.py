from author_common import task_meta, write

b = task_meta("09_tiered_fees", "Apply a non-marginal tiered fee schedule", "fees", [
    "fees.schedule:compute_fee, Tier, Schedule"], [
    ("wrong_exclusive_boundary", "Uses an exclusive upper tier boundary.", ["test_inclusive_boundaries"]),
    ("wrong_float_bps", "Binary percentage multiplication mis-rounds exact half-unit ties.", ["test_discovered_float_ties"]),
    ("wrong_marginal", "Charges each band separately instead of selecting one rate.", ["test_non_marginal"]),
], "Decimal quantization with tier selection by first matching record, versus integer numerator rounding.", terms=["Decimal", "ROUND_HALF_UP"])

write(b / "PROBLEM.md", '''
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
''')
write(b / "starter/fees/models.py", '''
"""Transport and validation for synthetic fee schedules."""
from dataclasses import dataclass


def nonnegative(value):
    return type(value) is int and value >= 0


@dataclass(frozen=True)
class Tier:
    up_to_minor: int | None
    bps: int
    fixed_minor: int

    def __post_init__(self):
        if self.up_to_minor is not None and not nonnegative(self.up_to_minor):
            raise ValueError("invalid bound")
        if not nonnegative(self.bps) or not nonnegative(self.fixed_minor):
            raise ValueError("invalid fee component")

    @classmethod
    def from_dict(cls, row):
        return cls(row["up_to_minor"], row["bps"], row["fixed_minor"])

    def as_dict(self):
        return {"up_to_minor": self.up_to_minor, "bps": self.bps, "fixed_minor": self.fixed_minor}


@dataclass(frozen=True)
class Schedule:
    tiers: list[Tier]
    min_fee_minor: int
    max_fee_minor: int

    def __post_init__(self):
        if not self.tiers or self.tiers[-1].up_to_minor is not None:
            raise ValueError("unbounded last tier required")
        if not nonnegative(self.min_fee_minor) or not nonnegative(self.max_fee_minor):
            raise ValueError("invalid limits")
        if self.min_fee_minor > self.max_fee_minor:
            raise ValueError("invalid clamp interval")
        prior = -1
        for tier in self.tiers[:-1]:
            if tier.up_to_minor is None or tier.up_to_minor <= prior:
                raise ValueError("strictly increasing bounded tiers required")
            prior = tier.up_to_minor

    @classmethod
    def from_dict(cls, row):
        return cls([Tier.from_dict(t) for t in row["tiers"]], row["min_fee_minor"], row["max_fee_minor"])

    def as_dict(self):
        return {"tiers": [tier.as_dict() for tier in self.tiers],
                "min_fee_minor": self.min_fee_minor, "max_fee_minor": self.max_fee_minor}


@dataclass(frozen=True)
class FeePreview:
    amount_minor: int
    fee_minor: int

    @property
    def total_minor(self):
        return self.amount_minor + self.fee_minor

    def as_dict(self):
        return {"amount_minor": self.amount_minor, "fee_minor": self.fee_minor, "total_minor": self.total_minor}
''')
reference = '''
from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer amount required")
    for tier in schedule.tiers:
        if tier.up_to_minor is None or amount_minor <= tier.up_to_minor:
            numerator = amount_minor * tier.bps + tier.fixed_minor * 10000
            rounded = (numerator + 5000) // 10000
            return min(schedule.max_fee_minor, max(schedule.min_fee_minor, rounded))
    raise ValueError("unbounded tier required")
'''
write(b / "solutions/reference/fees/schedule.py", reference)
write(b / "starter/fees/schedule.py", reference.replace('min(schedule.max_fee_minor, max(schedule.min_fee_minor, rounded))', 'rounded'))
write(b / "solutions/wrong_exclusive_boundary/fees/schedule.py", reference.replace('amount_minor <= tier.up_to_minor', 'amount_minor < tier.up_to_minor'))
write(b / "solutions/wrong_float_bps/fees/schedule.py", 'import math\n' + reference.replace(
    '            numerator = amount_minor * tier.bps + tier.fixed_minor * 10000\n            rounded = (numerator + 5000) // 10000',
    '            rounded = math.floor(amount_minor * (tier.bps / 10000) + tier.fixed_minor + .5)'))
write(b / "solutions/wrong_marginal/fees/schedule.py", '''
from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if type(amount_minor) is not int or amount_minor < 0:
        raise ValueError("nonnegative integer required")
    total, lower = 0, 0
    for tier in schedule.tiers:
        upper = amount_minor if tier.up_to_minor is None else min(amount_minor, tier.up_to_minor)
        total += max(0, upper - lower) * tier.bps
        if upper == amount_minor:
            total += tier.fixed_minor * 10000
            break
        lower = upper
    return min(schedule.max_fee_minor, max(schedule.min_fee_minor, (total + 5000) // 10000))
''')
write(b / "solutions/alt_valid/fees/schedule.py", '''
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fees.models import Tier, Schedule  # noqa: F401


def compute_fee(amount_minor, schedule):
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor < 0:
        raise ValueError("invalid payment amount")
    selected = next(t for t in schedule.tiers if t.up_to_minor is None or t.up_to_minor >= amount_minor)
    with localcontext() as ctx:
        ctx.prec = max(34, len(str(amount_minor)) + len(str(selected.bps)) + 10)
        raw = Decimal(amount_minor) * Decimal(selected.bps) / Decimal(10000) + selected.fixed_minor
        fee = int(raw.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if fee < schedule.min_fee_minor:
        return schedule.min_fee_minor
    if fee > schedule.max_fee_minor:
        return schedule.max_fee_minor
    return fee
''')
write(b / "starter/fees/preview.py", '''
"""Offline fee preview input/output."""
import argparse
import csv
import json
from pathlib import Path
from fees.models import Schedule, FeePreview
from fees.schedule import compute_fee


def read_schedule(path):
    return Schedule.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def preview(amounts, schedule):
    return [FeePreview(amount, compute_fee(amount, schedule)) for amount in amounts]


def read_amounts(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return [int(row["amount_minor"]) for row in csv.DictReader(stream)]


def write_preview(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=["amount_minor", "fee_minor", "total_minor"])
        output.writeheader()
        output.writerows(row.as_dict() for row in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview synthetic payment fees")
    parser.add_argument("schedule", type=Path)
    parser.add_argument("amounts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_preview(args.output, preview(read_amounts(args.amounts), read_schedule(args.schedule)))


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
from fees.schedule import compute_fee, Tier, Schedule


def test_one_tier():
    assert compute_fee(1000, Schedule([Tier(None, 100, 5)], 0, 99999)) == 15


def test_minimum():
    assert compute_fee(1, Schedule([Tier(None, 100, 0)], 10, 99999)) == 10
''')
write(b / "grader/naive/test_hidden.py", '''
from fees.schedule import compute_fee, Tier, Schedule


def test_tier_midpoints():
    schedule = Schedule([Tier(10000, 100, 10), Tier(20000, 50, 20), Tier(None, 25, 30)], 0, 999999)
    for amount, expected in [(5000, 60), (15000, 95), (30000, 105)]:
        assert compute_fee(amount, schedule) == expected
''')
text = (b / "task.toml").read_text(encoding="utf-8")
start = text.index('[variants.wrong_marginal]')
write(b / "task.toml", text[:start] + text[start:].replace('predicted_naive = "false_pass"', 'predicted_naive = "ok"'))
write(b / "NOTES.md", '''
# Private draft — fee reviewer notes

Integer numerator rounding is independent of the alternative's Decimal quantization. The
marginal candidate is plausible but predicted to fail even the naive mid-tier examples;
no artificial effort is made to make every wrong implementation pass the naive grader.
Float counterexamples are discovered by tools/find_ties.py, not chosen to fit a test.

## Blind review
Author self-review: upper-bound inclusivity, zero, fixed-fee clamp order and malformed schedules
were ambiguous in the starter; all are explicit in the ticket. Predictions: amount5000/bps3 ->2;
amount10000 uses the first inclusive tier; zero with fixed5/min10 ->10.
No unresolved graded ambiguity. Independent review remains owed.
''')
