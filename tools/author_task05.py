from author_common import task_meta, write

b = task_meta("05_double_entry", "Enforce an atomic double-entry journal", "ledger", [
    "ledger.service:LedgerService, Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount, AlreadyReversed, CannotReverseReversal"], [
    ("wrong_cross_currency_sum", "Balances the total across currencies instead of each currency.", ["test_cross_currency_cannot_net"]),
    ("wrong_non_atomic", "Commits individual lines before all account validation completes.", ["test_unknown_account_is_atomic"]),
    ("wrong_double_reverse", "Allows the same original transaction to be reversed twice.", ["test_reverse_once"]),
], "Set-based JSON recordset validation and INSERT SELECT reversal, with an independent journal schema.", requires=["postgres"], difficulty="hard", terms=["jsonb_to_recordset"])

write(b / "PROBLEM.md", '''
# Ticket: enforce the journal invariant

`ledger.service.LedgerService(database_url)` operates a synthetic PostgreSQL ledger.
Expose frozen `Line(account_code: str, side: "debit"|"credit", amount_minor: int)` and:
`create_account(code,currency)`, `post(lines: list[Line],memo: str)->int`,
`reverse(txn_id:int,memo:str)->int`, `balance(account_code)->int`,
`trial_balance()->dict[str,tuple[int,int]]`.

Money uses integer minor units. Currencies: CAD/USD/EUR/GBP=2 dp, JPY=0, KWD/BHD=3;
no exchange or cross-currency netting. Errors derive from LedgerError:
UnbalancedTransaction, InvalidAmount, UnknownAccount, AlreadyReversed, CannotReverseReversal.

- A post has at least two lines (otherwise UnbalancedTransaction). Each amount is a positive
  int, never bool (otherwise InvalidAmount). Side must be debit or credit (LedgerError).
- All accounts must exist (UnknownAccount). For EACH currency independently, sum of debits
  equals sum of credits (otherwise UnbalancedTransaction).
- Posting is atomic. Every rejected operation leaves balances and trial balance unchanged,
  including a missing account after other valid lines. Inputs are not mutated.
- Balance is debits minus credits. trial_balance keys are all currencies of created accounts,
  values are `(total_debits,total_credits)` across all posted lines, including reversal lines.
  A currency without postings has `(0,0)`. balance of an unknown account raises UnknownAccount.
- reverse creates a new transaction, with every side swapped, links it to the original and
  returns its distinct id. An original can be reversed at most once (AlreadyReversed).
  A reversal itself cannot be reversed (CannotReverseReversal). An unknown txn raises LedgerError.
  Reversal counts as real debit/credit turnover; it does not erase original lines.
- State survives constructing a new service. Re-creating an account with the same code and
  currency is idempotent; different currency, empty code or unsupported currency -> LedgerError.
- Validation priority: line count, amount/side, accounts, balancing. On reversing a reversal,
  CannotReverseReversal takes priority. Memo is arbitrary synthetic text.

The service may create its own tables; tests observe only the declared methods. Run
`python -m pytest tests -q` from starter with DATABASE_URL pointing at a disposable database.
''')

write(b / "starter/ledger/models.py", '''
"""Public journal records and domain failures."""
from dataclasses import dataclass


class LedgerError(Exception):
    """Base error for rejected journal operations."""


class UnbalancedTransaction(LedgerError):
    """A transaction does not balance or has fewer than two lines."""


class InvalidAmount(LedgerError):
    """Only positive integer minor units are accepted."""


class UnknownAccount(LedgerError):
    """A journal line refers to an account that has not been created."""


class AlreadyReversed(LedgerError):
    """An original transaction already has a reversal."""


class CannotReverseReversal(LedgerError):
    """A reversal is not itself reversible."""


@dataclass(frozen=True)
class Line:
    account_code: str
    side: str
    amount_minor: int

    def as_dict(self):
        return {"account_code": self.account_code, "side": self.side, "amount_minor": self.amount_minor}

    @classmethod
    def from_dict(cls, row):
        return cls(row["account_code"], row["side"], row["amount_minor"])


CURRENCIES = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


def validate_lines(lines):
    if len(lines) < 2:
        raise UnbalancedTransaction("at least two lines required")
    for line in lines:
        if type(line.amount_minor) is not int or line.amount_minor <= 0:
            raise InvalidAmount("positive integer required")
        if line.side not in {"debit", "credit"}:
            raise LedgerError("invalid side")
''')

reference = '''
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
'''
write(b / "solutions/reference/ledger/service.py", reference)
write(b / "starter/ledger/service.py", reference.replace('''        if any(totals.values()):
            raise UnbalancedTransaction("per-currency sums must balance")
''', ''))
write(b / "solutions/wrong_cross_currency_sum/ledger/service.py", reference.replace('totals[account[0]]', 'totals["all"]'))
write(b / "solutions/wrong_double_reverse/ledger/service.py", reference.replace('''            if row[1] is not None:
                raise AlreadyReversed(txn_id)
''', ''))
non_atomic = '''    def post(self, lines, memo):
        validate_lines(lines)
        with self.connect() as conn:
            txn = conn.execute("INSERT INTO transactions(memo) VALUES (%s) RETURNING id", (memo,)).fetchone()[0]
            conn.commit()
            totals = defaultdict(int)
            for line in lines:
                account = conn.execute("SELECT currency FROM accounts WHERE code=%s", (line.account_code,)).fetchone()
                if account is None:
                    raise UnknownAccount(line.account_code)
                totals[account[0]] += line.amount_minor * (1 if line.side == "debit" else -1)
                conn.execute("INSERT INTO lines VALUES (%s,%s,%s,%s)",
                             (txn, line.account_code, line.side, line.amount_minor))
                conn.commit()
            if any(totals.values()):
                raise UnbalancedTransaction("per-currency sums must balance")
            return txn

'''
first, last = reference.index('    def post('), reference.index('    def reverse(')
write(b / "solutions/wrong_non_atomic/ledger/service.py", reference[:first] + non_atomic + reference[last:])

write(b / "solutions/alt_valid/ledger/service.py", '''
import json
import psycopg
from ledger.models import (Line, LedgerError, UnbalancedTransaction, InvalidAmount, UnknownAccount,
                           AlreadyReversed, CannotReverseReversal, CURRENCIES, validate_lines)  # noqa: F401

RECORDS = "jsonb_to_recordset(%s::jsonb) AS x(account_code text, side text, amount_minor bigint)"


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
''')

write(b / "starter/ledger/preview.py", '''
"""JSON adapter for a synthetic journal batch."""
import argparse
import json
import os
from pathlib import Path
from ledger.models import Line
from ledger.service import LedgerService


def load_batch(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("accounts", []), [Line.from_dict(row) for row in data["lines"]], data.get("memo", "")


def book(service, accounts, lines, memo):
    for account in accounts:
        service.create_account(account["code"], account["currency"])
    transaction = service.post(lines, memo)
    return {
        "transaction_id": transaction,
        "balances": {line.account_code: service.balance(line.account_code) for line in lines},
        "trial_balance": service.trial_balance(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Book a synthetic journal JSON batch")
    parser.add_argument("batch", type=Path)
    args = parser.parse_args(argv)
    service = LedgerService(os.environ["DATABASE_URL"])
    print(json.dumps(book(service, *load_batch(args.batch)), indent=2))


if __name__ == "__main__":
    main()
''')
write(b / "starter/tests/test_visible.py", '''
import os
from uuid import uuid4
import pytest
from ledger.service import LedgerService, Line, UnbalancedTransaction


def accounts():
    s = LedgerService(os.environ["DATABASE_URL"])
    a, b = "a" + uuid4().hex, "b" + uuid4().hex
    s.create_account(a, "CAD")
    s.create_account(b, "CAD")
    return s, a, b


def test_balanced_post():
    s, a, b = accounts()
    assert isinstance(s.post([Line(a, "debit", 100), Line(b, "credit", 100)], "synthetic"), int)
    assert (s.balance(a), s.balance(b)) == (100, -100)


def test_unbalanced_rejected():
    s, a, b = accounts()
    with pytest.raises(UnbalancedTransaction):
        s.post([Line(a, "debit", 100), Line(b, "credit", 90)], "unbalanced")
''')
write(b / "grader/naive/test_hidden.py", (b / "starter/tests/test_visible.py").read_text(encoding="utf-8"))
write(b / "NOTES.md", '''
# Private draft — journal reviewer notes

Rowwise reference validation occurs within one transaction. The independent valid alternative
checks a JSON recordset using SQL aggregation and reverses by INSERT SELECT. Three wrong
implementations isolate cross-currency netting, per-line commit, and missing reversal lifecycle checks.

## Blind review
Author self-review from ticket and starter. Ambiguities: trial_balance key/value meaning,
invalid side/count errors, re-created accounts, unknown transaction errors, and reversal turnover.
All are specified in PROBLEM.md. Predictions: CAD debit100/USD credit100 -> UnbalancedTransaction;
unknown third account -> UnknownAccount with unchanged balances; reverse a reversal ->
CannotReverseReversal, no change. No unresolved graded ambiguity. Independent review remains owed.
''')
