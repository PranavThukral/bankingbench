from collections import defaultdict
import psycopg
from ledger.models import (Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount,
                           AlreadyReversed, CannotReverseReversal, CURRENCIES, validate_lines)  # noqa: F401


class LedgerService:
    def __init__(self, database_url):
        self.url = database_url
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS accounts(code text PRIMARY KEY, currency text NOT NULL);
                CREATE TABLE IF NOT EXISTS transactions(id bigserial PRIMARY KEY, memo text,
                    reversal_of bigint REFERENCES transactions(id), reversed_by bigint);
                CREATE TABLE IF NOT EXISTS lines(txn bigint REFERENCES transactions(id),
                    code text REFERENCES accounts(code), side text, amount bigint)""")

    def connect(self):
        return psycopg.connect(self.url)

    def create_account(self, code, currency):
        if not code or currency not in CURRENCIES:
            raise LedgerError("invalid account")
        with self.connect() as conn:
            conn.execute("INSERT INTO accounts VALUES (%s,%s) ON CONFLICT DO NOTHING", (code, currency))
            if conn.execute("SELECT currency FROM accounts WHERE code=%s", (code,)).fetchone()[0] != currency:
                raise LedgerError("currency mismatch")

    def _validate(self, conn, lines):
        validate_lines(lines)
        totals = defaultdict(int)
        for line in lines:
            account = conn.execute("SELECT currency FROM accounts WHERE code=%s", (line.account_code,)).fetchone()
            if account is None:
                raise UnknownAccount(line.account_code)
            totals[account[0]] += line.amount_minor * (1 if line.side == "debit" else -1)
        if any(totals.values()):
            raise UnbalancedTransaction("per-currency sums must balance")

    def _insert(self, conn, lines, memo, reversal_of=None):
        txn = conn.execute("INSERT INTO transactions(memo,reversal_of) VALUES (%s,%s) RETURNING id",
                           (memo, reversal_of)).fetchone()[0]
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO lines VALUES (%s,%s,%s,%s)",
                               [(txn, line.account_code, line.side, line.amount_minor) for line in lines])
        return txn

    def post(self, lines, memo):
        with self.connect() as conn:
            self._validate(conn, lines)
            return self._insert(conn, lines, memo)

    def reverse(self, txn_id, memo):
        with self.connect() as conn:
            row = conn.execute("SELECT reversal_of,reversed_by FROM transactions WHERE id=%s FOR UPDATE", (txn_id,)).fetchone()
            if row is None:
                raise LedgerError("unknown transaction")
            if row[0] is not None:
                raise CannotReverseReversal(txn_id)
            if row[1] is not None:
                raise AlreadyReversed(txn_id)
            rows = conn.execute("SELECT code,side,amount FROM lines WHERE txn=%s", (txn_id,)).fetchall()
            opposite = [Line(code, "credit" if side == "debit" else "debit", amount) for code, side, amount in rows]
            reversal = self._insert(conn, opposite, memo, txn_id)
            conn.execute("UPDATE transactions SET reversed_by=%s WHERE id=%s", (reversal, txn_id))
            return reversal

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
