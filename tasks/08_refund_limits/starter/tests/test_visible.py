import pytest
from refunds.service import RefundService, RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount


def test_single_full_refund(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    assert s.refund(p, 100) > 0
    assert s.refunded_total(p) == 100


def test_over_refund_rejected(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 101)


def test_uncaptured_and_invalid_amounts(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(PaymentNotCaptured):
        s.refund(p, 1)
    with pytest.raises(InvalidAmount):
        s.refund(p, 0)


def test_partial_authorization_limit(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 50)
    assert s.refund(p, 40) > 0
    assert s.refunded_total(p) == 40


def test_rejected_capture(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(InvalidAmount):
        s.capture(p, 101)


def test_capture_once(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    s.capture(p, 100)
    with pytest.raises(InvalidAmount):
        s.capture(p, 50)
