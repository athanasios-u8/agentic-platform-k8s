from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

from bookstore_agents.common.config import get_settings


@contextmanager
def connection():
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def execute(sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def execute_many(sql: str, values: Iterable[Sequence[Any] | dict[str, Any]]) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, values)


def fetch_all(
    sql: str, params: Sequence[Any] | dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def fetch_one(
    sql: str, params: Sequence[Any] | dict[str, Any] | None = None
) -> dict[str, Any] | None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def fetch_value(sql: str, params: Sequence[Any] | dict[str, Any] | None = None) -> Any:
    row = fetch_one(sql, params)
    if not row:
        return None
    return next(iter(row.values()))
