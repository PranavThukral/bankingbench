import os
from concurrent.futures import ThreadPoolExecutor
import threading
from uuid import uuid4
import pytest
from hypothesis import Phase, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from ledger.service import (LedgerService, Line, LedgerError, UnbalancedTransaction, InvalidAmount,
                            UnknownAccount, AlreadyReversed, CannotReverseReversal)


def setup(url):
    service = LedgerService(url)
    prefix = uuid4().hex
    accounts = {c: [f"{prefix}_{c}{i}" for i in range(4)] for c in ["CAD", "USD"]}
    for currency, codes in accounts.items():
        for code in codes:
            service.create_account(code, currency)
    return service, accounts


def test_cross_currency_cannot_net(database_url):
    s, accounts = setup(database_url)
    before = s.trial_balance()
    with pytest.raises(UnbalancedTransaction):
        s.post([Line(accounts["CAD"][0], "debit", 100), Line(accounts["USD"][0], "credit", 100)], "cross")
    assert s.trial_balance() == before
    assert s.balance(accounts["CAD"][0]) == s.balance(accounts["USD"][0]) == 0


def test_unknown_account_is_atomic(database_url):
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    before = s.trial_balance()
    with pytest.raises(UnknownAccount):
        s.post([Line(a, "debit", 100), Line(b, "credit", 100), Line("absent_account", "debit", 1)], "unknown")
    assert s.trial_balance() == before
    assert s.balance(a) == s.balance(b) == 0


def test_reverse_once(database_url):
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    totals = s.trial_balance()
    txn = s.post([Line(a, "debit", 100), Line(b, "credit", 100)], "posted")
    reversal = s.reverse(txn, "reverse")
    assert type(reversal) is int and reversal != txn
    assert s.balance(a) == s.balance(b) == 0
    assert s.trial_balance() == {c: (d + (200 if c == "CAD" else 0),
                                     cr + (200 if c == "CAD" else 0))
                                for c, (d, cr) in totals.items()}
    before = s.trial_balance()
    with pytest.raises(AlreadyReversed):
        s.reverse(txn, "again")
    assert s.trial_balance() == before
    with pytest.raises(CannotReverseReversal):
        s.reverse(reversal, "reverse reversal")
    assert s.trial_balance() == before


def test_multiple_currencies_and_persistence(database_url):
    s, accounts = setup(database_url)
    before = s.trial_balance()
    lines = [Line(accounts[c][i], side, 123) for c in accounts for i, side in enumerate(["debit", "credit"])]
    s.post(lines, "multi")
    restarted = LedgerService(database_url)
    after = restarted.trial_balance()
    for c in accounts:
        assert after[c] == (before[c][0] + 123, before[c][1] + 123)
        assert restarted.balance(accounts[c][0]) == 123
        assert restarted.balance(accounts[c][1]) == -123


@pytest.mark.parametrize("amount", [0, -1, True, 1.5])
def test_invalid_amount_unchanged(database_url, amount):
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    before = s.trial_balance()
    with pytest.raises(InvalidAmount):
        s.post([Line(a, "debit", amount), Line(b, "credit", 100)], "invalid")
    assert s.trial_balance() == before


def test_rejections_leave_no_trace(database_url):
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    before = s.trial_balance()
    for lines in [[], [Line(a, "debit", 1)], [Line(a, "debit", 100), Line(b, "credit", 99)]]:
        with pytest.raises(UnbalancedTransaction):
            s.post(lines, "invalid")
        assert s.trial_balance() == before
    with pytest.raises(LedgerError):
        s.reverse(-1, "absent")
    assert s.trial_balance() == before


@pytest.mark.parametrize("code,currency", [("", "CAD"), ("new", "XYZ"), ("new", "")])
def test_create_account_validation(database_url, code, currency):
    s, _ = setup(database_url)
    before = s.trial_balance()
    with pytest.raises(LedgerError):
        s.create_account(code, currency)
    assert s.trial_balance() == before
    with pytest.raises(UnknownAccount):
        s.balance(code)


def test_create_account_idempotence_and_currency_mismatch(database_url):
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    s.post([Line(a, "debit", 100), Line(b, "credit", 100)], "sale")
    before = s.trial_balance()
    s.create_account(a, "CAD")
    with pytest.raises(LedgerError):
        s.create_account(a, "USD")
    assert s.trial_balance() == before
    assert s.balance(a) == 100
    # Original currency must still balance against another CAD account.
    s.post([Line(a, "debit", 10), Line(b, "credit", 10)], "still CAD")
    assert s.balance(a) == 110


@pytest.mark.parametrize("lines,error", [
    ([Line("absent", "bad", 0)], UnbalancedTransaction),
    ([Line("absent", "debit", 0), Line("also_absent", "credit", 1)], InvalidAmount),
    ([Line("absent", "debit", True), Line("also_absent", "credit", 1)], InvalidAmount),
    ([Line("absent", "debit", 1), Line("also_absent", "credit", 2)], UnknownAccount),
])
def test_post_validation_priority(database_url, lines, error):
    s, _ = setup(database_url)
    before = s.trial_balance()
    with pytest.raises(error):
        s.post(lines, "invalid on several grounds")
    assert s.trial_balance() == before


def test_concurrent_reversals_once(database_url):
    # Each race (one transaction reversed by 8 callers at once) is probabilistic for a missing row lock, so
    # every round races several transactions: 3 rounds x 8 races give a miss probability below 1e-4.
    s, accounts = setup(database_url)
    a, b = accounts["CAD"][:2]
    services = [LedgerService(database_url) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for _ in range(3):
            before = s.trial_balance()
            txns = [s.post([Line(a, "debit", 100), Line(b, "credit", 100)], "concurrent sale") for _ in range(8)]
            barrier = threading.Barrier(8, timeout=15)

            def reverse_all(index):
                barrier.wait()
                results = []
                for txn in txns:
                    try:
                        results.append(services[index].reverse(txn, "concurrent undo"))
                    except AlreadyReversed:
                        results.append(None)
                return results

            results = list(pool.map(reverse_all, range(8)))
            for position, txn in enumerate(txns):
                ids = [value[position] for value in results if value[position] is not None]
                assert len(ids) == 1 and type(ids[0]) is int and ids[0] != txn
            assert s.balance(a) == s.balance(b) == 0
            assert s.trial_balance() == {c: (d + (200 * len(txns) if c == "CAD" else 0),
                                             cr + (200 * len(txns) if c == "CAD" else 0))
                                        for c, (d, cr) in before.items()}


class JournalMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.service, self.accounts = setup(os.environ["DATABASE_URL"])
        self.model = {a: 0 for codes in self.accounts.values() for a in codes}
        self.transactions = {}
        self.reversed = set()

    @rule(currency=st.sampled_from(["CAD", "USD"]), amount=st.integers(1, 100000), index=st.integers(0, 2))
    def post_valid(self, currency, amount, index):
        a, b = self.accounts[currency][index:index + 2]
        lines = [Line(a, "debit", amount), Line(b, "credit", amount)]
        txn = self.service.post(lines, "valid")
        self.transactions[txn] = (a, b, amount)
        self.model[a] += amount
        self.model[b] -= amount
        assert self.service.balance(a) == self.model[a]
        assert self.service.balance(b) == self.model[b]

    @rule(amount=st.integers(1, 100000))
    def post_invalid(self, amount):
        a, b = self.accounts["CAD"][:2]
        before = self.service.trial_balance()
        with pytest.raises(UnbalancedTransaction):
            self.service.post([Line(a, "debit", amount), Line(b, "credit", amount + 1)], "invalid")
        assert self.service.trial_balance() == before

    @precondition(lambda self: bool(set(self.transactions) - self.reversed))
    @rule(data=st.data())
    def reverse(self, data):
        txn = data.draw(st.sampled_from(sorted(set(self.transactions) - self.reversed)))
        a, b, amount = self.transactions[txn]
        self.service.reverse(txn, "reverse")
        self.reversed.add(txn)
        self.model[a] -= amount
        self.model[b] += amount
        assert self.service.balance(a) == self.model[a]
        assert self.service.balance(b) == self.model[b]

    @precondition(lambda self: bool(self.reversed))
    @rule(data=st.data())
    def reverse_again(self, data):
        txn = data.draw(st.sampled_from(sorted(self.reversed)))
        before = self.service.trial_balance()
        with pytest.raises(AlreadyReversed):
            self.service.reverse(txn, "again")
        assert self.service.trial_balance() == before

    @invariant()
    def balances_match_model(self):
        for currency, codes in self.accounts.items():
            assert sum(self.model[a] for a in codes) == 0, currency
        assert all(debit == credit for debit, credit in self.service.trial_balance().values())

    def teardown(self):
        assert {a: self.service.balance(a) for a in self.model} == self.model


TestJournal = JournalMachine.TestCase
TestJournal.settings = settings(max_examples=5, stateful_step_count=12, deadline=None,
                                derandomize=True, database=None, phases=[Phase.generate])
