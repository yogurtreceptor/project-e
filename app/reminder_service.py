"""Deterministic local reminder resolution and durable Inbox delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import sqlite3
from urllib.parse import urlencode

from app.db_support import utc_now
from app.defaults import DEFAULT_REMINDER_TIMINGS, MAX_EVENT_REMINDERS
from app.entity_repository import get_entity
from app.entities import DEFINITIONS_BY_TYPE
from app.event_service import get_event
from app.calendar_subscription_service import get_external_projection_event
from app.inbox_repository import (
    record_action as _record_action,
    resolve_items as _resolve_items,
    resolve_source_items,
    resolve_source_items_after_occurrence,
    resolve_source_items_for_occurrence,
    transition_item as _transition_item,
)
from app.temporal_occurrences import TemporalOccurrence, reminder_occurrences

DEFAULT_TIMINGS = {
    source_kind: list(timings)
    for source_kind, timings in DEFAULT_REMINDER_TIMINGS.items()
}
MAX_REMINDERS = MAX_EVENT_REMINDERS

@dataclass(frozen=True)
class InboxItem:
    id: int; delivery_key: str; source_kind: str; source_id: int; occurrence_key: str
    reason: str; timing: str; title: str; due_at: str; delivered_at: str; state: str
    next_attention_at: str; attention_expires_at: str; acted_at: str; action_note: str


@dataclass(frozen=True)
class InboxAction:
    action: str; previous_state: str; resulting_state: str; next_attention_at: str
    note: str; acted_at: str


def set_policy(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str, timings: list[str]) -> None:
    _validate_timings(timings, maximum=MAX_REMINDERS)
    connection.execute("""INSERT INTO reminder_policies (context_kind, context_id, source_kind, timings_json, updated_at)
        VALUES (?, ?, ?, ?, ?) ON CONFLICT(context_kind, context_id, source_kind)
        DO UPDATE SET timings_json=excluded.timings_json, updated_at=excluded.updated_at""",
        (context_kind, context_id, source_kind, json.dumps(timings), utc_now()))
    _reconcile_context_deliveries(connection, context_kind, context_id, source_kind)
    connection.commit()


def get_policy(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str) -> list[str] | None:
    """Return an explicitly configured policy, or None when it inherits."""
    row = connection.execute(
        "SELECT timings_json FROM reminder_policies WHERE context_kind=? AND context_id=? AND source_kind=?",
        (context_kind, context_id, source_kind),
    ).fetchone()
    return json.loads(row[0]) if row is not None else None


def clear_policy(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str) -> None:
    """Restore a contextual policy to its inherited default."""
    connection.execute(
        "DELETE FROM reminder_policies WHERE context_kind=? AND context_id=? AND source_kind=?",
        (context_kind, context_id, source_kind),
    )
    _reconcile_context_deliveries(connection, context_kind, context_id, source_kind)
    connection.commit()


def disable_policy(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str) -> None:
    """Explicitly suppress every reminder from one policy context.

    An empty timing list is distinct from a missing policy row: the former is an
    intentional local opt-out, while the latter inherits the source default.
    """
    set_policy(connection, context_kind, context_id, source_kind, [])


def set_override(connection: sqlite3.Connection, source_kind: str, source_id: int, *, mode: str = "default", custom_timings: list[str] | None = None, suppressed_timings: list[str] | None = None, occurrence_key: str = "") -> None:
    if mode not in {"default", "custom", "disabled"}: raise ValueError("Reminder override mode is invalid.")
    custom_timings, suppressed_timings = custom_timings or [], suppressed_timings or []
    _validate_timings(custom_timings, maximum=MAX_REMINDERS)
    _validate_timings(suppressed_timings, maximum=MAX_REMINDERS)
    if source_kind == "event" and mode != "disabled":
        context = _context_for_source(connection, source_kind, source_id)
        inherited = _context_timings(connection, context, source_kind) if context else []
        effective = (set(inherited) - set(suppressed_timings)) | set(custom_timings)
        if len(effective) > MAX_REMINDERS:
            raise ValueError(f"An Event can have at most {MAX_REMINDERS} reminders.")
    connection.execute("""INSERT INTO reminder_overrides (source_kind, source_id, occurrence_key, mode, custom_timings_json, suppressed_timings_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(source_kind, source_id, occurrence_key)
        DO UPDATE SET mode=excluded.mode, custom_timings_json=excluded.custom_timings_json,
        suppressed_timings_json=excluded.suppressed_timings_json, updated_at=excluded.updated_at""",
        (source_kind, source_id, occurrence_key, mode, json.dumps(custom_timings), json.dumps(suppressed_timings), utc_now()))
    _reconcile_source_deliveries(connection, source_kind, source_id, occurrence_key=occurrence_key)
    connection.commit()


def get_override(connection: sqlite3.Connection, source_kind: str, source_id: int, occurrence_key: str = "") -> dict[str, object]:
    row = connection.execute("SELECT * FROM reminder_overrides WHERE source_kind=? AND source_id=? AND occurrence_key=?", (source_kind, source_id, occurrence_key)).fetchone()
    if row is None:
        return {"mode": "default", "custom_timings": [], "suppressed_timings": []}
    return {"mode": row["mode"], "custom_timings": json.loads(row["custom_timings_json"]), "suppressed_timings": json.loads(row["suppressed_timings_json"])}


def evaluate_due_reminders(connection: sqlite3.Connection, *, now: datetime | None = None) -> int:
    """Materialise the latest currently due timing for each eligible occurrence."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    sources = reminder_occurrences(
        connection,
        now,
        horizon_days=_timing_horizon_days(_all_configured_timings(connection)),
    )
    _refresh_event_expiry_boundaries(connection, sources)
    _resolve_expired_event_attention(connection, now)
    created = 0
    for source in sources:
        if source.source_kind == "event" and source.due_at <= now:
            continue
        if source.persistent and source.due_at <= now:
            _resolve_pending_reminder_items(
                connection, source.source_kind, source.source_id
            )
            created += _deliver(
                connection, source, "overdue", "overdue", now
            )
            continue
        due_timings = []
        for timing in _resolved_timings(
            connection,
            source.source_kind,
            source.source_id,
            source.context,
            source.occurrence_key,
        ):
            attention_at = _subtract(source.due_at, timing)
            if attention_at <= now:
                due_timings.append((attention_at, timing))
        if due_timings:
            timing = max(due_timings, key=lambda item: item[0])[1]
            created += _deliver(connection, source, timing, "reminder", now)
    connection.commit()
    return created


def list_inbox_items(connection: sqlite3.Connection, *, archived: bool = False, limit: int = 500, offset: int = 0) -> list[InboxItem]:
    where = "state <> 'active' AND state <> 'snoozed'" if archived else "(state = 'active' OR (state = 'snoozed' AND next_attention_at <= ?))"
    params: tuple[object, ...] = () if archived else (utc_now(),)
    if archived:
        limit = max(0, min(limit, 500 - offset))
    if limit == 0:
        return []
    order = "delivered_at DESC, id DESC" if archived else "CASE WHEN reason='overdue' THEN 0 ELSE 1 END, due_at ASC, delivered_at ASC, id ASC"
    rows = connection.execute(f"SELECT * FROM inbox_items WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall()
    return [InboxItem(**dict(row)) for row in rows]


def list_deep_archive_items(connection: sqlite3.Connection) -> list[InboxItem]:
    rows = connection.execute(
        "SELECT * FROM inbox_items WHERE state <> 'active' AND state <> 'snoozed' "
        "ORDER BY delivered_at DESC, id DESC LIMIT -1 OFFSET 500"
    ).fetchall()
    return [InboxItem(**dict(row)) for row in rows]


def archived_inbox_count(connection: sqlite3.Connection) -> int:
    return int(connection.execute("SELECT COUNT(*) FROM inbox_items WHERE state <> 'active' AND state <> 'snoozed'").fetchone()[0])


def inbox_count(connection: sqlite3.Connection) -> int:
    return int(connection.execute("SELECT COUNT(*) FROM inbox_items WHERE state='active' OR (state='snoozed' AND next_attention_at <= ?)", (utc_now(),)).fetchone()[0])


def act_on_inbox_item(
    connection: sqlite3.Connection,
    item_id: int,
    action: str,
    *,
    now: datetime | None = None,
) -> bool:
    if action not in {"dismiss", "snooze_10m"}:
        raise ValueError("Inbox action is invalid.")
    row = connection.execute("SELECT * FROM inbox_items WHERE id = ?", (item_id,)).fetchone()
    if row is None or row["state"] not in {"active", "snoozed"}: return False
    instant = (now or datetime.now(UTC)).astimezone(UTC)
    if action == "snooze_10m":
        next_at = (instant + timedelta(minutes=10)).isoformat(timespec="seconds")
        _transition_item(connection, item_id, row["state"], "snoozed", action, next_at, "snoozed for 10 minutes", instant.isoformat(timespec="seconds"))
    else:
        _transition_item(connection, item_id, row["state"], "dismissed", action, "", "dismissed by user", instant.isoformat(timespec="seconds"))
    connection.commit(); return True


def open_inbox_item(connection: sqlite3.Connection, item_id: int) -> str | None:
    """Validate and open a reminder, clearing only Event-like attention."""
    row = connection.execute("SELECT * FROM inbox_items WHERE id = ?", (item_id,)).fetchone()
    if row is None or row["state"] not in {"active", "snoozed"}:
        return None
    destination = _source_destination(connection, row)
    if destination is None:
        return None
    if row["source_kind"] == "event":
        now = utc_now()
        _transition_item(
            connection,
            item_id,
            row["state"],
            "resolved",
            "opened_source",
            "",
            "Event occurrence opened",
            now,
        )
    connection.commit()
    return destination


def reactivate_next_open_snoozes(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT id, state FROM inbox_items WHERE state='snoozed' AND next_attention_at='9999-12-31T23:59:59+00:00'").fetchall()
    now = utc_now()
    for row in rows:
        _transition_item(connection, int(row["id"]), row["state"], "active", "next_open", "", "snooze ended on application open", now)
    connection.commit()


def _reconcile_context_deliveries(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str) -> None:
    """Resolve active deliveries whose timing was removed by a context policy edit."""
    source_ids = connection.execute(
        "SELECT DISTINCT source_id FROM inbox_items WHERE source_kind=? AND reason='reminder' AND state IN ('active', 'snoozed')",
        (source_kind,),
    ).fetchall()
    for row in source_ids:
        if _context_for_source(connection, source_kind, int(row["source_id"])) == (context_kind, context_id):
            _reconcile_source_deliveries(connection, source_kind, int(row["source_id"]))


def _reconcile_source_deliveries(connection: sqlite3.Connection, source_kind: str, source_id: int, *, occurrence_key: str | None = None) -> None:
    """Resolve only active reminders no longer enabled by the current policy."""
    context = _context_for_source(connection, source_kind, source_id)
    if context is None:
        resolve_source_items(connection, source_kind, source_id)
        return
    clause = " AND occurrence_key=?" if occurrence_key else ""
    parameters: list[object] = [source_kind, source_id]
    if occurrence_key:
        parameters.append(occurrence_key)
    rows = connection.execute(
        "SELECT id, occurrence_key, timing, state FROM inbox_items WHERE source_kind=? AND source_id=? AND reason='reminder' "
        "AND state IN ('active', 'snoozed')" + clause,
        parameters,
    ).fetchall()
    now = utc_now()
    for row in rows:
        timings = _resolved_timings(connection, source_kind, source_id, context, row["occurrence_key"])
        # Legacy deliveries predate the explicit timing column. They remain intact
        # unless reminders are disabled, when all pending delivery is suppressed.
        if not timings or (row["timing"] and row["timing"] not in timings):
            _transition_item(connection, int(row["id"]), row["state"], "resolved", "policy_superseded", "", "reminder policy superseded", now)


def _context_for_source(connection: sqlite3.Connection, source_kind: str, source_id: int) -> tuple[str, int] | None:
    if source_kind == "event":
        if source_id < 0:
            row = connection.execute(
                """SELECT subscription_id FROM external_calendar_events
                   WHERE id = ?""",
                (-source_id,),
            ).fetchone()
            return (
                "calendar_subscription",
                int(row["subscription_id"]),
            ) if row is not None else None
        row = connection.execute("SELECT calendar_id FROM events WHERE entity_id=?", (source_id,)).fetchone()
        return ("calendar", int(row["calendar_id"])) if row is not None else None
    if source_kind == "document_expiry":
        return ("global", 0)
    return None


def list_inbox_actions(connection: sqlite3.Connection, item_id: int) -> list[InboxAction]:
    rows = connection.execute("SELECT action, previous_state, resulting_state, next_attention_at, note, acted_at FROM inbox_item_actions WHERE inbox_item_id=? ORDER BY id", (item_id,)).fetchall()
    return [InboxAction(**dict(row)) for row in rows]


def list_inbox_actions_for_items(connection: sqlite3.Connection, item_ids: list[int]) -> dict[int, list[InboxAction]]:
    if not item_ids:
        return {}
    placeholders = ", ".join("?" for _ in item_ids)
    rows = connection.execute(
        f"SELECT inbox_item_id, action, previous_state, resulting_state, next_attention_at, note, acted_at "
        f"FROM inbox_item_actions WHERE inbox_item_id IN ({placeholders}) ORDER BY inbox_item_id, id",
        item_ids,
    ).fetchall()
    result = {item_id: [] for item_id in item_ids}
    for row in rows:
        values = dict(row)
        item_id = int(values.pop("inbox_item_id"))
        result[item_id].append(InboxAction(**values))
    return result


def _resolve_pending_reminder_items(connection: sqlite3.Connection, source_kind: str, source_id: int) -> None:
    _resolve_items(connection, "superseded by overdue condition", "overdue_condition", "source_kind=? AND source_id=? AND reason='reminder'", (source_kind, source_id))


def _resolved_timings(connection, kind, source_id, context, occurrence):
    row = connection.execute("SELECT * FROM reminder_overrides WHERE source_kind=? AND source_id=? AND occurrence_key IN (?, '') ORDER BY occurrence_key DESC LIMIT 1", (kind, source_id, occurrence)).fetchone()
    if row and row["mode"] == "disabled": return []
    timings = _context_timings(connection, context, kind)
    if row:
        suppressed = set(json.loads(row["suppressed_timings_json"])); timings = [value for value in timings if value not in suppressed]
        timings.extend(json.loads(row["custom_timings_json"]))
    return sorted(set(timings))


def _deliver(
    connection: sqlite3.Connection,
    source: TemporalOccurrence,
    timing: str,
    reason: str,
    now: datetime,
) -> int:
    key = _delivery_key(
        source.source_kind,
        source.source_id,
        source.occurrence_key,
        source.due_at,
        timing,
        reason,
    )
    _resolve_items(
        connection,
        "replaced by later reminder timing",
        "timing_superseded",
        "source_kind=? AND source_id=? AND occurrence_key=? AND reason=? AND delivery_key<>?",
        (
            source.source_kind,
            source.source_id,
            source.occurrence_key,
            reason,
            key,
        ),
    )
    expires_at = (
        source.attention_expires_at.isoformat(timespec="seconds")
        if source.attention_expires_at
        else ""
    )
    cursor = connection.execute("""INSERT OR IGNORE INTO inbox_items (delivery_key, source_kind, source_id, occurrence_key, reason, timing, title, due_at, delivered_at, attention_expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (key, source.source_kind, source.source_id, source.occurrence_key, reason, timing, source.title, source.due_at.isoformat(timespec="seconds"), now.isoformat(timespec="seconds"), expires_at))
    if cursor.rowcount:
        _record_action(connection, int(cursor.lastrowid), "delivered", "", "active", "", "local delivery created", now.isoformat(timespec="seconds"))
    return cursor.rowcount


def _refresh_event_expiry_boundaries(
    connection: sqlite3.Connection, sources: list[TemporalOccurrence]
) -> None:
    for source in sources:
        if source.source_kind != "event" or source.attention_expires_at is None:
            continue
        connection.execute(
            """UPDATE inbox_items
               SET occurrence_key=?, attention_expires_at=?
               WHERE source_kind='event' AND source_id=?
                 AND (occurrence_key=? OR due_at=?)
                 AND state IN ('active', 'snoozed')""",
            (
                source.occurrence_key,
                source.attention_expires_at.isoformat(timespec="seconds"),
                source.source_id,
                source.occurrence_key,
                source.due_at.isoformat(timespec="seconds"),
            ),
        )


def _resolve_expired_event_attention(
    connection: sqlite3.Connection, now: datetime
) -> None:
    rows = connection.execute(
        """SELECT id, state FROM inbox_items
           WHERE source_kind='event' AND state IN ('active', 'snoozed')
             AND attention_expires_at<>'' AND attention_expires_at<=?""",
        (now.isoformat(timespec="seconds"),),
    ).fetchall()
    acted_at = now.isoformat(timespec="seconds")
    for row in rows:
        _transition_item(
            connection,
            int(row["id"]),
            row["state"],
            "resolved",
            "occurrence_ended",
            "",
            "Event occurrence ended",
            acted_at,
        )


def _source_destination(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> str | None:
    source_id = int(row["source_id"])
    occurrence = row["occurrence_key"]
    occurrence_date = occurrence[:10]
    if row["source_kind"] == "event":
        if source_id < 0:
            if get_external_projection_event(connection, source_id) is None:
                return None
            return "/calendar?" + urlencode(
                {
                    "date": occurrence_date,
                    "external_preview": source_id,
                    "occurrence": occurrence_date,
                }
            )
        if get_event(connection, source_id) is None:
            return None
        return "/calendar?" + urlencode(
            {
                "date": occurrence_date,
                "preview": source_id,
                "occurrence": occurrence_date,
            }
        )
    if row["source_kind"] == "document_expiry":
        if get_entity(
            connection, DEFINITIONS_BY_TYPE["document"], source_id
        ) is None:
            return None
        return f"/documents/{source_id}"
    return None


def _delivery_key(kind, source_id, occurrence, due, timing, reason):
    return hashlib.sha256(f"{kind}|{source_id}|{occurrence}|{due.isoformat()}|{timing}|{reason}".encode()).hexdigest()


def _subtract(due, timing):
    if timing.endswith("mo"):
        months = int(timing[:-2]); month = due.month - months; year = due.year
        while month < 1: month += 12; year -= 1
        return due.replace(year=year, month=month, day=min(due.day, _month_day(year, month, due.day).day))
    amount = int(timing[:-1]); unit = timing[-1]
    return due - timedelta(minutes=amount if unit == "m" else 0, hours=amount if unit == "h" else 0, days=amount * (7 if unit == "w" else 1 if unit == "d" else 0))


def _month_day(year, month, day):
    while True:
        try: return date(year, month, day)
        except ValueError: day -= 1


def _timing_horizon_days(timings: list[str]) -> int:
    """Bound recurring projection far enough to include every configured lead time."""
    days = 1
    for timing in timings:
        if timing.endswith("mo"):
            days = max(days, int(timing[:-2]) * 32)
        elif timing.endswith("w"):
            days = max(days, int(timing[:-1]) * 7)
        elif timing.endswith("d"):
            days = max(days, int(timing[:-1]))
        else:
            days = max(days, 1)
    return days + 2


def _all_configured_timings(connection: sqlite3.Connection) -> list[str]:
    timings = [
        timing
        for defaults in DEFAULT_TIMINGS.values()
        for timing in defaults
    ]
    for row in connection.execute("SELECT timings_json FROM reminder_policies"):
        timings.extend(json.loads(row["timings_json"]))
    for row in connection.execute(
        "SELECT custom_timings_json FROM reminder_overrides"
    ):
        timings.extend(json.loads(row["custom_timings_json"]))
    return timings


def _context_timings(connection, context, source_kind):
    policy = connection.execute("SELECT timings_json FROM reminder_policies WHERE context_kind=? AND context_id=? AND source_kind=?", (*context, source_kind)).fetchone()
    if policy:
        return json.loads(policy[0])
    default_kind = source_kind
    if source_kind == "event" and context[0] == "calendar":
        calendar_row = connection.execute(
            "SELECT kind FROM calendars WHERE id=?", (context[1],)
        ).fetchone()
        if calendar_row is not None and calendar_row["kind"] == "birthday":
            default_kind = "birthday"
    return list(DEFAULT_TIMINGS[default_kind])


def _validate_timings(timings, *, maximum: int | None = None):
    if maximum is not None and len(set(timings)) > maximum:
        raise ValueError(f"No more than {maximum} reminder timings are allowed.")
    for value in timings:
        suffix = "mo" if isinstance(value, str) and value.endswith("mo") else value[-1:] if isinstance(value, str) else ""
        number = value[:-2] if suffix == "mo" else value[:-1] if isinstance(value, str) else ""
        if not number.isdigit() or int(number) <= 0 or suffix not in {"m", "h", "d", "w", "mo"}:
            raise ValueError("Reminder timing must use a positive number and m, h, d, w or mo.")
