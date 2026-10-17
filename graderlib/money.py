from decimal import Decimal


def assert_money(value, places=2):
    assert isinstance(value, Decimal), f"expected Decimal, got {type(value).__name__}"
    assert value.is_finite()
    assert value.as_tuple().exponent == -places
