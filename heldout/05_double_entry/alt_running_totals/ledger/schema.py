"""PostgreSQL schema: journal plus denormalised running totals (reviewer alternative)."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts(code text PRIMARY KEY, currency text NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(
    id bigserial PRIMARY KEY,
    memo text,
    reversal_of bigint REFERENCES transactions(id));
CREATE UNIQUE INDEX IF NOT EXISTS one_reversal_per_original ON transactions(reversal_of);
CREATE TABLE IF NOT EXISTS lines(
    txn bigint REFERENCES transactions(id),
    code text REFERENCES accounts(code),
    side text,
    amount bigint);
CREATE TABLE IF NOT EXISTS account_net(code text PRIMARY KEY REFERENCES accounts(code), net bigint NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS currency_totals(currency text PRIMARY KEY, debit bigint NOT NULL DEFAULT 0,
    credit bigint NOT NULL DEFAULT 0)
"""
