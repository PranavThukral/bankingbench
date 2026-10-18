"""Plain-text reconciliation report for the operations desk."""


def format_amount(minor):
    """Render integer CAD minor units (2 dp) without going through floating point."""
    major, cents = divmod(abs(minor), 100)
    return f"{'-' if minor < 0 else ''}{major}.{cents:02d}"


def describe_match(match, statements, entries):
    lines = sorted(match.statement_ids)
    total = sum(statements[identifier].amount_minor for identifier in lines)
    return (f"{match.rule}  {', '.join(lines)} -> {', '.join(sorted(match.ledger_ids))}"
            f"  ({format_amount(total)})")


def render_report(result, statement, ledger):
    statements = {line.id: line for line in statement}
    entries = {entry.id: entry for entry in ledger}
    out = [f"Matched groups: {len(result.matches)}"]
    for match in sorted(result.matches, key=lambda m: (m.rule, sorted(m.statement_ids))):
        out.append("  " + describe_match(match, statements, entries))
    out.append(f"Unmatched statement lines: {len(result.unmatched_statement)}")
    for identifier in sorted(result.unmatched_statement):
        line = statements[identifier]
        out.append(f"  {identifier}  {line.value_date.isoformat()}  {line.reference}"
                   f"  {format_amount(line.amount_minor)}  [{result.unmatched_statement[identifier]}]")
    out.append(f"Unmatched ledger entries: {len(result.unmatched_ledger)}")
    for identifier in sorted(result.unmatched_ledger):
        entry = entries[identifier]
        out.append(f"  {identifier}  {entry.booking_date.isoformat()}  {entry.reference}"
                   f"  {format_amount(entry.amount_minor)}  ({entry.kind})")
    return "\n".join(out) + "\n"
