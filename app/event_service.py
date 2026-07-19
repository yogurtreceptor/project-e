"""Canonical Event persistence and lifecycle services."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import json
import sqlite3
from typing import Any

from app.audit import record_audit_event, set_provenance
from app.db_support import utc_now
from app.temporal import (
    UTC_FORMAT,
    TemporalValueError,
    get_timezone,
    normalise_all_day_interval,
    normalise_timed_interval,
)


@dataclass(frozen=True)
class EventInput:
    title: str
    all_day: bool
    calendar_id: int | None = None
    notes: str = ""
    timezone: str = ""
    start_local: str = ""
    end_local: str = ""
    start_fold: int | None = None
    end_fold: int | None = None
    start_date: str = ""
    end_date: str = ""
    date_precision: str = "exact"


@dataclass(frozen=True)
class EventUpdate:
    title: str
    calendar_id: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class EventSchedule:
    all_day: bool
    timezone: str = ""
    start_local: str = ""
    end_local: str = ""
    start_fold: int | None = None
    end_fold: int | None = None
    start_date: str = ""
    end_date: str = ""
    date_precision: str = "exact"


@dataclass(frozen=True)
class EventRecord:
    id: int
    title: str
    notes: str
    calendar_id: int
    is_all_day: bool
    start_utc: str
    end_utc: str
    start_date: str
    end_date_exclusive: str
    timezone: str
    date_precision: str
    status: str
    archived_at: str
    deleted_at: str
    created_at: str
    updated_at: str

    @property
    def is_archived(self) -> bool:
        return bool(self.archived_at)

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"


def create_event(connection: sqlite3.Connection, event: EventInput) -> int:
    values = _normalise_event(connection, event)
    now = utc_now()
    try:
        cursor = connection.execute(
            """
            INSERT INTO entities (
                type, display_name, summary, notes, created_at, updated_at
            ) VALUES ('event', ?, '', ?, ?, ?)
            """,
            (values["title"], values["notes"], now, now),
        )
        event_id = int(cursor.lastrowid)
        _insert_event_row(connection, event_id, values)
        snapshot = _snapshot_values(values)
        record_audit_event(
            connection,
            "create",
            [("entity", event_id)],
            after=snapshot,
            notes="Event created",
        )
        for field_name, value in snapshot.items():
            if value not in ("", None, False):
                set_provenance(connection, "entity", event_id, field_name, "manual")
        connection.commit()
        return event_id
    except Exception:
        connection.rollback()
        raise


def update_event(
    connection: sqlite3.Connection, event_id: int, event: EventUpdate
) -> None:
    current = get_event(connection, event_id, include_archived=True)
    if current is None:
        raise ValueError("Event does not exist.")
    title = event.title.strip()
    if not title:
        raise ValueError("Event title is required.")
    calendar = _resolve_reference(
        connection,
        "calendars",
        event.calendar_id,
        current.calendar_id,
        "Calendar",
    )
    before = _record_snapshot(current)
    after = dict(before)
    after.update(
        {
            "title": title,
            "notes": event.notes.strip(),
            "calendar_id": int(calendar["id"]),
        }
    )
    if before == after:
        return
    now = utc_now()
    try:
        connection.execute(
            """
            UPDATE entities
            SET display_name = ?, notes = ?, updated_at = ?
            WHERE id = ? AND type = 'event' AND deleted_at = ''
            """,
            (after["title"], after["notes"], now, event_id),
        )
        connection.execute(
            "UPDATE events SET calendar_id = ? WHERE entity_id = ?",
            (after["calendar_id"], event_id),
        )
        _record_history(connection, event_id, "edit", before, after)
        record_audit_event(
            connection,
            "edit",
            [("entity", event_id)],
            before=before,
            after=after,
            notes="Event edited",
        )
        for field_name, value in after.items():
            if before.get(field_name) != value:
                set_provenance(connection, "entity", event_id, field_name, "manual")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def cancel_event(connection: sqlite3.Connection, event_id: int) -> bool:
    return _change_event_status(
        connection, event_id, expected="planned", replacement="cancelled",
        action="cancel", note="Event cancelled",
    )


def reinstate_event(connection: sqlite3.Connection, event_id: int) -> bool:
    return _change_event_status(
        connection, event_id, expected="cancelled", replacement="planned",
        action="reinstate", note="Event reinstated",
    )


def reschedule_event(
    connection: sqlite3.Connection,
    event_id: int,
    schedule: EventSchedule,
) -> bool:
    current = get_event(connection, event_id, include_archived=True)
    if current is None:
        raise ValueError("Event does not exist.")
    values = _normalise_event(
        connection,
        EventInput(
            title=current.title,
            notes=current.notes,
            calendar_id=current.calendar_id,
            all_day=schedule.all_day,
            timezone=schedule.timezone,
            start_local=schedule.start_local,
            end_local=schedule.end_local,
            start_fold=schedule.start_fold,
            end_fold=schedule.end_fold,
            start_date=schedule.start_date,
            end_date=schedule.end_date,
            date_precision=schedule.date_precision,
        ),
        current_calendar_id=current.calendar_id,
        current_status=current.status,
    )
    before = _record_snapshot(current)
    after = _snapshot_values(values)
    temporal_fields = (
        "is_all_day", "start_utc", "end_utc", "start_date",
        "end_date_exclusive", "timezone", "date_precision",
    )
    if all(before[field] == after[field] for field in temporal_fields):
        return False
    now = utc_now()
    try:
        connection.execute(
            """
            UPDATE events SET
                is_all_day = ?, start_utc = ?, end_utc = ?, start_date = ?,
                end_date_exclusive = ?, timezone = ?, date_precision = ?
            WHERE entity_id = ?
            """,
            (
                after["is_all_day"], after["start_utc"], after["end_utc"],
                after["start_date"], after["end_date_exclusive"],
                after["timezone"], after["date_precision"], event_id,
            ),
        )
        connection.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?", (now, event_id)
        )
        history_before = {field: before[field] for field in temporal_fields}
        history_after = {field: after[field] for field in temporal_fields}
        _record_history(
            connection, event_id, "reschedule", history_before, history_after
        )
        record_audit_event(
            connection,
            "reschedule",
            [("entity", event_id)],
            before=history_before,
            after=history_after,
            notes="Event rescheduled",
        )
        for field in temporal_fields:
            if history_before[field] != history_after[field]:
                set_provenance(connection, "entity", event_id, field, "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def archive_event(connection: sqlite3.Connection, event_id: int) -> bool:
    event = get_event(connection, event_id, include_archived=True)
    if event is None:
        raise ValueError("Event does not exist.")
    if event.is_archived:
        return False
    archived_at = utc_now()
    try:
        connection.execute(
            "UPDATE events SET archived_at = ? WHERE entity_id = ?",
            (archived_at, event_id),
        )
        connection.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?",
            (archived_at, event_id),
        )
        _record_history(
            connection,
            event_id,
            "archive",
            {"archived_at": ""},
            {"archived_at": archived_at},
        )
        record_audit_event(
            connection,
            "archive",
            [("entity", event_id)],
            before={"archived_at": ""},
            after={"archived_at": archived_at},
            notes="Event archived",
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def unarchive_event(connection: sqlite3.Connection, event_id: int) -> bool:
    event = get_event(connection, event_id, include_archived=True)
    if event is None:
        raise ValueError("Event does not exist.")
    if not event.is_archived:
        return False
    restored_at = utc_now()
    try:
        connection.execute(
            "UPDATE events SET archived_at = '' WHERE entity_id = ?", (event_id,)
        )
        connection.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?",
            (restored_at, event_id),
        )
        _record_history(
            connection,
            event_id,
            "unarchive",
            {"archived_at": event.archived_at},
            {"archived_at": ""},
        )
        record_audit_event(
            connection,
            "unarchive",
            [("entity", event_id)],
            before={"archived_at": event.archived_at},
            after={"archived_at": ""},
            notes="Event unarchived",
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def get_event(
    connection: sqlite3.Connection,
    event_id: int,
    *,
    include_archived: bool = False,
) -> EventRecord | None:
    archived_clause = "" if include_archived else "AND event.archived_at = ''"
    row = connection.execute(
        f"""
        SELECT entity.*, event.*
        FROM entities AS entity
        JOIN events AS event ON event.entity_id = entity.id
        WHERE entity.id = ? AND entity.type = 'event'
          AND entity.deleted_at = '' {archived_clause}
        """,
        (event_id,),
    ).fetchone()
    return _to_event_record(row) if row is not None else None


def list_events(
    connection: sqlite3.Connection, *, include_archived: bool = False
) -> list[EventRecord]:
    archived_clause = "" if include_archived else "AND event.archived_at = ''"
    rows = connection.execute(
        f"""
        SELECT entity.*, event.*
        FROM entities AS entity
        JOIN events AS event ON event.entity_id = entity.id
        WHERE entity.type = 'event' AND entity.deleted_at = ''
          {archived_clause}
        ORDER BY
          CASE WHEN event.is_all_day = 1
               THEN event.start_date ELSE event.start_utc END,
          entity.id
        """
    ).fetchall()
    return [_to_event_record(row) for row in rows]


def validate_stored_event(connection: sqlite3.Connection, event_id: int) -> list[str]:
    """Validate an Event loaded from an imported or upgraded database."""
    row = connection.execute(
        """
        SELECT event.*, entity.display_name
        FROM events AS event
        JOIN entities AS entity ON entity.id = event.entity_id
        WHERE event.entity_id = ? AND entity.type = 'event'
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        return ["Event typed record is missing."]
    errors: list[str] = []
    if not row["display_name"].strip():
        errors.append("Event title is required.")
    if row["date_precision"] not in ("exact", "approximate"):
        errors.append("Event date precision is invalid.")
    if row["status"] not in ("planned", "cancelled"):
        errors.append("Event status is invalid.")
    for table, reference_id, label in (
        ("calendars", row["calendar_id"], "Calendar"),
    ):
        if connection.execute(
            f"SELECT 1 FROM {table} WHERE id = ?", (reference_id,)
        ).fetchone() is None:
            errors.append(f"{label} reference is invalid.")
    if row["is_all_day"]:
        try:
            inclusive_end = (
                date.fromisoformat(row["end_date_exclusive"]) - timedelta(days=1)
            ).isoformat()
            normalise_all_day_interval(
                row["start_date"],
                inclusive_end,
            )
        except (TemporalValueError, ValueError):
            errors.append("All-day Event boundaries are invalid.")
    else:
        try:
            start = datetime.strptime(row["start_utc"], UTC_FORMAT)
            end = datetime.strptime(row["end_utc"], UTC_FORMAT)
            if end <= start:
                raise ValueError
            get_timezone(row["timezone"])
        except (TemporalValueError, ValueError):
            errors.append("Timed Event values are invalid.")
    return errors


def _normalise_event(
    connection: sqlite3.Connection,
    event: EventInput,
    *,
    current_calendar_id: int | None = None,
    current_status: str = "planned",
) -> dict[str, Any]:
    title = event.title.strip()
    if not title:
        raise ValueError("Event title is required.")
    if event.date_precision not in ("exact", "approximate"):
        raise ValueError("Event date precision must be exact or approximate.")

    calendar = _resolve_reference(
        connection,
        "calendars",
        event.calendar_id,
        current_calendar_id,
        "Calendar",
    )
    values: dict[str, Any] = {
        "title": title,
        "notes": event.notes.strip(),
        "calendar_id": int(calendar["id"]),
        "is_all_day": int(event.all_day),
        "start_utc": "",
        "end_utc": "",
        "start_date": "",
        "end_date_exclusive": "",
        "timezone": "",
        "date_precision": event.date_precision,
        "status": current_status,
    }
    if event.all_day:
        interval = normalise_all_day_interval(event.start_date, event.end_date)
        values["start_date"] = interval.start_date
        values["end_date_exclusive"] = interval.end_date_exclusive
    else:
        timezone_name = event.timezone.strip() or calendar["timezone"]
        interval = normalise_timed_interval(
            event.start_local,
            event.end_local,
            timezone_name,
            start_fold=event.start_fold,
            end_fold=event.end_fold,
        )
        values["start_utc"] = interval.start_utc
        values["end_utc"] = interval.end_utc
        values["timezone"] = interval.timezone
    return values


def _change_event_status(
    connection: sqlite3.Connection,
    event_id: int,
    *,
    expected: str,
    replacement: str,
    action: str,
    note: str,
) -> bool:
    event = get_event(connection, event_id, include_archived=True)
    if event is None:
        raise ValueError("Event does not exist.")
    if event.status == replacement:
        return False
    if event.status != expected:
        raise ValueError(f"Event cannot be changed from {event.status}.")
    now = utc_now()
    try:
        connection.execute(
            "UPDATE events SET status = ? WHERE entity_id = ?",
            (replacement, event_id),
        )
        connection.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?", (now, event_id)
        )
        before = {"status": expected}
        after = {"status": replacement}
        _record_history(connection, event_id, action, before, after)
        record_audit_event(
            connection,
            action,
            [("entity", event_id)],
            before=before,
            after=after,
            notes=note,
        )
        set_provenance(connection, "entity", event_id, "status", "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def _resolve_reference(
    connection: sqlite3.Connection,
    table: str,
    requested_id: int | None,
    current_id: int | None,
    label: str,
) -> sqlite3.Row:
    if requested_id is None:
        if current_id is not None:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE id = ?", (current_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"{label} does not exist.")
            return row
        row = connection.execute(
            f"SELECT * FROM {table} WHERE is_default = 1 AND archived_at = ''"
        ).fetchone()
        if row is None:
            raise ValueError(f"No active default {label.lower()} is configured.")
        return row
    row = connection.execute(
        f"SELECT * FROM {table} WHERE id = ?", (requested_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"{label} does not exist.")
    if row["archived_at"] and int(row["id"]) != current_id:
        raise ValueError(f"Archived {label.lower()} cannot be selected.")
    return row


def _insert_event_row(
    connection: sqlite3.Connection, event_id: int, values: dict[str, Any]
) -> None:
    connection.execute(
        """
        INSERT INTO events (
            entity_id, calendar_id, is_all_day,
            start_utc, end_utc, start_date, end_date_exclusive,
            timezone, date_precision, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            values["calendar_id"],
            values["is_all_day"],
            values["start_utc"],
            values["end_utc"],
            values["start_date"],
            values["end_date_exclusive"],
            values["timezone"],
            values["date_precision"],
            values["status"],
        ),
    )


def _to_event_record(row: sqlite3.Row) -> EventRecord:
    return EventRecord(
        id=int(row["id"]),
        title=row["display_name"],
        notes=row["notes"],
        calendar_id=int(row["calendar_id"]),
        is_all_day=bool(row["is_all_day"]),
        start_utc=row["start_utc"],
        end_utc=row["end_utc"],
        start_date=row["start_date"],
        end_date_exclusive=row["end_date_exclusive"],
        timezone=row["timezone"],
        date_precision=row["date_precision"],
        status=row["status"],
        archived_at=row["archived_at"],
        deleted_at=row["deleted_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _snapshot_values(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if key not in {"start_fold", "end_fold"}
    }


def _record_snapshot(event: EventRecord) -> dict[str, Any]:
    values = asdict(event)
    return {
        "title": values["title"],
        "notes": values["notes"],
        "calendar_id": values["calendar_id"],
        "is_all_day": int(values["is_all_day"]),
        "start_utc": values["start_utc"],
        "end_utc": values["end_utc"],
        "start_date": values["start_date"],
        "end_date_exclusive": values["end_date_exclusive"],
        "timezone": values["timezone"],
        "date_precision": values["date_precision"],
        "status": values["status"],
    }


def _record_history(
    connection: sqlite3.Connection,
    event_id: int,
    event_type: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO entity_edit_history (
            entity_id, event_type, details, created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            event_id,
            event_type,
            json.dumps({"before": before, "after": after}, sort_keys=True),
            utc_now(),
        ),
    )
