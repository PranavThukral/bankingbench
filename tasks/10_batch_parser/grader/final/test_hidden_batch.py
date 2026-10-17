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
