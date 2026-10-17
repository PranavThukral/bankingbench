from batch.parser import parse, Payment
from batch.render import render


def fixture():
    return render([Payment("000000000123", 100, "reference")], batch_id="SYNTHETIC001")


def test_valid_lf():
    result = parse(fixture())
    assert result.accepted
    assert result.payments == [Payment("000000000123", 100, "reference")]
    assert result.errors == []


def test_count_mismatch():
    lines = fixture().splitlines()
    lines[-1] = b"T000002" + lines[-1][7:]
    result = parse(b"\n".join(lines) + b"\n")
    assert not result.accepted
    assert result.payments == []
    assert any(error.code == "count_mismatch" for error in result.errors)
