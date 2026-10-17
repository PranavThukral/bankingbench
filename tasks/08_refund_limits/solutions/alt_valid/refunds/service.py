import json
import sqlite3
from contextlib import contextmanager
from refunds.models import RefundExceedsCaptured, PaymentNotCaptured, InvalidAmount, validate_amount

__all__ = ["RefundService", "RefundExceedsCaptured", "PaymentNotCaptured", "InvalidAmount"]


@contextmanager
def journal(filename):
    connection = sqlite3.connect(filename)
    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
    finally:
        connection.close()


def append(connection, tag, owner, payload):
    inserted = connection.execute("INSERT INTO event_log(tag,owner,payload) VALUES (?,?,?)",
                                  [tag, owner, json.dumps(payload)])
    return inserted.lastrowid


def reconstruct(connection, number):
    state = {"ceiling": 0, "settled": None, "returned": 0}
    history = connection.execute("SELECT tag,payload FROM event_log WHERE number=? OR owner=? ORDER BY number",
                                 [number, number])
    for tag, payload in history:
        value = json.loads(payload)["minor"]
        if tag == "approval":
            state["ceiling"] = value
        elif tag == "settlement":
            state["settled"] = value
        elif tag == "credit":
            state["returned"] += value
    return state


class RefundService:
    def __init__(self, db_path):
        self.filename = str(db_path)
        with journal(self.filename) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS event_log(number INTEGER PRIMARY KEY, tag TEXT, owner INTEGER, payload TEXT)")

    def create_payment(self, authorized_minor):
        validate_amount(authorized_minor)
        with journal(self.filename) as connection:
            return append(connection, "approval", None, {"minor": authorized_minor})

    def capture(self, id, amount_minor):
        validate_amount(amount_minor)
        with journal(self.filename) as connection:
            state = reconstruct(connection, id)
            if state["settled"] is not None or amount_minor > state["ceiling"]:
                raise InvalidAmount("capture not permitted")
            append(connection, "settlement", id, {"minor": amount_minor})

    def refund(self, id, amount_minor):
        validate_amount(amount_minor)
        with journal(self.filename) as connection:
            state = reconstruct(connection, id)
            if state["settled"] is None:
                raise PaymentNotCaptured(id)
            if state["returned"] + amount_minor > state["settled"]:
                raise RefundExceedsCaptured(id)
            return append(connection, "credit", id, {"minor": amount_minor})

    def refunded_total(self, id):
        with journal(self.filename) as connection:
            return reconstruct(connection, id)["returned"]
