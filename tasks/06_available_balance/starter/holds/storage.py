"""SQLite persistence for the synthetic account adapter."""
from contextlib import contextmanager
import sqlite3


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
                created REAL, state TEXT)""")
        db.executemany("INSERT OR IGNORE INTO accounts VALUES (?,?,?)",
                       [("acct_standard", 10000, 0), ("acct_flex", 10000, 5000)])


def active_total(db, account, now):
    return db.execute("""SELECT COALESCE(SUM(amount),0) FROM authorizations
        WHERE account=? AND state='active' AND created>?""", (account, now - 7 * 86400)).fetchone()[0]


def account(db, identifier):
    return db.execute("SELECT * FROM accounts WHERE id=?", (identifier,)).fetchone()


def authorization(db, identifier):
    return db.execute("SELECT * FROM authorizations WHERE id=?", (identifier,)).fetchone()
