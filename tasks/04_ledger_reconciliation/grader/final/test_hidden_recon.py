from collections import Counter
from datetime import date, timedelta
from hypothesis import given, strategies as st

from recon.engine import reconcile, StatementLine as S, LedgerEntry as L

DAY = date(2026, 1, 5)


def pairs(result):
    return {(m.statement_ids, m.ledger_ids, m.rule) for m in result.matches}


def match(ss, ll, rule):
    return frozenset(ss), frozenset(ll), rule


def partition(statement, ledger, result):
    ss = [i for m in result.matches for i in m.statement_ids] + list(result.unmatched_statement)
    ll = [i for m in result.matches for i in m.ledger_ids] + list(result.unmatched_ledger)
    assert Counter(ss) == Counter(s.id for s in statement)
    assert Counter(ll) == Counter(e.id for e in ledger)
    statements, entries = {s.id: s for s in statement}, {e.id: e for e in ledger}
    for m in result.matches:
        left = sum(statements[i].amount_minor for i in m.statement_ids)
        right = sum(entries[i].amount_minor for i in m.ledger_ids)
        assert left == (-right if m.rule == "R3" else right)


def test_duplicate_statement_line_left_unmatched():
    statement = [S("b", DAY, 100, "r"), S("a", DAY, 100, "r")]
    ledger = [L("l", DAY, 100, "r")]
    result = reconcile(statement, ledger)
    assert pairs(result) == {match(["a"], ["l"], "R1")}
    assert result.unmatched_statement == {"b": "duplicate"}
    assert not result.unmatched_ledger
    partition(statement, ledger, result)


def test_split_all_lines():
    statement = [S("a", DAY, 40, "r"), S("b", DAY + timedelta(days=3), 60, "r")]
    result = reconcile(statement, [L("l", DAY, 100, "r")])
    assert pairs(result) == {match(["a", "b"], ["l"], "R2")}
    assert not result.unmatched_statement


def test_split_wrong_sum_and_no_subset():
    statement = [S("a", DAY, 40, "r"), S("b", DAY, 60, "r"), S("c", DAY, 1, "r")]
    result = reconcile(statement, [L("l", DAY, 100, "r")])
    assert not result.matches
    assert result.unmatched_statement == {"a": "no_match", "b": "no_match", "c": "no_match"}
    assert result.unmatched_ledger == {"l"}


def test_refund_kind_and_original_reference():
    statement = [S("s", DAY, -100, "original")]
    ledger = [L("payment", DAY, 100, "original"),
              L("refund", DAY + timedelta(days=30), 100, "other", "refund", "original")]
    result = reconcile(statement, ledger)
    assert pairs(result) == {match(["s"], ["refund"], "R3")}
    assert result.unmatched_ledger == {"payment"}
    partition(statement, ledger, result)


def test_tie_breaks_and_window():
    statement = [S("s", DAY, 100, "r"), S("outside", DAY, 101, "far")]
    ledger = [L("z", DAY + timedelta(days=1), 100, "r"),
              L("b", DAY - timedelta(days=1), 100, "r"),
              L("a", DAY - timedelta(days=1), 100, "r"),
              L("far", DAY + timedelta(days=4), 101, "far")]
    result = reconcile(statement, ledger)
    assert pairs(result) == {match(["s"], ["a"], "R1")}
    assert result.unmatched_statement == {"outside": "no_match"}
    assert result.unmatched_ledger == {"z", "b", "far"}
    boundary = reconcile([S("s", DAY, 100, "r")], [L("l", DAY + timedelta(days=3), 100, "r")])
    assert pairs(boundary) == {match(["s"], ["l"], "R1")}


@given(st.lists(st.tuples(st.sampled_from(["exact", "split", "refund", "duplicate", "noise"]),
                         st.integers(10, 1000000), st.integers(2, 4)), min_size=0, max_size=8))
def test_ground_truth_transforms(cases):
    statement, ledger, truth, reasons, unmatched = [], [], set(), {}, set()
    for i, (mode, amount, parts) in enumerate(cases):
        reference, lid, sid = f"r{i}", f"l{i}", f"s{i}"
        if mode == "refund":
            ledger.append(L(lid, DAY, amount, f"refund{i}", "refund", reference))
            statement.append(S(sid, DAY, -amount, reference))
            truth.add(match([sid], [lid], "R3"))
        elif mode == "split":
            ledger.append(L(lid, DAY, amount, reference))
            ids = []
            for j in range(parts):
                identifier = f"{sid}_{j}"
                value = amount // parts if j < parts - 1 else amount - (amount // parts) * (parts - 1)
                statement.append(S(identifier, DAY, value, reference))
                ids.append(identifier)
            truth.add(match(ids, [lid], "R2"))
        elif mode == "noise":
            statement.append(S(sid, DAY, amount, reference))
            ledger.append(L(lid, DAY, amount + 1, reference))
            reasons[sid] = "no_match"
            unmatched.add(lid)
        else:
            statement.append(S(sid, DAY, amount, reference))
            ledger.append(L(lid, DAY, amount, reference))
            truth.add(match([sid], [lid], "R1"))
            if mode == "duplicate":
                statement.append(S(sid + "z", DAY, amount, reference))
                reasons[sid + "z"] = "duplicate"
    before = (list(statement), list(ledger))
    result = reconcile(list(reversed(statement)), list(reversed(ledger)))
    assert pairs(result) == truth
    assert result.unmatched_statement == reasons
    assert result.unmatched_ledger == unmatched
    partition(statement, ledger, result)
    assert (statement, ledger) == before
