"""Focused persistence operations for Inbox item lifecycle changes."""

import sqlite3

from app.db_support import utc_now


def record_action(
    connection: sqlite3.Connection,
    item_id: int,
    action: str,
    previous_state: str,
    resulting_state: str,
    next_attention_at: str,
    note: str,
    acted_at: str,
) -> None:
    connection.execute(
        """INSERT INTO inbox_item_actions
           (inbox_item_id, action, previous_state, resulting_state,
            next_attention_at, note, acted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            item_id,
            action,
            previous_state,
            resulting_state,
            next_attention_at,
            note,
            acted_at,
        ),
    )


def transition_item(
    connection: sqlite3.Connection,
    item_id: int,
    previous_state: str,
    resulting_state: str,
    action: str,
    next_attention_at: str,
    note: str,
    acted_at: str,
) -> None:
    connection.execute(
        """UPDATE inbox_items
           SET state=?, next_attention_at=?, acted_at=?, action_note=?
           WHERE id=?""",
        (resulting_state, next_attention_at, acted_at, note, item_id),
    )
    record_action(
        connection,
        item_id,
        action,
        previous_state,
        resulting_state,
        next_attention_at,
        note,
        acted_at,
    )


def resolve_items(
    connection: sqlite3.Connection,
    note: str,
    action: str,
    clause: str,
    parameters: tuple[object, ...],
) -> None:
    rows = connection.execute(
        "SELECT id, state FROM inbox_items WHERE "
        + clause
        + " AND state IN ('active', 'snoozed')",
        parameters,
    ).fetchall()
    now = utc_now()
    for row in rows:
        transition_item(
            connection,
            int(row["id"]),
            row["state"],
            "resolved",
            action,
            "",
            note,
            now,
        )


def resolve_source_items(
    connection: sqlite3.Connection, source_kind: str, source_id: int
) -> None:
    resolve_items(
        connection,
        "source no longer due",
        "source_lifecycle",
        "source_kind=? AND source_id=?",
        (source_kind, source_id),
    )


def resolve_source_items_after_occurrence(
    connection: sqlite3.Connection,
    source_kind: str,
    source_id: int,
    occurrence_key: str,
) -> None:
    """Resolve deliveries moved to a successor recurring series."""
    resolve_items(
        connection,
        "recurring series superseded",
        "series_split",
        "source_kind=? AND source_id=? AND occurrence_key>=?",
        (source_kind, source_id, occurrence_key),
    )


def resolve_source_items_for_occurrence(
    connection: sqlite3.Connection,
    source_kind: str,
    source_id: int,
    occurrence_key: str,
    *,
    note: str = "occurrence no longer due",
) -> None:
    """Resolve attention for one cancelled or rescheduled occurrence."""
    resolve_items(
        connection,
        note,
        "occurrence_changed",
        "source_kind=? AND source_id=? AND occurrence_key=?",
        (source_kind, source_id, occurrence_key),
    )
