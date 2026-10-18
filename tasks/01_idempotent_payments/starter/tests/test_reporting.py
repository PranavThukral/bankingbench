import os
from uuid import uuid4

from app.contracts import PaymentRequest
from app.gateway import ChargeResult
from app.reporting import format_amount, merchant_totals, render_merchant_report
from app.storage import PaymentStore


def test_format_amount_uses_currency_places():
    assert format_amount(1250, "CAD") == "12.50 CAD"
    assert format_amount(5, "USD") == "0.05 USD"
    assert format_amount(700, "JPY") == "700 JPY"
    assert format_amount(1234, "KWD") == "1.234 KWD"


def test_merchant_report_groups_by_currency_and_status():
    store = PaymentStore(os.environ["DATABASE_URL"])
    merchant = "report_" + uuid4().hex
    for amount, currency, status in [(1000, "CAD", "succeeded"), (250, "CAD", "succeeded"),
                                     (400, "CAD", "declined"), (900, "JPY", "succeeded")]:
        request = PaymentRequest(amount, currency, "token_report")
        store.save(merchant, request, ChargeResult(uuid4().hex, status))
    payments = store.list_for_merchant(merchant)
    assert merchant_totals(payments) == {
        "CAD": {"succeeded": [2, 1250], "declined": [1, 400]},
        "JPY": {"succeeded": [1, 900], "declined": [0, 0]},
    }
    text = render_merchant_report(merchant, payments)
    assert text.startswith(f"Merchant {merchant}: 4 payment(s)")
    assert "CAD succeeded    2  12.50 CAD" in text and "JPY succeeded    1  900 JPY" in text
