import hashlib
import os
import re

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo


def admin_url():
    return os.environ.get("PG_ADMIN_URL", "postgresql://postgres:bcp@postgres:5432/postgres")


def db_name(run_id):
    safe = "bcp_" + re.sub(r"[^a-z0-9_]", "_", run_id.lower())
    return safe[:46] + "_" + hashlib.sha256(run_id.encode()).hexdigest()[:12]


def create_db(name):
    with psycopg.connect(admin_url(), autocommit=True, connect_timeout=5) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
    return make_conninfo(admin_url(), dbname=name)


def drop_db(name):
    with psycopg.connect(admin_url(), autocommit=True, connect_timeout=5) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def version():
    try:
        with psycopg.connect(admin_url(), connect_timeout=3) as conn:
            return conn.execute("SHOW server_version").fetchone()[0]
    except psycopg.Error as exc:
        return f"unavailable: {type(exc).__name__}"
