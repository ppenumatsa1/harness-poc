"""Postgres access. Two roles: app_ro (reads) and app_rw (fixes table only)."""

from contextlib import contextmanager
from decimal import Decimal

import psycopg2
import psycopg2.extras

from . import config


@contextmanager
def connect(dsn: str):
    conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _clean(row: dict) -> dict:
    # JSON-friendly values for the model (timestamps -> ISO text, decimals -> float).
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        elif isinstance(v, Decimal):
            v = float(v)
        out[k] = v
    return out


def query(sql: str, params: tuple = (), *, dsn: str | None = None) -> list[dict]:
    with connect(dsn or config.DB_RO_DSN) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [_clean(r) for r in cur.fetchall()] if cur.description else []


def query_one(sql: str, params: tuple = (), *, dsn: str | None = None) -> dict | None:
    rows = query(sql, params, dsn=dsn)
    return rows[0] if rows else None


def write(sql: str, params: tuple = ()) -> dict | None:
    return query_one(sql, params, dsn=config.DB_RW_DSN)
