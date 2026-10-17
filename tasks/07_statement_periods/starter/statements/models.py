"""Timestamped synthetic statement records."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Txn:
    id: str
    at: datetime

    @classmethod
    def from_dict(cls, row):
        return cls(str(row["id"]), datetime.fromisoformat(row["at"]))

    def as_dict(self):
        return {"id": self.id, "at": self.at.isoformat()}


@dataclass(frozen=True)
class PeriodRequest:
    account_tz: str
    year: int
    month: int

    @classmethod
    def from_dict(cls, row):
        return cls(row["account_tz"], row["year"], row["month"])

    def as_dict(self):
        return {"account_tz": self.account_tz, "year": self.year, "month": self.month}


@dataclass(frozen=True)
class Selection:
    request: PeriodRequest
    start: datetime
    end: datetime
    ids: list[str]

    def as_dict(self):
        return {"request": self.request.as_dict(), "start": self.start.isoformat(),
                "end": self.end.isoformat(), "ids": self.ids}
