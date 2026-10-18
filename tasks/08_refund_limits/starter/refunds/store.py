"""SQLite access for payments and refunds. Each call receives the caller's connection."""
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentRow:
    id: int
    authorized: int
    captured: int | None
    refunded: int


def connect(path):
    return sqlite3.connect(str(path), timeout=30)


def initialize(conn):
    conn.executescript("""CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY, authorized INTEGER, captured INTEGER, refunded INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS refunds(id INTEGER PRIMARY KEY, payment INTEGER, amount INTEGER)""")


def insert_payment(conn, authorized_minor):
    return conn.execute("INSERT INTO payments(authorized) VALUES (?)", (authorized_minor,)).lastrowid


def get_payment(conn, payment_id):
    row = conn.execute("SELECT id,authorized,captured,refunded FROM payments WHERE id=?", (payment_id,)).fetchone()
    return PaymentRow(*row) if row else None


def set_captured(conn, payment_id, amount_minor):
    conn.execute("UPDATE payments SET captured=? WHERE id=?", (amount_minor, payment_id))


def add_refund(conn, payment_id, amount_minor):
    """Record a refund row and add it to the payment's refunded counter."""
    refund_id = conn.execute("INSERT INTO refunds(payment,amount) VALUES (?,?)", (payment_id, amount_minor)).lastrowid
    conn.execute("UPDATE payments SET refunded=refunded+? WHERE id=?", (amount_minor, payment_id))
    return refund_id


def list_refunds(conn, payment_id):
    return conn.execute("SELECT id,amount FROM refunds WHERE payment=? ORDER BY id", (payment_id,)).fetchall()
