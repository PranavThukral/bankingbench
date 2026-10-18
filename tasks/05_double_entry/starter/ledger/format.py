"""Human-readable rendering of journal figures. Uses only the public service surface."""
from ledger.models import CURRENCIES


def format_minor(amount_minor, currency):
    """Render integer minor units with the decimal places of the currency (JPY 0, KWD/BHD 3, others 2)."""
    places = CURRENCIES[currency]
    sign = "-" if amount_minor < 0 else ""
    if places == 0:
        return f"{sign}{abs(amount_minor)} {currency}"
    major, minor = divmod(abs(amount_minor), 10 ** places)
    return f"{sign}{major}.{minor:0{places}d} {currency}"


def render_trial_balance(trial_balance):
    rows = [f"{'currency':<10}{'debits':>20}{'credits':>20}{'difference':>20}"]
    for currency in sorted(trial_balance):
        debit, credit = trial_balance[currency]
        rows.append(f"{currency:<10}{format_minor(debit, currency):>20}{format_minor(credit, currency):>20}"
                    f"{format_minor(debit - credit, currency):>20}")
    return "\n".join(rows) + "\n"


def render_posting(lines, currencies, memo):
    """Describe one journal entry; `currencies` maps account code to currency."""
    out = [f"Entry: {memo}"]
    for line in lines:
        amount = format_minor(line.amount_minor, currencies[line.account_code])
        out.append(f"  {line.side:<7}{line.account_code:<24}{amount:>20}")
    return "\n".join(out) + "\n"
