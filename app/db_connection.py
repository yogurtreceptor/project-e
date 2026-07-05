"""Small PostgreSQL boundary for connections, parameters, and transactions."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

try:
    import psycopg
except ImportError:  # pragma: no cover - produces a useful startup error
    psycopg = None

from app.config import DATABASE_URL


class DatabaseUnavailable(RuntimeError):
    pass


class Row(dict):
    """Mapping row that also supports positional access for compact projections."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def row_factory(cursor):
    columns = [column.name for column in (cursor.description or ())]

    def make_row(values):
        return Row(zip(columns, values))

    return make_row


def _sql(statement: str) -> str:
    """Translate the application's driver-neutral qmark parameters."""
    return statement.replace("?", "%s")


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        row = self._cursor.fetchone()
        if row is None:
            raise RuntimeError("INSERT did not return an identity value")
        return row["id"]


class Connection:
    """Expose the deliberately small connection surface repositories use."""

    def __init__(self, connection):
        self._connection = connection

    def execute(self, statement: str, parameters: Iterable[Any] = ()) -> Cursor:
        sql = statement.strip()
        identity_tables = {
            "entities", "relationships", "entity_edit_history", "inference_batches",
            "inference_suggestions", "audit_events", "journal_entries", "entity_aliases",
            "reference_data_items", "taxonomies", "taxonomy_entries",
        }
        match = __import__("re").match(r"INSERT\s+INTO\s+(\w+)", sql, __import__("re").IGNORECASE)
        if match and match.group(1).lower() in identity_tables and "RETURNING" not in sql.upper() and "ON CONFLICT" not in sql.upper():
            sql += " RETURNING id"
        return Cursor(self._connection.execute(_sql(sql), parameters))

    def executemany(self, statement: str, parameters) -> Cursor:
        cursor = self._connection.cursor()
        cursor.executemany(_sql(statement), parameters)
        return Cursor(cursor)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, *args):
        return self._connection.__exit__(*args)


def connect(database_url: str | None = None, *, autocommit: bool = False) -> Connection:
    if psycopg is None:
        raise DatabaseUnavailable(
            "psycopg is not installed; run 'python3 -m pip install -r requirements.txt'."
        )
    return Connection(
        psycopg.connect(resolve_database_url(database_url), autocommit=autocommit, row_factory=row_factory)
    )


def resolve_database_url(value=None) -> str:
    """Map path-shaped test identifiers to isolated PostgreSQL databases."""
    if value is None or (
        isinstance(value, str) and (
            value.startswith(("postgresql://", "postgres://")) or "=" in value
        )
    ):
        return value or DATABASE_URL
    name = "project_e_test_" + hashlib.sha1(str(Path(value)).encode()).hexdigest()[:16]
    info = psycopg.conninfo.conninfo_to_dict(DATABASE_URL)
    info["dbname"] = "postgres"
    with psycopg.connect(**info, autocommit=True) as admin:
        exists = admin.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (name,)
        ).fetchone()
        if not exists:
            admin.execute(
                psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(name))
            )
    info["dbname"] = name
    return psycopg.conninfo.make_conninfo(**info)


@contextmanager
def transaction(database_url: str | None = None):
    with connect(database_url) as connection:
        yield connection
