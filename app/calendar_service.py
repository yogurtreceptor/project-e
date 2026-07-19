"""Calendar management services and lifecycle safeguards."""

from dataclasses import asdict, dataclass
import json
import re
import sqlite3

from app.audit import record_audit_event, set_provenance
from app.db_support import utc_now
from app.temporal import TemporalValueError, get_timezone


_COLOUR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class CalendarInput:
    name: str
    colour: str = "#2563EB"
    timezone: str = "Australia/Brisbane"
    default_event_duration_minutes: int = 60
    sort_order: int = 0


@dataclass(frozen=True)
class CalendarRecord:
    id: int
    name: str
    colour: str
    timezone: str
    default_event_duration_minutes: int
    sort_order: int
    is_default: bool
    created_at: str
    updated_at: str
    archived_at: str

    @property
    def is_archived(self) -> bool:
        return bool(self.archived_at)


def list_calendars(
    connection: sqlite3.Connection, *, include_archived: bool = False
) -> list[CalendarRecord]:
    clause = "" if include_archived else "WHERE archived_at = ''"
    rows = connection.execute(
        f"SELECT * FROM calendars {clause} "
        "ORDER BY archived_at, sort_order, lower(name), id"
    ).fetchall()
    return [_to_record(row) for row in rows]


def get_calendar(
    connection: sqlite3.Connection, calendar_id: int, *, include_archived: bool = False
) -> CalendarRecord | None:
    clause = "" if include_archived else "AND archived_at = ''"
    row = connection.execute(
        f"SELECT * FROM calendars WHERE id = ? {clause}", (calendar_id,)
    ).fetchone()
    return _to_record(row) if row is not None else None


def create_calendar(connection: sqlite3.Connection, values: CalendarInput) -> int:
    normalised = _normalise(values)
    now = utc_now()
    try:
        cursor = connection.execute(
            """
            INSERT INTO calendars (
                name, colour, timezone, default_event_duration_minutes, sort_order,
                is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (*_stored_values(normalised), now, now),
        )
        calendar_id = int(cursor.lastrowid)
        after = _snapshot(get_calendar(connection, calendar_id, include_archived=True))
        record_audit_event(
            connection, "create", [("calendar", calendar_id)], after=after,
            notes="Calendar created",
        )
        for field_name, value in after.items():
            if value not in ("", None, False):
                set_provenance(connection, "calendar", calendar_id, field_name, "manual")
        connection.commit()
        return calendar_id
    except Exception:
        connection.rollback()
        raise


def rename_calendar(connection: sqlite3.Connection, calendar_id: int, name: str) -> bool:
    current = _require_calendar(connection, calendar_id)
    return _update_calendar(connection, current, CalendarInput(
        name=name, colour=current.colour, timezone=current.timezone,
        default_event_duration_minutes=current.default_event_duration_minutes,
        sort_order=current.sort_order,
    ))


def update_calendar(
    connection: sqlite3.Connection, calendar_id: int, values: CalendarInput
) -> bool:
    return _update_calendar(connection, _require_calendar(connection, calendar_id), values)


def set_default_calendar(connection: sqlite3.Connection, calendar_id: int) -> bool:
    calendar = _require_calendar(connection, calendar_id)
    if calendar.is_default:
        return False
    before = {item.id: _snapshot(item) for item in list_calendars(connection, include_archived=True) if item.is_default}
    now = utc_now()
    try:
        connection.execute("UPDATE calendars SET is_default = 0 WHERE is_default = 1")
        connection.execute(
            "UPDATE calendars SET is_default = 1, updated_at = ? WHERE id = ?",
            (now, calendar_id),
        )
        after = _snapshot(get_calendar(connection, calendar_id, include_archived=True))
        _record_history(connection, calendar_id, "set_default", {"is_default": False}, {"is_default": True})
        record_audit_event(
            connection, "edit", [("calendar", calendar_id)], before=before,
            after=after, notes="Calendar selected as default",
        )
        set_provenance(connection, "calendar", calendar_id, "is_default", "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def archive_calendar(connection: sqlite3.Connection, calendar_id: int) -> bool:
    calendar = _require_calendar(connection, calendar_id)
    if calendar.is_default:
        raise ValueError("Select another active Calendar as default before archiving this Calendar.")
    archived_at = utc_now()
    try:
        connection.execute(
            "UPDATE calendars SET archived_at = ?, updated_at = ? WHERE id = ?",
            (archived_at, archived_at, calendar_id),
        )
        _record_history(connection, calendar_id, "archive", {"archived_at": ""}, {"archived_at": archived_at})
        record_audit_event(connection, "archive", [("calendar", calendar_id)],
                           before={"archived_at": ""}, after={"archived_at": archived_at},
                           notes="Calendar archived; assigned Events were retained")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def unarchive_calendar(connection: sqlite3.Connection, calendar_id: int) -> bool:
    calendar = get_calendar(connection, calendar_id, include_archived=True)
    if calendar is None:
        raise ValueError("Calendar does not exist.")
    if not calendar.is_archived:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE calendars SET archived_at = '', updated_at = ? WHERE id = ?", (now, calendar_id))
        _record_history(connection, calendar_id, "unarchive", {"archived_at": calendar.archived_at}, {"archived_at": ""})
        record_audit_event(connection, "unarchive", [("calendar", calendar_id)],
                           before={"archived_at": calendar.archived_at}, after={"archived_at": ""},
                           notes="Calendar unarchived")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def delete_calendar(connection: sqlite3.Connection, calendar_id: int) -> None:
    """Permanently remove only an empty, non-default Calendar.

    Events are never moved implicitly; including recycled Events protects their
    retained identity and prevents a future restoration from becoming orphaned.
    """
    calendar = get_calendar(connection, calendar_id, include_archived=True)
    if calendar is None:
        raise ValueError("Calendar does not exist.")
    if calendar.is_default:
        raise ValueError("The default Calendar cannot be deleted.")
    event_count = connection.execute(
        "SELECT COUNT(*) FROM events WHERE calendar_id = ?", (calendar_id,)
    ).fetchone()[0]
    if event_count:
        raise ValueError("Calendar cannot be deleted while Events are assigned to it.")
    before = _snapshot(calendar)
    try:
        connection.execute("DELETE FROM calendars WHERE id = ?", (calendar_id,))
        record_audit_event(connection, "permanent_delete", [("calendar", calendar_id)],
                           before=before, notes="Empty Calendar permanently deleted")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def list_calendar_history(connection: sqlite3.Connection, calendar_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM calendar_edit_history WHERE calendar_id = ? ORDER BY created_at DESC, id DESC",
        (calendar_id,),
    ).fetchall()


def validate_stored_calendar(connection: sqlite3.Connection, calendar_id: int) -> list[str]:
    row = connection.execute("SELECT * FROM calendars WHERE id = ?", (calendar_id,)).fetchone()
    if row is None:
        return ["Calendar record is missing."]
    errors: list[str] = []
    try:
        _normalise(CalendarInput(row["name"], row["colour"], row["timezone"], row["default_event_duration_minutes"], row["sort_order"]))
    except ValueError as error:
        errors.append(str(error))
    if row["is_default"] not in (0, 1):
        errors.append("Calendar default state is invalid.")
    if row["is_default"] and row["archived_at"]:
        errors.append("The default Calendar must be active.")
    return errors


def _update_calendar(connection: sqlite3.Connection, current: CalendarRecord, values: CalendarInput) -> bool:
    normalised = _normalise(values)
    before = _snapshot(current)
    after = dict(before)
    after.update(asdict(normalised))
    if before == after:
        return False
    now = utc_now()
    try:
        connection.execute(
            """UPDATE calendars SET name = ?, colour = ?, timezone = ?,
               default_event_duration_minutes = ?, sort_order = ?, updated_at = ?
               WHERE id = ?""",
            (*_stored_values(normalised), now, current.id),
        )
        _record_history(connection, current.id, "edit", before, after)
        record_audit_event(connection, "edit", [("calendar", current.id)], before=before,
                           after=after, notes="Calendar updated")
        for field_name, value in after.items():
            if before.get(field_name) != value:
                set_provenance(connection, "calendar", current.id, field_name, "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def _require_calendar(connection: sqlite3.Connection, calendar_id: int) -> CalendarRecord:
    calendar = get_calendar(connection, calendar_id)
    if calendar is None:
        archived = get_calendar(connection, calendar_id, include_archived=True)
        if archived is not None:
            raise ValueError("Archived Calendar cannot be changed until it is unarchived.")
        raise ValueError("Calendar does not exist.")
    return calendar


def _normalise(values: CalendarInput) -> CalendarInput:
    name = values.name.strip()
    if not name:
        raise ValueError("Calendar name is required.")
    colour = values.colour.strip()
    if not _COLOUR_PATTERN.fullmatch(colour):
        raise ValueError("Calendar colour must be a #RRGGBB value.")
    timezone = values.timezone.strip()
    try:
        get_timezone(timezone)
    except TemporalValueError as error:
        raise ValueError(str(error)) from error
    if isinstance(values.default_event_duration_minutes, bool) or not isinstance(values.default_event_duration_minutes, int) or values.default_event_duration_minutes <= 0:
        raise ValueError("Calendar default Event duration must be a positive number of minutes.")
    if isinstance(values.sort_order, bool) or not isinstance(values.sort_order, int):
        raise ValueError("Calendar ordering must be an integer.")
    return CalendarInput(name, colour, timezone, values.default_event_duration_minutes, values.sort_order)


def _stored_values(values: CalendarInput) -> tuple[object, ...]:
    return (values.name, values.colour, values.timezone, values.default_event_duration_minutes, values.sort_order)


def _to_record(row: sqlite3.Row) -> CalendarRecord:
    return CalendarRecord(int(row["id"]), row["name"], row["colour"], row["timezone"],
                          int(row["default_event_duration_minutes"]), int(row["sort_order"]),
                          bool(row["is_default"]), row["created_at"], row["updated_at"], row["archived_at"])


def _snapshot(calendar: CalendarRecord | None) -> dict[str, object]:
    if calendar is None:
        raise ValueError("Calendar does not exist.")
    values = asdict(calendar)
    values.pop("created_at")
    values.pop("updated_at")
    return values


def _record_history(connection: sqlite3.Connection, calendar_id: int, event_type: str,
                    before: dict[str, object], after: dict[str, object]) -> None:
    connection.execute(
        "INSERT INTO calendar_edit_history (calendar_id, event_type, details, created_at) VALUES (?, ?, ?, ?)",
        (calendar_id, event_type, json.dumps({"before": before, "after": after}, sort_keys=True), utc_now()),
    )
