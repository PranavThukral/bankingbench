import hashlib
import os
import re
import secrets

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

README_HINT = "the README section 'Run it'"


def admin_url():
    return os.environ.get("PG_ADMIN_URL", "postgresql://postgres:bankingbench@postgres:5432/postgres")


def db_name(run_id):
    safe = "bb_" + re.sub(r"[^a-z0-9_]", "_", run_id.lower())
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


def create_run_db(run_id, admin=None):
    """Create a per-run database owned by a fresh non-superuser role; return (database, role, url).

    The candidate receives only this role's URL. The role cannot create roles or databases, and
    CONNECT to the run database is revoked from PUBLIC so concurrent runs cannot open each other's.
    """
    admin = admin or admin_url()
    name = db_name(run_id)
    role = name[:50] + "_u"
    password = secrets.token_urlsafe(18)
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION "
                             "NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(password)))
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 OWNER {}").format(
            sql.Identifier(name), sql.Identifier(role)))
        conn.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(name)))
    return name, role, make_conninfo(admin, dbname=name, user=role, password=password)


def drop_run_db(name, role, admin=None):
    admin = admin or admin_url()
    with psycopg.connect(admin, autocommit=True, connect_timeout=5) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))


def preflight(needs_postgres=True):
    """Return None when PostgreSQL is usable, else an actionable message."""
    if not needs_postgres:
        return None
    if "PG_ADMIN_URL" not in os.environ:
        return (f"PG_ADMIN_URL is not set and the default ({admin_url()}) is only valid inside the docker "
                f"compose network. Set PG_ADMIN_URL to a superuser connection URL, e.g. "
                f"postgresql://postgres@localhost:5432/postgres (see {README_HINT}).")
    try:
        with psycopg.connect(admin_url(), connect_timeout=5) as conn:
            conn.execute("SELECT 1")
    except psycopg.Error as exc:
        return (f"cannot connect to PostgreSQL at PG_ADMIN_URL ({type(exc).__name__}: "
                f"{str(exc).strip().splitlines()[0] if str(exc).strip() else ''}). Check that the server is running "
                f"and PG_ADMIN_URL is a superuser URL (see {README_HINT}).")
    return None
