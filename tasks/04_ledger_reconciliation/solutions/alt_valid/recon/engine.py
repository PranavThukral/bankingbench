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
