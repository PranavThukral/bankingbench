from pathlib import Path
from contextlib import contextmanager
import gc
from tempfile import TemporaryDirectory
import pytest
from hypothesis import given, strategies as st
from refunds.service import RefundService, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount


@contextmanager
def workspace():
    with TemporaryDirectory() as temp:
        try:
            yield Path(temp) / "db"
        finally:
            # SQLite connection cycles may await collection before Windows file removal.
            gc.collect()


def payment(path, authorized=100, captured=100):
    service = RefundService(path)
    pid = service.create_payment(authorized)
    service.capture(pid, captured)
    return service, pid


def test_cumulative_partials(tmp_path):
    s, p = payment(tmp_path / "db")
    a = s.refund(p, 60)
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 60)
    assert s.refunded_total(p) == 60
    b = s.refund(p, 40)
    assert a != b
    assert s.refunded_total(p) == 100


def test_capture_less_than_authorization(tmp_path):
    s, p = payment(tmp_path / "db", 100, 60)
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 61)
    assert s.refunded_total(p) == 0
    s.refund(p, 60)
    assert s.refunded_total(p) == 60


def test_valid_after_rejection(tmp_path):
    s, p = payment(tmp_path / "db")
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 101)
    assert s.refunded_total(p) == 0
    s.refund(p, 100)
    assert s.refunded_total(p) == 100


def test_invalid_and_uncaptured(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(PaymentNotCaptured):
        s.refund(p, 1)
    for amount in (0, -1, True, 1.5):
        with pytest.raises(InvalidAmount):
            s.refund(p, amount)
    assert s.refunded_total(p) == 0


def test_unknown_payment_id_raises_value_error(tmp_path):
    s = RefundService(tmp_path / "db")
    for call in (lambda: s.capture(99, 1), lambda: s.refund(99, 1), lambda: s.refunded_total(99)):
        with pytest.raises(ValueError):
            call()
    with pytest.raises(InvalidAmount):
        s.refund(99, 0)


def test_capture_once_and_within_authorization(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(InvalidAmount):
        s.capture(p, 101)
    s.capture(p, 60)
    for amount in (60, 50, 100):
        with pytest.raises(InvalidAmount):
            s.capture(p, amount)
    assert s.refund(p, 60) > 0
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 1)


@given(capture=st.integers(1, 100000), extra=st.integers(0, 100000),
       attempts=st.lists(st.integers(1, 100000), max_size=30))
def test_refund_sequence_matches_greedy_oracle(capture, extra, attempts):
    with workspace() as path:
        s, p = payment(path, capture + extra, capture)
        total, identifiers = 0, set()
        for amount in attempts:
            if amount <= capture - total:
                identifier = s.refund(p, amount)
                assert type(identifier) is int and identifier > 0 and identifier not in identifiers
                identifiers.add(identifier)
                total += amount
            else:
                with pytest.raises(RefundExceedsCaptured):
                    s.refund(p, amount)
            s = RefundService(path)
            assert s.refunded_total(p) == total <= capture
