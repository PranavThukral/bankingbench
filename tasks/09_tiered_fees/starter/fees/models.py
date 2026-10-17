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
