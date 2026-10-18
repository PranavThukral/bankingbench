from datetime import date
from batch.parser import parse, Payment


def render(payments: list[Payment], batch_id="SYNTHETIC001", created=date(2026, 1, 1), currency="CAD"):
    rows = [f"H{batch_id}{created:%Y%m%d}{currency}".ljust(80)]
    for payment in payments:
        rows.append(f"D{payment.payee_account}{payment.amount_minor:012d}{payment.reference:<20}".ljust(80))
    total = sum(payment.amount_minor for payment in payments)
    hash_total = sum(int(payment.payee_account[-8:]) for payment in payments) % 10**10
    rows.append(f"T{len(payments):06d}{total:015d}{hash_total:010d}".ljust(80))
    return "\n".join(rows).encode("ascii") + b"\n"


def test_valid_lf():
    result = parse(render([Payment("000000000123", 100, "reference")]))
    assert result.accepted
    assert result.payments == [Payment("000000000123", 100, "reference")]
    assert result.errors == []


def test_ticket_worked_example():
    data = render([Payment("000000012345", 10000, "INV-2026-001"), Payment("000000067890", 2550, "INV-2026-002")],
                  batch_id="SYNTHBATCH01", created=date(2026, 1, 15))
    assert data.splitlines()[3] == b"T0000020000000000125500000080235".ljust(80)
    result = parse(data)
    assert result.accepted
    assert [p.amount_minor for p in result.payments] == [10000, 2550]
    assert result.errors == []


def test_count_mismatch():
    lines = render([Payment("000000000123", 100, "reference")]).splitlines()
    lines[-1] = b"T000002" + lines[-1][7:]
    result = parse(b"\n".join(lines) + b"\n")
    assert not result.accepted
    assert result.payments == []
    assert any(error.code == "count_mismatch" for error in result.errors)
