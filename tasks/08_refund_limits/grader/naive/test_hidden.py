import pytest
from refunds.service import RefundService, RefundExceedsCaptured


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


