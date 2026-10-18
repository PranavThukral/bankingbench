import psycopg
from ledger.models import (Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount,
                           AlreadyReversed, CannotReverseReversal, CURRENCIES, validate_lines)  # noqa: F401
from ledger.schema import SCHEMA


__all__ = ["LedgerService", "Line", "LedgerError", "UnbalancedTransaction", "InvalidAmount",
           "UnknownAccount", "AlreadyReversed", "CannotReverseReversal"]


class LedgerService:
    def __init__(self, database_url):
        self.url = database_url
        with self.connect() as conn:
            conn.execute(SCHEMA)

    def connect(self):
        return psycopg.connect(self.url, autocommit=True)

    def create_account(self, code, currency):
        if not code or currency not in CURRENCIES:
            raise LedgerError("invalid account")
        with self.connect() as conn:
            conn.execute("INSERT INTO accounts VALUES (%s,%s) ON CONFLICT DO NOTHING", (code, currency))
            if conn.execute("SELECT currency FROM accounts WHERE code=%s", (code,)).fetchone()[0] != currency:
                raise LedgerError("currency mismatch")

    def post(self, lines, memo):
        validate_lines(lines)
        with self.connect() as conn:
            txn = conn.execute("INSERT INTO transactions(memo) VALUES (%s) RETURNING id", (memo,)).fetchone()[0]
            for line in lines:
                conn.execute("INSERT INTO lines VALUES (%s,%s,%s,%s)",
                             (txn, line.account_code, line.side, line.amount_minor))
            return txn

    def balance(self, account_code):
        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM accounts WHERE code=%s", (account_code,)).fetchone() is None:
                raise UnknownAccount(account_code)
            return int(conn.execute("""SELECT COALESCE(SUM(CASE WHEN side='debit' THEN amount ELSE -amount END),0)
                FROM lines WHERE code=%s""", (account_code,)).fetchone()[0])

    def trial_balance(self):
        with self.connect() as conn:
            rows = conn.execute("""SELECT a.currency,
                COALESCE(SUM(l.amount) FILTER (WHERE l.side='debit'),0),
                COALESCE(SUM(l.amount) FILTER (WHERE l.side='credit'),0)
                FROM accounts a LEFT JOIN lines l ON a.code=l.code GROUP BY a.currency""").fetchall()
        return {currency: (int(debit), int(credit)) for currency, debit, credit in rows}
