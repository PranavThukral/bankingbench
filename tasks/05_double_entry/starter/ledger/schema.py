"""PostgreSQL schema for the synthetic journal."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(code text PRIMARY KEY, currency text NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(id bigserial PRIMARY KEY, memo text);
CREATE TABLE IF NOT EXISTS lines(
    txn bigint REFERENCES transactions(id),
    code text REFERENCES accounts(code),
    side text,
    amount bigint)
"""
