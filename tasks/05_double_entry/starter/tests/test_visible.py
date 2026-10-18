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


def test_account_creation_is_idempotent():
    s, a, b = accounts()
    s.create_account(a, "CAD")
    s.create_account(b, "CAD")
    assert s.balance(a) == s.balance(b) == 0


def test_reverse_restores_balances():
    s, a, b = accounts()
    txn = s.post([Line(a, "debit", 70), Line(b, "credit", 70)], "synthetic")
    reversal = s.reverse(txn, "undo")
    assert reversal != txn
    assert (s.balance(a), s.balance(b)) == (0, 0)
