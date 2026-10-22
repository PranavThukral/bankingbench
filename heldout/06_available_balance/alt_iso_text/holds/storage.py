"""SQLite persistence for the synthetic account adapter."""
from contextlib import contextmanager
import sqlite3
from holds.seed import seed_accounts


@contextmanager
def transaction(path):
    connection = sqlite3.connect(str(path), timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.execute("BEGIN")
            yield connection
    finally:
        connection.close()


def initialize(path):
    with transaction(path) as db:
        db.executescript("""CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, posted INTEGER, overdraft INTEGER);
            CREATE TABLE IF NOT EXISTS authorizations(id TEXT PRIMARY KEY, account TEXT, amount INTEGER,
                created TEXT, state TEXT)""")
        seed_accounts(db)


HOLD_SECONDS = 7 * 86400


def active_total(db, account, now):
    """Sum of the account's active holds that have not yet expired at `now` (epoch seconds)."""
    from datetime import datetime, timedelta
    rows = db.execute("SELECT amount, created FROM authorizations WHERE account=? AND state='active'", (account,)).fetchall()
    return sum(r["amount"] for r in rows if datetime.fromisoformat(r["created"]) + timedelta(days=7) > now)


def account(db, identifier):
    return db.execute("SELECT * FROM accounts WHERE id=?", (identifier,)).fetchone()


def authorization(db, identifier):
    return db.execute("SELECT * FROM authorizations WHERE id=?", (identifier,)).fetchone()


def all_authorizations(db):
    return db.execute("SELECT * FROM authorizations ORDER BY created, id").fetchall()


def accounts_overview(db):
    """Every account with the number of authorization records in each state."""
    rows = db.execute("SELECT id, posted, overdraft FROM accounts ORDER BY id").fetchall()
    states = db.execute("SELECT account, state, COUNT(*) AS n FROM authorizations GROUP BY account, state").fetchall()
    counts = {}
    for item in states:
        counts.setdefault(item["account"], {})[item["state"]] = item["n"]
    return [dict(id=r["id"], posted=r["posted"], overdraft=r["overdraft"], authorizations=counts.get(r["id"], {}))
            for r in rows]
