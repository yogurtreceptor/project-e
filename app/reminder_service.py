"""Deterministic local reminder resolution and durable Inbox delivery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import sqlite3
from zoneinfo import ZoneInfo

from app.db_support import utc_now
from app.entity_repository import list_entities
from app.entities import DEFINITIONS_BY_TYPE
from app.event_service import list_events
from app.event_recurrence import get_recurrence, occurrence_exceptions, occurrences_between
from app.task_service import list_tasks

PLATFORM_TIMEZONE = "Australia/Brisbane"
DEFAULT_TIMINGS = {
    "event": ["1h", "10m"],
    "task_deadline": ["3d", "2d", "1d", "6h", "1h"],
    "birthday": ["1mo", "2w", "1w", "3d", "1d", "12h"],
    "document_expiry": ["1mo", "2w", "1w", "3d", "1d"],
}

@dataclass(frozen=True)
class InboxItem:
    id: int; delivery_key: str; source_kind: str; source_id: int; occurrence_key: str
    reason: str; timing: str; title: str; due_at: str; delivered_at: str; state: str
    next_attention_at: str; acted_at: str; action_note: str


@dataclass(frozen=True)
class UpcomingReminder:
    source_kind: str; source_id: int; occurrence_key: str; title: str
    due_at: str; attention_at: str; timing: str


@dataclass(frozen=True)
class InboxAction:
    action: str; previous_state: str; resulting_state: str; next_attention_at: str
    note: str; acted_at: str


def set_policy(connection: sqlite3.Connection, context_kind: str, context_id: int, source_kind: str, timings: list[str]) -> None:
    _validate_timings(timings)
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


def set_override(connection: sqlite3.Connection, source_kind: str, source_id: int, *, mode: str = "default", custom_timings: list[str] | None = None, suppressed_timings: list[str] | None = None, occurrence_key: str = "") -> None:
    if mode not in {"default", "custom", "disabled"}: raise ValueError("Reminder override mode is invalid.")
    custom_timings, suppressed_timings = custom_timings or [], suppressed_timings or []
    _validate_timings(custom_timings + suppressed_timings)
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
    """Materialise every currently due, eligible delivery exactly once."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    created = 0
    for kind, source_id, occurrence, title, due, context in _sources(connection, now):
        timings = _resolved_timings(connection, kind, source_id, context, occurrence)
        for timing in timings:
            attention = _subtract(due, timing)
            if attention > now: continue
            created += _deliver(connection, kind, source_id, occurrence, title, due, timing, "reminder", now)
        if kind == "task_deadline" and due <= now:
            created += _deliver(connection, kind, source_id, occurrence, title, due, "overdue", "overdue", now)
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


def list_upcoming_reminders(connection: sqlite3.Connection, *, now: datetime | None = None, limit: int = 20) -> list[UpcomingReminder]:
    """Preview future reminder attention without creating a delivery before it is due."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    results: list[UpcomingReminder] = []
    for kind, source_id, occurrence, title, due, context in _sources(connection, now):
        for timing in _resolved_timings(connection, kind, source_id, context, occurrence):
            attention = _subtract(due, timing)
            if attention <= now:
                continue
            key = _delivery_key(kind, source_id, occurrence, due, timing, "reminder")
            row = connection.execute("SELECT 1 FROM inbox_items WHERE delivery_key=?", (key,)).fetchone()
            if row is None:
                results.append(UpcomingReminder(kind, source_id, occurrence, title, due.isoformat(timespec="seconds"), attention.isoformat(timespec="seconds"), timing))
    return sorted(results, key=lambda item: (item.attention_at, item.due_at, item.source_kind, item.source_id))[:limit]


def inbox_count(connection: sqlite3.Connection) -> int:
    return int(connection.execute("SELECT COUNT(*) FROM inbox_items WHERE state='active' OR (state='snoozed' AND next_attention_at <= ?)", (utc_now(),)).fetchone()[0])


def act_on_inbox_item(connection: sqlite3.Connection, item_id: int, action: str) -> bool:
    if action not in {"acknowledge", "dismiss", "snooze_30m", "snooze_next_open"}: raise ValueError("Inbox action is invalid.")
    row = connection.execute("SELECT * FROM inbox_items WHERE id = ?", (item_id,)).fetchone()
    if row is None or row["state"] not in {"active", "snoozed"}: return False
    now = datetime.now(UTC)
    if action.startswith("snooze"):
        next_at = (now + timedelta(minutes=30)).isoformat(timespec="seconds") if action == "snooze_30m" else "9999-12-31T23:59:59+00:00"
        _transition_item(connection, item_id, row["state"], "snoozed", action, next_at, action, now.isoformat(timespec="seconds"))
    else:
        state = "acknowledged" if action == "acknowledge" else "dismissed"
        _transition_item(connection, item_id, row["state"], state, action, "", action, now.isoformat(timespec="seconds"))
    connection.commit(); return True


def reactivate_next_open_snoozes(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT id, state FROM inbox_items WHERE state='snoozed' AND next_attention_at='9999-12-31T23:59:59+00:00'").fetchall()
    now = utc_now()
    for row in rows:
        _transition_item(connection, int(row["id"]), row["state"], "active", "next_open", "", "snooze ended on application open", now)
    connection.commit()


def resolve_source_items(connection: sqlite3.Connection, source_kind: str, source_id: int) -> None:
    _resolve_items(connection, "source no longer due", "source_lifecycle", "source_kind=? AND source_id=?", (source_kind, source_id))


def resolve_source_items_after_occurrence(connection: sqlite3.Connection, source_kind: str, source_id: int, occurrence_key: str) -> None:
    """Resolve pending source deliveries moved to a successor recurring series."""
    _resolve_items(connection, "recurring series superseded", "series_split", "source_kind=? AND source_id=? AND occurrence_key>=?", (source_kind, source_id, occurrence_key))


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
        row = connection.execute("SELECT calendar_id FROM events WHERE entity_id=?", (source_id,)).fetchone()
        return ("calendar", int(row["calendar_id"])) if row is not None else None
    if source_kind == "task_deadline":
        row = connection.execute("SELECT task_list_id FROM tasks WHERE entity_id=?", (source_id,)).fetchone()
        return ("task_list", int(row["task_list_id"])) if row is not None else None
    if source_kind in {"birthday", "document_expiry"}:
        return ("global", 0)
    return None


def list_inbox_actions(connection: sqlite3.Connection, item_id: int) -> list[InboxAction]:
    rows = connection.execute("SELECT action, previous_state, resulting_state, next_attention_at, note, acted_at FROM inbox_item_actions WHERE inbox_item_id=? ORDER BY id", (item_id,)).fetchall()
    return [InboxAction(**dict(row)) for row in rows]


def _resolve_items(connection: sqlite3.Connection, note: str, action: str, clause: str, parameters: tuple[object, ...]) -> None:
    rows = connection.execute("SELECT id, state FROM inbox_items WHERE " + clause + " AND state IN ('active', 'snoozed')", parameters).fetchall()
    now = utc_now()
    for row in rows:
        _transition_item(connection, int(row["id"]), row["state"], "resolved", action, "", note, now)


def _transition_item(connection: sqlite3.Connection, item_id: int, previous_state: str, resulting_state: str, action: str, next_attention_at: str, note: str, acted_at: str) -> None:
    connection.execute("UPDATE inbox_items SET state=?, next_attention_at=?, acted_at=?, action_note=? WHERE id=?", (resulting_state, next_attention_at, acted_at, note, item_id))
    _record_action(connection, item_id, action, previous_state, resulting_state, next_attention_at, note, acted_at)


def _record_action(connection: sqlite3.Connection, item_id: int, action: str, previous_state: str, resulting_state: str, next_attention_at: str, note: str, acted_at: str) -> None:
    connection.execute("INSERT INTO inbox_item_actions (inbox_item_id, action, previous_state, resulting_state, next_attention_at, note, acted_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (item_id, action, previous_state, resulting_state, next_attention_at, note, acted_at))


def _sources(connection, now):
    zone = ZoneInfo(PLATFORM_TIMEZONE)
    for event in list_events(connection):
        if event.is_cancelled or event.is_archived or event.date_precision != "exact": continue
        recurrence = get_recurrence(connection, event.id)
        if recurrence is None:
            occurrences = [event]
        else:
            local_today = now.astimezone(ZoneInfo(event.timezone or PLATFORM_TIMEZONE)).date()
            exceptions = occurrence_exceptions(connection, recurrence)
            occurrences = [item.event for item in occurrences_between(
                event, recurrence, local_today - timedelta(days=1), local_today + timedelta(days=1), exceptions
            )]
        for occurrence in occurrences:
            due = _parse_utc(occurrence.start_utc) if not occurrence.is_all_day else datetime.combine(date.fromisoformat(occurrence.start_date), datetime.min.time(), zone).replace(hour=9).astimezone(UTC)
            yield "event", event.id, occurrence.start_date or occurrence.start_utc, occurrence.title, due, ("calendar", event.calendar_id)
    for task in list_tasks(connection):
        if not (task.deadline_date or task.deadline_utc): continue
        due = _parse_utc(task.deadline_utc) if task.deadline_utc else datetime.combine(date.fromisoformat(task.deadline_date), datetime.min.time(), zone).replace(hour=9).astimezone(UTC)
        yield "task_deadline", task.id, task.deadline_date or task.deadline_utc, task.title, due, ("task_list", task.task_list_id)
    for person in list_entities(connection, DEFINITIONS_BY_TYPE["person"]):
        birthday = person.metadata.get("birthday", "")
        if not birthday: continue
        born = date.fromisoformat(birthday); year = now.astimezone(zone).year
        for occurrence_year in (year, year + 1):
            day = _month_day(occurrence_year, born.month, born.day)
            due = datetime.combine(day, datetime.min.time(), zone).replace(hour=9).astimezone(UTC)
            yield "birthday", person.id, day.isoformat(), f"{person.title}'s birthday", due, ("global", 0)
    for document in list_entities(connection, DEFINITIONS_BY_TYPE["document"]):
        expiry = document.metadata.get("expiry_date", "")
        if expiry:
            due = datetime.combine(date.fromisoformat(expiry), datetime.min.time(), zone).replace(hour=9).astimezone(UTC)
            yield "document_expiry", document.id, expiry, f"{document.title} expires", due, ("global", 0)


def _resolved_timings(connection, kind, source_id, context, occurrence):
    row = connection.execute("SELECT * FROM reminder_overrides WHERE source_kind=? AND source_id=? AND occurrence_key IN (?, '') ORDER BY occurrence_key DESC LIMIT 1", (kind, source_id, occurrence)).fetchone()
    if row and row["mode"] == "disabled": return []
    policy = connection.execute("SELECT timings_json FROM reminder_policies WHERE context_kind=? AND context_id=? AND source_kind=?", (*context, kind)).fetchone()
    timings = json.loads(policy[0]) if policy else list(DEFAULT_TIMINGS[kind])
    if row:
        suppressed = set(json.loads(row["suppressed_timings_json"])); timings = [value for value in timings if value not in suppressed]
        timings.extend(json.loads(row["custom_timings_json"]))
    return sorted(set(timings))


def _deliver(connection, kind, source_id, occurrence, title, due, timing, reason, now):
    key = _delivery_key(kind, source_id, occurrence, due, timing, reason)
    cursor = connection.execute("""INSERT OR IGNORE INTO inbox_items (delivery_key, source_kind, source_id, occurrence_key, reason, timing, title, due_at, delivered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (key, kind, source_id, occurrence, reason, timing, title, due.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")))
    if cursor.rowcount:
        _record_action(connection, int(cursor.lastrowid), "delivered", "", "active", "", "local delivery created", now.isoformat(timespec="seconds"))
    return cursor.rowcount


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

def _parse_utc(value): return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
def _validate_timings(timings):
    for value in timings:
        suffix = "mo" if isinstance(value, str) and value.endswith("mo") else value[-1:] if isinstance(value, str) else ""
        number = value[:-2] if suffix == "mo" else value[:-1] if isinstance(value, str) else ""
        if not number.isdigit() or int(number) <= 0 or suffix not in {"m", "h", "d", "w", "mo"}:
            raise ValueError("Reminder timing must use a positive number and m, h, d, w or mo.")
