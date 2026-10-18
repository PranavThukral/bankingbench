"""Plain-text summary of accounts for the operations desk."""


def money(minor):
    major, cents = divmod(abs(minor), 100)
    return f"{'-' if minor < 0 else ''}{major}.{cents:02d}"


def render_overview(rows):
    out = [f"{'account':<16}{'posted':>12}{'overdraft':>12}  authorizations"]
    for row in rows:
        states = ", ".join(f"{state}={count}" for state, count in sorted(row["authorizations"].items())) or "none"
        out.append(f"{row['id']:<16}{money(row['posted']):>12}{money(row['overdraft']):>12}  {states}")
    return "\n".join(out) + "\n"
