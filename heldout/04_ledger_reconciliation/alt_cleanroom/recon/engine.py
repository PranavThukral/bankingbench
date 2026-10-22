"""Clean-room implementation written from PROBLEM.md only (reviewer): rule passes over mutable pools."""
from recon.models import StatementLine, LedgerEntry, Match, ReconResult  # noqa: F401

DAYS = 3


def reconcile(statement, ledger):
    open_lines = sorted(statement, key=lambda s: (s.value_date, s.id))      # pool, kept in R1/R3 order
    open_entries = list(ledger)
    result = []

    def claim(lines, entry, rule):
        gone = {line.id for line in lines}
        open_lines[:] = [s for s in open_lines if s.id not in gone]
        open_entries[:] = [e for e in open_entries if e.id != entry.id]
        result.append(Match(frozenset(gone), frozenset({entry.id}), rule))

    # R1
    for line in list(open_lines):
        pool = [e for e in open_entries
                if e.kind == "payment" and e.reference == line.reference
                and e.amount_minor == line.amount_minor
                and abs((e.booking_date - line.value_date).days) <= DAYS]
        if pool:
            pool.sort(key=lambda e: (abs((e.booking_date - line.value_date).days), e.booking_date, e.id))
            claim([line], pool[0], "R1")
    # R2
    payments = sorted((e for e in open_entries if e.kind == "payment"),
                      key=lambda e: (e.reference, e.booking_date, e.id))
    for entry in payments:
        group = [s for s in open_lines
                 if s.reference == entry.reference and abs((s.value_date - entry.booking_date).days) <= DAYS]
        if len(group) >= 2 and sum(s.amount_minor for s in group) == entry.amount_minor:
            claim(group, entry, "R2")
    # R3
    for line in list(open_lines):
        if line.amount_minor >= 0:
            continue
        pool = [e for e in open_entries
                if e.kind == "refund" and e.original_reference == line.reference
                and e.amount_minor == abs(line.amount_minor)]
        if pool:
            pool.sort(key=lambda e: (e.booking_date, e.id))
            claim([line], pool[0], "R3")
    # R4
    matched_ids = {i for m in result for i in m.statement_ids}
    seen = {(s.value_date, s.amount_minor, s.reference) for s in statement if s.id in matched_ids}
    unmatched = {s.id: ("duplicate" if (s.value_date, s.amount_minor, s.reference) in seen else "no_match")
                 for s in open_lines}
    return ReconResult(result, unmatched, {e.id for e in open_entries})
