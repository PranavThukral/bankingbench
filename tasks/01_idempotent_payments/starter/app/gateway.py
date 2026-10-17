"""External charging boundary for a synthetic network."""
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Protocol
from uuid import uuid4


@dataclass(frozen=True)
class ChargeResult:
    charge_id: str
    status: Literal["succeeded", "declined"]


class Gateway(Protocol):
    def charge(self, merchant_id: str, amount_minor: int, currency: str,
               source_token: str) -> ChargeResult:
        """Return a network receipt; a decline is a normal result."""
        ...


@dataclass(frozen=True)
class ChargeCall:
    merchant_id: str
    amount_minor: int
    currency: str
    source_token: str


class FakeGateway:
    """Inert local development gateway, with a thread-safe call history."""

    def __init__(self):
        self._calls: list[ChargeCall] = []
        self._lock = Lock()

    @property
    def calls(self) -> tuple[ChargeCall, ...]:
        with self._lock:
            return tuple(self._calls)

    def charge(self, merchant_id, amount_minor, currency, source_token):
        call = ChargeCall(merchant_id, amount_minor, currency, source_token)
        with self._lock:
            self._calls.append(call)
        status = "declined" if source_token.startswith("decline_") else "succeeded"
        return ChargeResult(str(uuid4()), status)
