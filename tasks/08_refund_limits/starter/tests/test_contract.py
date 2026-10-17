import pytest
from refunds.models import Payment, RefundRequest, InvalidAmount, validate_amount


def test_request_transport():
    row = {"payment_id": 1, "amount_minor": 100}
    assert RefundRequest.from_dict(row).as_dict() == row


def test_payment_transport():
    payment = Payment(1, 100, 60)
    assert payment.as_dict() == {"id": 1, "authorized_minor": 100, "captured_minor": 60}


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "100", None])
def test_amount_validation(value):
    with pytest.raises(InvalidAmount):
        validate_amount(value)


def test_valid_amount():
    assert validate_amount(100) is None
