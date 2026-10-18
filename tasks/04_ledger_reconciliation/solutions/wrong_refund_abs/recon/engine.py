"""Statement-to-ledger matching."""
from recon.models import StatementLine, LedgerEntry, Match, ReconResult  # noqa: F401

WINDOW_DAYS = 3


def day_gap(entry, line):
    return abs((entry.booking_date - line.value_date).days)


def exact_candidates(line, ledger, used_ledger):
    """Unused ledger payments that agree on reference and amount within the date window."""
    return [entry for entry in ledger
            if entry.id not in used_ledger and entry.kind == "payment"
            and entry.reference == line.reference and entry.amount_minor == abs(line.amount_minor)
            and day_gap(entry, line) <= WINDOW_DAYS]


def split_group(entry, ordered, used_statement):
    """All unused statement lines for the entry's reference inside the window, if they sum to it."""
    group = [line for line in ordered if line.id not in used_statement
             and line.reference == entry.reference and day_gap(entry, line) <= WINDOW_DAYS]
    if len(group) >= 2 and sum(line.amount_minor for line in group) == entry.amount_minor:
        return group
    return []


def refund_candidates(line, ledger, used_ledger):
    return [entry for entry in ledger
            if entry.id not in used_ledger and entry.kind == "refund"
            and entry.original_reference == line.reference and entry.amount_minor == -line.amount_minor]


def reconcile(statement, ledger):
    ordered = sorted(statement, key=lambda s: (s.value_date, s.id))
    used_statement, used_ledger, matches = set(), set(), []

    def record(lines, entry, rule):
        used_statement.update(line.id for line in lines)
        used_ledger.add(entry.id)
        matches.append(Match(frozenset(line.id for line in lines), frozenset([entry.id]), rule))

    for line in ordered:
        candidates = exact_candidates(line, ledger, used_ledger)
        if candidates:
            record([line], min(candidates, key=lambda e: (day_gap(e, line), e.booking_date, e.id)), "R1")
    for entry in sorted(ledger, key=lambda e: (e.reference, e.booking_date, e.id)):
        if entry.id not in used_ledger and entry.kind == "payment":
            group = split_group(entry, ordered, used_statement)
            if group:
                record(group, entry, "R2")
    for line in ordered:
        if line.id not in used_statement and line.amount_minor < 0:
            candidates = refund_candidates(line, ledger, used_ledger)
            if candidates:
                record([line], min(candidates, key=lambda e: (e.booking_date, e.id)), "R3")
    matched_signatures = {(s.value_date, s.amount_minor, s.reference) for s in statement if s.id in used_statement}
    unmatched = {line.id: "duplicate" if (line.value_date, line.amount_minor, line.reference) in matched_signatures
                 else "no_match" for line in ordered if line.id not in used_statement}
    return ReconResult(matches, unmatched, {e.id for e in ledger} - used_ledger)
