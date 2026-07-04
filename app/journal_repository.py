import sqlite3
from datetime import datetime, timedelta

from app.db_support import utc_now
from app.journal import JournalEntry


def list_journal_entries(
    connection: sqlite3.Connection,
    entity_type: str,
    entity_id: int,
    include_archived: bool = False,
) -> list[JournalEntry]:
    archived_clause = "" if include_archived else "AND archived_at = ''"
    rows = connection.execute(
        f"""
        SELECT * FROM journal_entries
        WHERE entity_type = ? AND entity_id = ? {archived_clause}
        ORDER BY created_at, id
        """,
        (entity_type, entity_id),
    ).fetchall()
    return [_to_journal_entry(row) for row in rows]


def get_journal_entry(
    connection: sqlite3.Connection, entry_id: int
) -> JournalEntry | None:
    row = connection.execute(
        "SELECT * FROM journal_entries WHERE id = ?", (entry_id,)
    ).fetchone()
    return _to_journal_entry(row) if row else None


def create_journal_entry(
    connection: sqlite3.Connection, entity_type: str, entity_id: int, body: str
) -> int:
    body = body.strip()
    if not body:
        raise ValueError("Journal entry text is required.")
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO journal_entries
            (entity_type, entity_id, body, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entity_type, entity_id, body, now, now),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_journal_entry(
    connection: sqlite3.Connection, entry_id: int, body: str
) -> None:
    body = body.strip()
    if not body:
        raise ValueError("Journal entry text is required.")
    entry = get_journal_entry(connection, entry_id)
    if entry is None:
        raise ValueError("Journal entry not found.")
    updated_at = utc_now()
    if updated_at == entry.created_at:
        updated_at = (datetime.fromisoformat(entry.created_at) + timedelta(seconds=1)).isoformat()
    connection.execute(
        "UPDATE journal_entries SET body = ?, updated_at = ? WHERE id = ?",
        (body, updated_at, entry_id),
    )
    connection.commit()


def archive_journal_entry(connection: sqlite3.Connection, entry_id: int) -> None:
    connection.execute(
        "UPDATE journal_entries SET archived_at = ? WHERE id = ?", (utc_now(), entry_id)
    )
    connection.commit()


def delete_journal_entry(connection: sqlite3.Connection, entry_id: int) -> None:
    connection.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    connection.commit()


def _to_journal_entry(row: sqlite3.Row) -> JournalEntry:
    return JournalEntry(**dict(row))
