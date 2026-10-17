from author_common import task_meta, write

b = task_meta("04_ledger_reconciliation", "Reconcile synthetic statements deterministically", "recon", [
    "recon.engine:reconcile, StatementLine, LedgerEntry, Match, ReconResult"], [
    ("wrong_no_consumption", "Allows one ledger payment to match multiple statement lines.", ["test_duplicate_statement_line_left_unmatched"]),
    ("wrong_split_ignored", "Omits aggregate split matches.", ["test_split_all_lines"]),
    ("wrong_refund_abs", "Treats negative statement amounts as payments of the absolute amount.", ["test_refund_kind_and_original_reference"]),
], "Indexed candidate buckets and explicit remaining-id maps instead of repeated scans with consumed sets.", difficulty="hard", terms=["subset search"])

write(b / "PROBLEM.md", '''
# Ticket: reconcile a synthetic statement to ledger entries

Keep `recon.engine.reconcile(statement: list[StatementLine], ledger: list[LedgerEntry]) -> ReconResult`.
Public frozen dataclasses (also exported from recon.engine):
- `StatementLine(id: str, value_date: date, amount_minor: int, reference: str)`
- `LedgerEntry(id: str, booking_date: date, amount_minor: int, reference: str,
  kind: "payment"|"refund" = "payment", original_reference: str|None = None)`
- `Match(statement_ids: frozenset[str], ledger_ids: frozenset[str], rule: str)`
- `ReconResult(matches: list[Match], unmatched_statement: dict[str,str], unmatched_ledger: set[str])`

All amounts are integer minor units in one synthetic currency (CAD, 2 dp); statement amounts
are signed, ledger payment/refund amounts positive. Dates are calendar dates. IDs are unique
within each input, strings sort lexicographically. Inputs are valid and must not be mutated.
Apply complete passes in the following order; each id can appear in at most one match:

1. R1: process statements by `(value_date,id)`. Match an unmatched ledger **payment** with equal
   reference and equal signed amount, date difference <=3 calendar days. Choose smallest absolute
   date difference, then earliest booking_date, then smallest id.
2. R2: process remaining ledger payments by `(reference,booking_date,id)`. For each payment,
   collect **all** unmatched statement lines of the same reference within +/-3 days of that payment.
   If at least two lines and their signed sum equals its amount, match the whole group. Do not
   search subsets. Negative lines, if present, contribute their signed amount to this pass.
3. R3: process remaining negative statements by `(value_date,id)`. Match an unmatched ledger
   **refund**, with original_reference equal to the statement reference and positive amount equal
   to abs(statement amount). There is no date restriction in R3. Choose earliest booking_date,
   then smallest id. The refund's own reference need not equal the original reference.
4. R4: each remaining statement identical in `(value_date,amount_minor,reference)` to any matched
   statement gets reason `duplicate`; otherwise `no_match`. Unused ledger ids form unmatched_ledger.

Use rule strings `R1`, `R2`, `R3`. Match-list order is not graded. Exact membership, reasons,
partitions and no reuse are graded. Empty inputs produce empty collections.
Run from starter: `python -m pytest tests -q`.
''')
write(b / "starter/recon/models.py", '''
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
''')
reference = '''
from recon.models import StatementLine, LedgerEntry, Match, ReconResult  # noqa: F401


def reconcile(statement, ledger):
    ordered = sorted(statement, key=lambda s: (s.value_date, s.id))
    used_s, used_l, matches = set(), set(), []

    def record(lines, entry, rule):
        used_s.update(s.id for s in lines)
        used_l.add(entry.id)
        matches.append(Match(frozenset(s.id for s in lines), frozenset([entry.id]), rule))

    for s in ordered:
        candidates = [e for e in ledger if e.id not in used_l and e.kind == "payment"
                      and e.reference == s.reference and e.amount_minor == s.amount_minor
                      and abs((e.booking_date - s.value_date).days) <= 3]
        if candidates:
            chosen = min(candidates, key=lambda e: (abs((e.booking_date - s.value_date).days), e.booking_date, e.id))
            record([s], chosen, "R1")
    for e in sorted(ledger, key=lambda e: (e.reference, e.booking_date, e.id)):
        if e.id in used_l or e.kind != "payment":
            continue
        group = [s for s in ordered if s.id not in used_s and s.reference == e.reference
                 and abs((e.booking_date - s.value_date).days) <= 3]
        if len(group) >= 2 and sum(s.amount_minor for s in group) == e.amount_minor:
            record(group, e, "R2")
    for s in ordered:
        if s.id in used_s or s.amount_minor >= 0:
            continue
        candidates = [e for e in ledger if e.id not in used_l and e.kind == "refund"
                      and e.original_reference == s.reference and e.amount_minor == -s.amount_minor]
        if candidates:
            record([s], min(candidates, key=lambda e: (e.booking_date, e.id)), "R3")
    matched_signatures = {(s.value_date, s.amount_minor, s.reference) for s in statement if s.id in used_s}
    unmatched = {s.id: "duplicate" if (s.value_date, s.amount_minor, s.reference) in matched_signatures
                 else "no_match" for s in ordered if s.id not in used_s}
    return ReconResult(matches, unmatched, {e.id for e in ledger} - used_l)
'''
write(b / "solutions/reference/recon/engine.py", reference)
write(b / "starter/recon/engine.py", reference.replace('abs((e.booking_date - s.value_date).days) <= 3', 'abs((e.booking_date - s.value_date).days) == 0'))
write(b / "solutions/wrong_no_consumption/recon/engine.py", reference.replace('e.id not in used_l and e.kind == "payment"', 'e.kind == "payment"'))
write(b / "solutions/wrong_split_ignored/recon/engine.py", reference.replace('if len(group) >= 2 and', 'if len(group) < 0 and'))
# Independent omission of the R2 pass rather than an impossible conditional.
path = b / "solutions/wrong_split_ignored/recon/engine.py"
start, end = reference.index('    for e in sorted(ledger'), reference.index('    for s in ordered:', reference.index('    for e in sorted(ledger'))
write(path, reference[:start] + reference[end:])
write(b / "solutions/wrong_refund_abs/recon/engine.py", reference.replace(
    'e.amount_minor == s.amount_minor', 'e.amount_minor == abs(s.amount_minor)'))
write(b / "solutions/alt_valid/recon/engine.py", '''
from collections import defaultdict
from recon.models import StatementLine, LedgerEntry, Match, ReconResult  # noqa: F401


def reconcile(statement, ledger):
    pending = {s.id: s for s in statement}
    remaining = {e.id: e for e in ledger}
    by_reference = defaultdict(list)
    for entry in ledger:
        if entry.kind == "payment":
            by_reference[entry.reference].append(entry)
    output = []
    consumed_signatures = set()

    def take(ids, target, rule):
        for identifier in ids:
            line = pending.pop(identifier)
            consumed_signatures.add((line.value_date, line.amount_minor, line.reference))
        del remaining[target]
        output.append(Match(frozenset(ids), frozenset([target]), rule))

    for line in sorted(statement, key=lambda v: (v.value_date, v.id)):
        possible = sorted((abs((e.booking_date - line.value_date).days), e.booking_date, e.id)
                          for e in by_reference[line.reference]
                          if e.id in remaining and e.amount_minor == line.amount_minor
                          and abs((e.booking_date - line.value_date).days) <= 3)
        if possible:
            take([line.id], possible[0][2], "R1")
    for target in sorted(ledger, key=lambda v: (v.reference, v.booking_date, v.id)):
        if target.id not in remaining or target.kind != "payment":
            continue
        ids = [i for i, s in pending.items() if s.reference == target.reference
               and abs((s.value_date - target.booking_date).days) <= 3]
        total = sum(pending[i].amount_minor for i in ids)
        if len(ids) > 1 and total == target.amount_minor:
            take(ids, target.id, "R2")
    for line in sorted(list(pending.values()), key=lambda v: (v.value_date, v.id)):
        if line.amount_minor >= 0:
            continue
        refunds = sorted((e.booking_date, e.id) for e in remaining.values()
                         if e.kind == "refund" and e.original_reference == line.reference
                         and e.amount_minor + line.amount_minor == 0)
        if refunds:
            take([line.id], refunds[0][1], "R3")
    reasons = {}
    for identifier, line in pending.items():
        signature = line.value_date, line.amount_minor, line.reference
        reasons[identifier] = "duplicate" if signature in consumed_signatures else "no_match"
    return ReconResult(output, reasons, set(remaining))
''')
write(b / "starter/recon/preview.py", '''
"""Transport layer for offline reconciliation previews."""
import argparse
import json
from pathlib import Path
from recon.models import StatementLine, LedgerEntry
from recon.engine import reconcile


def read_statement(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [StatementLine.from_dict(row) for row in rows]


def read_ledger(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [LedgerEntry.from_dict(row) for row in rows]


def preview(statement, ledger):
    result = reconcile(statement, ledger)
    data = result.as_dict()
    data["counts"] = {
        "statement": len(statement),
        "ledger": len(ledger),
        "matches": len(result.matches),
        "unmatched_statement": len(result.unmatched_statement),
        "unmatched_ledger": len(result.unmatched_ledger),
    }
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reconcile synthetic JSON records")
    parser.add_argument("statement", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    data = preview(read_statement(args.statement), read_ledger(args.ledger))
    rendered = json.dumps(data, indent=2) + "\\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
from datetime import date, timedelta
from recon.engine import reconcile, StatementLine, LedgerEntry

DAY = date(2026, 1, 5)


def test_exact():
    result = reconcile([StatementLine("s", DAY, 100, "ref")], [LedgerEntry("l", DAY, 100, "ref")])
    assert result.matches[0].statement_ids == frozenset(["s"])


def test_date_window():
    result = reconcile([StatementLine("s", DAY, 100, "ref")], [LedgerEntry("l", DAY + timedelta(days=2), 100, "ref")])
    assert len(result.matches) == 1
''')
write(b / "grader/naive/test_hidden.py", '''
from datetime import date
from recon.engine import reconcile, StatementLine, LedgerEntry


def test_clean_one_to_one():
    day = date(2026, 1, 5)
    statement = [StatementLine(f"s{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    ledger = [LedgerEntry(f"l{i}", day, 100 + i, f"ref{i}") for i in range(3)]
    assert len(reconcile(statement, ledger).matches) == 3
''')
write(b / "NOTES.md", '''
# Private draft — reconciliation reviewer notes

Counts alone hide identity reuse. The three realistic candidates respectively reuse an entry,
implement only the common R1 case, or normalize a negative amount too early. Alternative
uses remaining-record maps and indexed references; reference maintains consumed-id sets.

## Blind review
Author self-review on ticket plus starter. Ambiguities: R2 traversal with repeated references,
negative R2 amounts, R3 tie breaks/date window, ordering of result lists. Ticket now states all
of these. Predictions: exact amount at +3 days -> R1; duplicate exact statement -> one R1 and
one duplicate; parts 40+60 against 100 -> one R2 with both ids. No unresolved graded ambiguity.
Independent review remains owed.
''')
