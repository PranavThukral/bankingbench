"""Request and response construction shared by the HTTP adapter."""
from dataclasses import dataclass
import hashlib
import json

from fastapi.responses import JSONResponse

CURRENCIES = {"CAD": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}


@dataclass(frozen=True)
class PaymentRequest:
    amount_minor: int
    currency: str
    source_token: str

    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict):
            raise ValueError("object required")
        if set(data) != {"amount_minor", "currency", "source_token"}:
            raise ValueError("payment fields required")
        amount = data["amount_minor"]
        if type(amount) is not int or amount <= 0:
            raise ValueError("positive integer amount required")
        currency = data["currency"]
        if not isinstance(currency, str) or currency not in CURRENCIES:
            raise ValueError("unsupported currency")
        token = data["source_token"]
        if not isinstance(token, str) or not token:
            raise ValueError("source token required")
        return cls(amount, currency, token)

    def as_dict(self):
        return dict(amount_minor=self.amount_minor, currency=self.currency,
                    source_token=self.source_token)

    def fingerprint(self):
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


def error(status, code, message=None):
    return JSONResponse({"error": {"code": code, "message": message or code}}, status_code=status)


def headers(merchant, key):
    if not merchant:
        return error(400, "merchant_required")
    if key is None or not 1 <= len(key) <= 64:
        return error(400, "idempotency_key_required")
    return None


def receipt(payment_id, merchant, request, charge):
    if charge.status == "declined":
        return 402, {"error": {"code": "card_declined", "message": "Synthetic decline"}}
    return 201, {"payment_id": payment_id, "charge_id": charge.charge_id,
                 "status": charge.status, "merchant_id": merchant,
                 "amount_minor": request.amount_minor, "currency": request.currency}
