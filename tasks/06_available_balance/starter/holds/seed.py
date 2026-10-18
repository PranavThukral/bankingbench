"""Synthetic accounts created the first time a database is used."""

# (account id, posted_minor, overdraft_minor), all in CAD minor units (2 dp).
SEED_ACCOUNTS = [
    ("acct_standard", 10000, 0),
    ("acct_flex", 10000, 5000),
]


def seed_accounts(db):
    """Insert the seed accounts without touching any account that already exists."""
    db.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?)", SEED_ACCOUNTS)
    return [account_id for account_id, _, _ in SEED_ACCOUNTS]
