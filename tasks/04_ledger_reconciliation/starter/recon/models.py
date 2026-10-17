"""Input records and transport conversion for synthetic reconciliation."""
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class StatementLine:
    id: str
    value_date: date
    amount_minor: int
    reference: str

    @classmethod
    def from_dict(cls, row):
        return cls(str(row["id"]), date.fromisoformat(row["value_date"]),
                   int(row["amount_minor"]), str(row["reference"]))

    def as_dict(self):
        return dict(id=self.id, value_date=self.value_date.isoformat(),
                    amount_minor=self.amount_minor, reference=self.reference)


@dataclass(frozen=True)
class LedgerEntry:
    id: str
    booking_date: date
    amount_minor: int
    reference: str
    kind: str = "payment"
    original_reference: str | None = None

    @classmethod
    def from_dict(cls, row):
        return cls(str(row["id"]), date.fromisoformat(row["booking_date"]), int(row["amount_minor"]),
                   str(row["reference"]), row.get("kind", "payment"), row.get("original_reference"))

    def as_dict(self):
        return dict(id=self.id, booking_date=self.booking_date.isoformat(),
                    amount_minor=self.amount_minor, reference=self.reference,
                    kind=self.kind, original_reference=self.original_reference)


@dataclass(frozen=True)
class Match:
    statement_ids: frozenset[str]
    ledger_ids: frozenset[str]
    rule: str

    def as_dict(self):
        return dict(statement_ids=sorted(self.statement_ids), ledger_ids=sorted(self.ledger_ids), rule=self.rule)


@dataclass(frozen=True)
class ReconResult:
    matches: list[Match]
    unmatched_statement: dict[str, str]
    unmatched_ledger: set[str]

    def as_dict(self):
        return dict(matches=[m.as_dict() for m in self.matches],
                    unmatched_statement=self.unmatched_statement,
                    unmatched_ledger=sorted(self.unmatched_ledger))
