import json
import psycopg
from ledger.models import (Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount,
                           AlreadyReversed, CannotReverseReversal, CURRENCIES, validate_lines)  # noqa: F401

RECORDS = "jsonb_to_recordset(%s::jsonb) AS x(account_code text, side text, amount_minor bigint)"


__all__ = ["LedgerService", "Line", "LedgerError", "UnbalancedTransaction", "InvalidAmount",
           "UnknownAccount", "AlreadyReversed", "CannotReverseReversal"]


class LedgerService:
    def __init__(self, database_url):
        self.dsn = database_url
        with psycopg.connect(self.dsn) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS journal_accounts(name text PRIMARY KEY, denomination text);
                CREATE TABLE IF NOT EXISTS journal_batches(number bigserial PRIMARY KEY, note text,
                    undoes bigint, undone_by bigint);
                CREATE TABLE IF NOT EXISTS journal_lines(batch bigint, account text, direction text, value bigint)""")

    def create_account(self, code, currency):
        if not code or currency not in CURRENCIES:
            raise LedgerError("invalid account")
        with psycopg.connect(self.dsn) as c:
            c.execute("INSERT INTO journal_accounts VALUES (%s,%s) ON CONFLICT DO NOTHING", (code, currency))
            stored, = c.execute("SELECT denomination FROM journal_accounts WHERE name=%s", (code,)).fetchone()
            if stored != currency:
                raise LedgerError("account already has a different denomination")

    def post(self, lines, memo):
        validate_lines(lines)
        payload = json.dumps([line.as_dict() for line in lines])
        with psycopg.connect(self.dsn) as c:
            absent = c.execute("SELECT x.account_code FROM " + RECORDS +
                               " LEFT JOIN journal_accounts a ON a.name=x.account_code WHERE a.name IS NULL",
                               (payload,)).fetchone()
            if absent:
                raise UnknownAccount(absent[0])
            imbalance = c.execute("SELECT a.denomination FROM " + RECORDS +
                                  " JOIN journal_accounts a ON a.name=x.account_code GROUP BY a.denomination "
                                  "HAVING SUM(CASE WHEN x.side='debit' THEN x.amount_minor ELSE -x.amount_minor END)<>0",
                                  (payload,)).fetchone()
            if imbalance:
                raise UnbalancedTransaction("denomination totals differ")
            number, = c.execute("INSERT INTO journal_batches(note) VALUES (%s) RETURNING number", (memo,)).fetchone()
            c.execute("INSERT INTO journal_lines SELECT %s,x.account_code,x.side,x.amount_minor FROM " + RECORDS,
                      (number, payload))
            return number

    def reverse(self, txn_id, memo):
        with psycopg.connect(self.dsn) as c:
            info = c.execute("SELECT undoes,undone_by FROM journal_batches WHERE number=%s FOR UPDATE", (txn_id,)).fetchone()
            if info is None:
                raise LedgerError("transaction not found")
            original, prior = info
            if original is not None:
                raise CannotReverseReversal(txn_id)
            if prior is not None:
                raise AlreadyReversed(txn_id)
            number, = c.execute("INSERT INTO journal_batches(note,undoes) VALUES (%s,%s) RETURNING number", (memo, txn_id)).fetchone()
            c.execute("""INSERT INTO journal_lines SELECT %s,account,
                CASE direction WHEN 'debit' THEN 'credit' ELSE 'debit' END,value
                FROM journal_lines WHERE batch=%s""", (number, txn_id))
            c.execute("UPDATE journal_batches SET undone_by=%s WHERE number=%s", (number, txn_id))
            return number

    def balance(self, account_code):
        with psycopg.connect(self.dsn) as c:
            exists = c.execute("SELECT 1 FROM journal_accounts WHERE name=%s", (account_code,)).fetchone()
            if not exists:
                raise UnknownAccount(account_code)
            value, = c.execute("""SELECT COALESCE(SUM(value * CASE direction WHEN 'debit' THEN 1 ELSE -1 END),0)
                FROM journal_lines WHERE account=%s""", (account_code,)).fetchone()
            return int(value)

    def trial_balance(self):
        with psycopg.connect(self.dsn) as c:
            rows = c.execute("""SELECT denomination,
                COALESCE(SUM(CASE WHEN direction='debit' THEN value ELSE 0 END),0),
                COALESCE(SUM(CASE WHEN direction='credit' THEN value ELSE 0 END),0)
                FROM journal_accounts LEFT JOIN journal_lines ON name=account GROUP BY denomination""").fetchall()
        return {row[0]: tuple(map(int, row[1:])) for row in rows}
