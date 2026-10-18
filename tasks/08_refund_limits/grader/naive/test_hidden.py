import pytest
from refunds.service import RefundService, RefundExceedsCaptured, PaymentNotCaptured


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


def test_ticket_worked_example(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(10000)
    s.capture(p, 6000)
    assert s.refund(p, 4000) > 0
    assert s.refunded_total(p) == 4000
    with pytest.raises(RefundExceedsCaptured):
        s.refund(p, 2500)
    assert s.refunded_total(p) == 4000


def test_refund_before_capture_rejected(tmp_path):
    s = RefundService(tmp_path / "db")
    p = s.create_payment(100)
    with pytest.raises(PaymentNotCaptured):
        s.refund(p, 1)
