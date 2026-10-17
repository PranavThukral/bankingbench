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
                      and e.reference == s.reference and e.amount_minor == abs(s.amount_minor)
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
