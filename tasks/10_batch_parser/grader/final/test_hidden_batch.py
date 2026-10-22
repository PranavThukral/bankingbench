from hypothesis import given, strategies as st
import pytest
from batch.parser import parse, Payment


def render(payments, crlf=False):
    header = "HSYNTHETIC00120260101CAD".ljust(80)
    details = [f"D{p.payee_account}{p.amount_minor:012d}{p.reference:<20}".ljust(80) for p in payments]
    total = sum(p.amount_minor for p in payments)
    hash_total = sum(int(p.payee_account[-8:]) for p in payments) % 10**10
    trailer = f"T{len(payments):06d}{total:015d}{hash_total:010d}".ljust(80)
    separator = b"\r\n" if crlf else b"\n"
    return separator.join(row.encode("ascii") for row in [header, *details, trailer]) + separator


def errors(result):
    return [(e.line_no, e.code) for e in result.errors]


def fixture():
    return [Payment("000000000123", 100, "reference")]


def test_crlf():
    result = parse(render(fixture(), crlf=True))
    assert result.accepted and result.errors == []
    assert result.payments == fixture()


def test_hash_total():
    rows = render(fixture()).splitlines()
    rows[-1] = rows[-1][:22] + b"0000000124" + rows[-1][32:]
    result = parse(b"\n".join(rows))
    assert not result.accepted and result.payments == []
    assert errors(result) == [(3, "hash_total_mismatch")]
    many = [Payment("999999999999", 1, "reference") for _ in range(101)]
    assert parse(render(many)).payments == many


def test_count_mismatch():
    rows = render(fixture()).splitlines()
    rows[-1] = b"T000002" + rows[-1][7:]
    result = parse(b"\n".join(rows))
    assert not result.accepted and result.payments == []
    assert errors(result) == [(3, "count_mismatch")]


def test_atomic_batch_rejection():
    payments = fixture() + [Payment("000000000456", 200, "second")]
    rows = render(payments).splitlines()
    rows[2] = rows[2][:1] + b"X" + rows[2][2:]
    result = parse(b"\n".join(rows))
    assert not result.accepted and result.payments == []
    assert errors(result) == [(3, "invalid_detail"), (4, "control_total_mismatch"), (4, "hash_total_mismatch")]


def test_multiple_errors_and_line_numbers():
    rows = render(fixture()).splitlines()
    rows[0] = rows[0][:13] + b"20260230" + rows[0][21:]
    rows[1] = rows[1][:13] + b"X" + rows[1][14:]
    result = parse(b"\n".join(rows))
    assert not result.accepted and not result.payments
    assert errors(result) == [(1, "invalid_header"), (2, "invalid_detail"),
                              (3, "control_total_mismatch"), (3, "hash_total_mismatch")]


@pytest.mark.parametrize("change,code", [(lambda row: row[:-1], "line_length"),
                                        (lambda row: b"\xff" + row[1:], "invalid_encoding"),
                                        (lambda row: b"X" + row[1:], "record_type")])
def test_invalid_records(change, code):
    rows = render(fixture()).splitlines()
    rows[1] = change(rows[1])
    result = parse(b"\n".join(rows))
    assert not result.accepted and not result.payments
    assert (2, code) in errors(result)


def test_missing_and_order():
    assert errors(parse(b"")) == [(1, "missing_header"), (1, "missing_trailer")]
    rows = render(fixture()).splitlines()
    result = parse(b"\n".join([rows[1], rows[0], rows[2]]))
    assert not result.accepted
    assert (1, "missing_header") in errors(result)
    assert (1, "record_order") in errors(result)
    assert (2, "record_order") in errors(result)


@pytest.mark.parametrize("row,start,end,value,code", [
    (0, 1, 13, b"synthetic001", "invalid_header"),
    (0, 1, 13, b"SYNTHETIC00!", "invalid_header"),
    (0, 13, 21, b"20260230", "invalid_header"),
    (0, 21, 24, b"XYZ", "invalid_header"),
    (0, 24, 25, b"X", "invalid_header"),
    (1, 1, 13, b"00000000012X", "invalid_detail"),
    (1, 13, 25, b"000000000000", "invalid_detail"),
    (1, 13, 25, b"00000000000X", "invalid_detail"),
    (1, 25, 45, b" " * 20, "invalid_detail"),
    (1, 45, 46, b"X", "invalid_detail"),
    (2, 1, 7, b"00000X", "invalid_trailer"),
    (2, 7, 22, b"00000000000000X", "invalid_trailer"),
    (2, 22, 32, b"000000000X", "invalid_trailer"),
    (2, 32, 33, b"X", "invalid_trailer"),
])
def test_field_formats(row, start, end, value, code):
    rows = render(fixture()).splitlines()
    rows[row] = rows[row][:start] + value + rows[row][end:]
    result = parse(b"\n".join(rows))
    expected = [(row + 1, code)]
    if row == 1:
        expected += [(3, "control_total_mismatch"), (3, "hash_total_mismatch")]
    assert not result.accepted and result.payments == []
    assert errors(result) == expected


@pytest.mark.parametrize("currency", ["CAD", "USD", "EUR", "GBP", "JPY", "KWD", "BHD"])
def test_supported_currencies_preserve_minor_units(currency):
    rows = render(fixture()).splitlines()
    rows[0] = rows[0][:21] + currency.encode() + rows[0][24:]
    result = parse(b"\n".join(rows))
    assert result.accepted and result.errors == [] and result.payments == fixture()


@pytest.mark.parametrize("final", [b"", b"\n", b"\r\n"])
def test_mixed_terminators_and_optional_final(final):
    rows = render(fixture()).splitlines()
    data = rows[0] + b"\r\n" + rows[1] + b"\n" + rows[2] + final
    result = parse(data)
    assert result.accepted and result.payments == fixture() and result.errors == []


@pytest.mark.parametrize("data,want", [
    (render(fixture()).replace(b"\n", b"\r"), [
        (1, "invalid_encoding"), (1, "missing_trailer")]),
    (render(fixture()).rstrip(b"\n") + b"\r", [(3, "invalid_encoding")]),
    (render(fixture()).replace(b"\n", b"\n", 1).splitlines()[0] + b"\n\n" +
     b"\n".join(render(fixture()).splitlines()[1:]), [(2, "line_length")]),
    (b"\n".join(render(fixture()).splitlines()[:2]), [
        (2, "missing_trailer"), (2, "record_order")]),
])
def test_terminator_blank_and_missing_trailer_errors(data, want):
    result = parse(data)
    assert not result.accepted and result.payments == []
    assert errors(result) == want


def test_reference_preserves_leading_spaces():
    payments = [Payment("000000000123", 100, "  reference")]
    result = parse(render(payments))
    assert result.accepted and result.errors == [] and result.payments == payments


@given(cases=st.lists(st.tuples(st.integers(0, 999999999999), st.integers(1, 10**8),
                              st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=1, max_size=20)),
                     min_size=1, max_size=20), crlf=st.booleans())
def test_roundtrip_and_single_digit_corruption(cases, crlf):
    payments = [Payment(f"{account:012d}", amount, ref) for account, amount, ref in cases]
    data = render(payments, crlf)
    result = parse(data)
    assert result.accepted and result.payments == payments and result.errors == []
    rows = data.split(b"\r\n" if crlf else b"\n")
    detail = bytearray(rows[1])
    detail[13] = ord("1") if detail[13] != ord("1") else ord("2")
    rows[1] = bytes(detail)
    corrupted = parse((b"\r\n" if crlf else b"\n").join(rows))
    assert not corrupted.accepted and corrupted.payments == []
    assert any(e.code == "control_total_mismatch" for e in corrupted.errors)
