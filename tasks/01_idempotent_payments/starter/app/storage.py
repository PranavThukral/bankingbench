"""Persistent payment receipts. Each operation owns its connection."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import psycopg

from app.contracts import receipt


@dataclass(frozen=True)
class StoredPayment:
    payment_id: str
    merchant_id: str
    amount_minor: int
    currency: str
    source_token: str
    charge_id: str
    status: str
    created_at: datetime


class PaymentStore:
    def __init__(self, database_url):
        self.database_url = database_url
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS payments (
                payment_id text PRIMARY KEY,
                merchant_id text NOT NULL,
                amount_minor bigint NOT NULL,
                currency text NOT NULL,
                source_token text NOT NULL,
                charge_id text NOT NULL,
                status text NOT NULL,
                created_at timestamptz NOT NULL
            )""")

    def connect(self):
        return psycopg.connect(self.database_url)

    def save(self, merchant, request, charge, conn=None):
        payment = StoredPayment(str(uuid4()), merchant, request.amount_minor, request.currency,
                                request.source_token, charge.charge_id, charge.status,
                                datetime.now(timezone.utc))
        if conn is None:
            with self.connect() as owned:
                self.insert(owned, payment)
        else:
            self.insert(conn, payment)
        return receipt(payment.payment_id, merchant, request, charge)

    @staticmethod
    def insert(conn, payment):
        conn.execute("""INSERT INTO payments VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (payment.payment_id, payment.merchant_id, payment.amount_minor,
                      payment.currency, payment.source_token, payment.charge_id,
                      payment.status, payment.created_at))

    def list_for_merchant(self, merchant):
        with self.connect() as conn:
            rows = conn.execute("""SELECT payment_id,merchant_id,amount_minor,currency,
                source_token,charge_id,status,created_at FROM payments
                WHERE merchant_id=%s ORDER BY created_at,payment_id""", (merchant,)).fetchall()
        return [StoredPayment(*row) for row in rows]

    def get(self, payment_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM payments WHERE payment_id=%s", (payment_id,)).fetchone()
        return StoredPayment(*row) if row else None
