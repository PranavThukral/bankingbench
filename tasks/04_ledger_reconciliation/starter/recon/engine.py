"""Statement-to-ledger matching."""
from recon.models import StatementLine, LedgerEntry, Match, ReconResult  # noqa: F401


def exact_candidates(line, ledger):
    """Ledger payments that agree with a statement line on reference, amount and booking date."""
    return [entry for entry in ledger
            if entry.kind == "payment" and entry.reference == line.reference
            and entry.amount_minor == line.amount_minor and entry.booking_date == line.value_date]


def reconcile(statement, ledger):
    matches, matched = [], set()
    for line in sorted(statement, key=lambda s: (s.value_date, s.id)):
        candidates = exact_candidates(line, ledger)
        if candidates:
            entry = min(candidates, key=lambda e: e.id)
            matches.append(Match(frozenset([line.id]), frozenset([entry.id]), "R1"))
            matched.add(line.id)
    unmatched = {s.id: "no_match" for s in statement if s.id not in matched}
    used = {identifier for match in matches for identifier in match.ledger_ids}
    return ReconResult(matches, unmatched, {e.id for e in ledger} - used)
