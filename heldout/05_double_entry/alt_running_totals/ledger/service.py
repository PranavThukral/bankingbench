from collections import defaultdict
import psycopg
from psycopg import errors
from ledger.models import (Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount,
                           AlreadyReversed, CannotReverseReversal, CURRENCIES, validate_lines)  # noqa: F401
from ledger.schema import SCHEMA

__all__ = ["LedgerService", "Line", "LedgerError", "UnbalancedTransaction", "InvalidAmount",
           "UnknownAccount", "AlreadyReversed", "CannotReverseReversal"]


class LedgerService:
    def __init__(self, database_url):
        self.url = database_url
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(5051)")
            conn.execute(SCHEMA)

    def connect(self):
        return psycopg.connect(self.url)

    def create_account(self, code, currency):
        if not code or currency not in CURRENCIES:
            raise LedgerError("invalid account")
        with self.connect() as conn:
            conn.execute("INSERT INTO accounts VALUES (%s,%s) ON CONFLICT DO NOTHING", (code, currency))
            if conn.execute("SELECT currency FROM accounts WHERE code=%s", (code,)).fetchone()[0] != currency:
                raise LedgerError("currency mismatch")
            conn.execute("INSERT INTO account_net(code) VALUES (%s) ON CONFLICT DO NOTHING", (code,))
            conn.execute("INSERT INTO currency_totals(currency) VALUES (%s) ON CONFLICT DO NOTHING", (currency,))

    def _apply(self, conn, lines, memo, reversal_of=None):
        currency_of = {}
        net = defaultdict(int)
        for line in lines:
            if line.account_code not in currency_of:
                row = conn.execute("SELECT currency FROM accounts WHERE code=%s", (line.account_code,)).fetchone()
                if row is None:
                    raise UnknownAccount(line.account_code)
                currency_of[line.account_code] = row[0]
            net[currency_of[line.account_code]] += line.amount_minor if line.side == "debit" else -line.amount_minor
        if any(net.values()):
            raise UnbalancedTransaction("each currency must balance")
        txn = conn.execute("INSERT INTO transactions(memo,reversal_of) VALUES (%s,%s) RETURNING id",
                           (memo, reversal_of)).fetchone()[0]
        for line in lines:
            sign = 1 if line.side == "debit" else -1
            conn.execute("INSERT INTO lines VALUES (%s,%s,%s,%s)", (txn, line.account_code, line.side, line.amount_minor))
            conn.execute("UPDATE account_net SET net=net+%s WHERE code=%s", (sign * line.amount_minor, line.account_code))
            column = "debit" if line.side == "debit" else "credit"
            conn.execute(f"UPDATE currency_totals SET {column}={column}+%s WHERE currency=%s",
                         (line.amount_minor, currency_of[line.account_code]))
        return txn

    def post(self, lines, memo):
        validate_lines(lines)
        with self.connect() as conn:
            return self._apply(conn, lines, memo)

    def reverse(self, txn_id, memo):
        with self.connect() as conn:
            row = conn.execute("SELECT reversal_of FROM transactions WHERE id=%s FOR UPDATE", (txn_id,)).fetchone()
            if row is None:
                raise LedgerError("unknown transaction")
            if row[0] is not None:
                raise CannotReverseReversal(txn_id)
            rows = conn.execute("SELECT code,side,amount FROM lines WHERE txn=%s", (txn_id,)).fetchall()
            swapped = [Line(c, "credit" if s == "debit" else "debit", a) for c, s, a in rows]
            try:
                return self._apply(conn, swapped, memo, txn_id)
            except errors.UniqueViolation:
                raise AlreadyReversed(txn_id) from None

    def balance(self, account_code):
        with self.connect() as conn:
            row = conn.execute("SELECT net FROM account_net WHERE code=%s", (account_code,)).fetchone()
            if row is None:
                raise UnknownAccount(account_code)
            return int(row[0])

    def trial_balance(self):
        with self.connect() as conn:
            rows = conn.execute("""SELECT c.currency, COALESCE(t.debit,0), COALESCE(t.credit,0)
                FROM (SELECT DISTINCT currency FROM accounts) c LEFT JOIN currency_totals t USING (currency)""").fetchall()
        return {currency: (int(d), int(c)) for currency, d, c in rows}
