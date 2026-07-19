"""Deterministic recurrence definitions and derived Event occurrences."""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
import calendar
import json
import sqlite3
from zoneinfo import ZoneInfo

from app.db_support import utc_now
from app.audit import record_audit_event, set_provenance
from app.event_service import EventInput, EventRecord, create_event, normalise_event_input
from app.temporal import normalise_timed_interval


FREQUENCIES = ("daily", "weekly", "monthly", "yearly")


@dataclass(frozen=True)
class RecurrenceRule:
    frequency: str
    interval: int = 1
    weekdays: tuple[int, ...] = ()
    monthly_ordinal: int = 0
    monthly_weekday: int = -1
    until_date: str = ""


@dataclass(frozen=True)
class RecurrenceDefinition:
    event_id: int
    rule: RecurrenceRule
    version: int


@dataclass(frozen=True)
class EventOccurrence:
    event: EventRecord
    occurrence_date: str
    recurrence_version: int


def get_recurrence(connection: sqlite3.Connection, event_id: int) -> RecurrenceDefinition | None:
    row = connection.execute("SELECT * FROM event_recurrences WHERE event_id = ?", (event_id,)).fetchone()
    if row is None:
        return None
    return RecurrenceDefinition(int(row["event_id"]), _rule_from_row(row), int(row["version"]))


def _rule_from_row(row: sqlite3.Row) -> RecurrenceRule:
    return RecurrenceRule(
        row["frequency"], int(row["interval"]), tuple(json.loads(row["weekdays_json"])),
        int(row["monthly_ordinal"]), int(row["monthly_weekday"]), row["until_date"],
    )


def set_recurrence(connection: sqlite3.Connection, event: EventRecord, rule: RecurrenceRule) -> RecurrenceDefinition:
    rule = _normalise_rule(rule, _anchor_date(event))
    current = get_recurrence(connection, event.id)
    now = utc_now()
    version = (current.version + 1) if current else 1
    connection.execute(
        """INSERT INTO event_recurrences (
            event_id, frequency, interval, weekdays_json, monthly_ordinal,
            monthly_weekday, until_date, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET frequency=excluded.frequency,
            interval=excluded.interval, weekdays_json=excluded.weekdays_json,
            monthly_ordinal=excluded.monthly_ordinal,
            monthly_weekday=excluded.monthly_weekday, until_date=excluded.until_date,
            version=excluded.version, updated_at=excluded.updated_at""",
        (event.id, rule.frequency, rule.interval, json.dumps(rule.weekdays), rule.monthly_ordinal,
         rule.monthly_weekday, rule.until_date, version, now, now),
    )
    _record_recurrence_change(
        connection, event.id, "recurrence_set", _definition_snapshot(current),
        _definition_snapshot(RecurrenceDefinition(event.id, rule, version)),
    )
    connection.commit()
    return RecurrenceDefinition(event.id, rule, version)


def remove_recurrence(connection: sqlite3.Connection, event_id: int) -> bool:
    current = get_recurrence(connection, event_id)
    cursor = connection.execute("DELETE FROM event_recurrences WHERE event_id = ?", (event_id,))
    if cursor.rowcount:
        _record_recurrence_change(connection, event_id, "recurrence_removed", _definition_snapshot(current), {})
    connection.commit()
    return bool(cursor.rowcount)


def cancel_occurrence(connection: sqlite3.Connection, definition: RecurrenceDefinition, occurrence_date: str) -> None:
    _validate_occurrence_date(occurrence_date)
    now = utc_now()
    connection.execute(
        """INSERT INTO event_recurrence_exceptions (
            event_id, occurrence_date, recurrence_version, exception_type, created_at, updated_at
        ) VALUES (?, ?, ?, 'cancelled', ?, ?)
        ON CONFLICT(event_id, occurrence_date, recurrence_version) DO UPDATE SET
            exception_type='cancelled', override_json='', updated_at=excluded.updated_at""",
        (definition.event_id, occurrence_date, definition.version, now, now),
    )
    _record_recurrence_change(
        connection, definition.event_id, "occurrence_cancelled", {},
        {"occurrence_date": occurrence_date, "recurrence_version": definition.version, "scope": "this"},
    )
    connection.commit()


def exception_dates(connection: sqlite3.Connection, definition: RecurrenceDefinition) -> set[str]:
    return {row["occurrence_date"] for row in connection.execute(
        "SELECT occurrence_date FROM event_recurrence_exceptions WHERE event_id = ? AND recurrence_version = ? AND exception_type = 'cancelled'",
        (definition.event_id, definition.version),
    )}


def occurrence_exceptions(connection: sqlite3.Connection, definition: RecurrenceDefinition) -> dict[str, dict[str, object]]:
    """Return the current-version cancellation and override records by occurrence date."""
    results: dict[str, dict[str, object]] = {}
    for row in connection.execute(
        "SELECT occurrence_date, exception_type, override_json FROM event_recurrence_exceptions WHERE event_id = ? AND recurrence_version = ?",
        (definition.event_id, definition.version),
    ):
        results[row["occurrence_date"]] = {
            "type": row["exception_type"],
            "override": json.loads(row["override_json"]) if row["override_json"] else {},
        }
    return results


def override_occurrence(connection: sqlite3.Connection, event: EventRecord, definition: RecurrenceDefinition, occurrence_date: str, values: EventInput) -> None:
    """Persist one edited occurrence without mutating its canonical source Event."""
    occurrence = _require_occurrence(event, definition, occurrence_date)
    normalised = normalise_event_input(connection, values, current_calendar_id=occurrence.calendar_id, current_status=occurrence.status)
    payload = _override_payload(normalised)
    now = utc_now()
    connection.execute(
        """INSERT INTO event_recurrence_exceptions (
            event_id, occurrence_date, recurrence_version, exception_type, override_json, created_at, updated_at
        ) VALUES (?, ?, ?, 'override', ?, ?, ?)
        ON CONFLICT(event_id, occurrence_date, recurrence_version) DO UPDATE SET
            exception_type='override', override_json=excluded.override_json, updated_at=excluded.updated_at""",
        (event.id, occurrence_date, definition.version, json.dumps(payload, sort_keys=True), now, now),
    )
    _record_recurrence_change(
        connection, event.id, "occurrence_overridden", {},
        {"occurrence_date": occurrence_date, "recurrence_version": definition.version, "scope": "this", "override": payload},
    )
    connection.commit()


def split_series(connection: sqlite3.Connection, event: EventRecord, definition: RecurrenceDefinition, split_date: str, successor_rule: RecurrenceRule | None = None, successor_input: EventInput | None = None) -> int:
    """End a source series before one occurrence and create its traceable successor."""
    split_day = date.fromisoformat(split_date)
    generated = [item.occurrence_date for item in occurrences_between(event, definition, _anchor_date(event), split_day)]
    if split_date not in generated or split_day == _anchor_date(event):
        raise ValueError("Series can be split only at a later generated occurrence.")
    prior_day = date.fromisoformat(generated[-2])
    source_rule = RecurrenceRule(**{**definition.rule.__dict__, "until_date": prior_day.isoformat()})
    set_recurrence(connection, event, source_rule)
    occurrence = _event_for_date(event, split_day)
    if successor_input is not None:
        successor_id = create_event(connection, successor_input)
    elif occurrence.is_all_day:
        successor_input = EventInput(occurrence.title, True, occurrence.calendar_id, occurrence.notes,
            start_date=occurrence.start_date,
            end_date=(date.fromisoformat(occurrence.end_date_exclusive) - timedelta(days=1)).isoformat(),
            date_precision=occurrence.date_precision)
        successor_id = create_event(connection, successor_input)
    else:
        successor_input = EventInput(occurrence.title, False, occurrence.calendar_id, occurrence.notes,
            occurrence.timezone, _local_value(occurrence.start_utc, occurrence.timezone),
            _local_value(occurrence.end_utc, occurrence.timezone), date_precision=occurrence.date_precision)
        successor_id = create_event(connection, successor_input)
    successor = connection.execute("SELECT entity.*, event.* FROM entities entity JOIN events event ON event.entity_id=entity.id WHERE entity.id=?", (successor_id,)).fetchone()
    successor_event = EventRecord(int(successor["id"]), successor["display_name"], successor["notes"], int(successor["calendar_id"]), bool(successor["is_all_day"]), successor["start_utc"], successor["end_utc"], successor["start_date"], successor["end_date_exclusive"], successor["timezone"], successor["date_precision"], successor["status"], successor["archived_at"], successor["deleted_at"], successor["created_at"], successor["updated_at"])
    rule = successor_rule or definition.rule
    set_recurrence(connection, successor_event, RecurrenceRule(**{**rule.__dict__, "until_date": rule.until_date}))
    connection.execute("INSERT INTO event_recurrence_splits (source_event_id, successor_event_id, split_occurrence_date, created_at) VALUES (?, ?, ?, ?)", (event.id, successor_id, split_date, utc_now()))
    _record_recurrence_change(
        connection, event.id, "series_split", {},
        {"occurrence_date": split_date, "scope": "this_and_following", "successor_event_id": successor_id},
    )
    connection.commit()
    return successor_id


def truncate_series(connection: sqlite3.Connection, event: EventRecord, definition: RecurrenceDefinition, occurrence_date: str) -> None:
    """End a series before the chosen occurrence without creating a successor."""
    split_day = date.fromisoformat(occurrence_date)
    generated = [item.occurrence_date for item in occurrences_between(event, definition, _anchor_date(event), split_day)]
    if occurrence_date not in generated:
        raise ValueError("Occurrence is not part of this Event series.")
    if split_day == _anchor_date(event):
        remove_recurrence(connection, event.id)
        return
    prior_day = generated[-2]
    set_recurrence(connection, event, RecurrenceRule(**{**definition.rule.__dict__, "until_date": prior_day}))
    _record_recurrence_change(connection, event.id, "series_truncated", {}, {"occurrence_date": occurrence_date, "scope": "this_and_following"})
    connection.commit()


def is_series_anchor(event: EventRecord, occurrence_date: str) -> bool:
    return _anchor_date(event).isoformat() == occurrence_date


def occurrences_between(event: EventRecord, definition: RecurrenceDefinition | None, start: date, end: date, exceptions: set[str] | dict[str, dict[str, object]] | None = None) -> list[EventOccurrence]:
    """Generate only derived instances intersecting an inclusive display range."""
    if definition is None:
        return [EventOccurrence(event, _anchor_date(event).isoformat(), 0)] if _anchor_date(event) <= end else []
    results = []
    exceptions = exceptions or {}
    for occurrence_day in _dates_for_rule(_anchor_date(event), definition.rule, start, end):
        exception = _exception_for_date(exceptions, occurrence_day.isoformat())
        if exception and exception.get("type") == "cancelled":
            continue
        occurrence = _event_for_date(event, occurrence_day)
        if exception and exception.get("type") == "override":
            occurrence = _event_with_override(occurrence, exception.get("override", {}))
        results.append(EventOccurrence(occurrence, occurrence_day.isoformat(), definition.version))
    return results


def _exception_for_date(exceptions: set[str] | dict[str, dict[str, object]], occurrence_date: str) -> dict[str, object] | None:
    if isinstance(exceptions, set):
        return {"type": "cancelled"} if occurrence_date in exceptions else None
    return exceptions.get(occurrence_date)


def _require_occurrence(event: EventRecord, definition: RecurrenceDefinition, occurrence_date: str) -> EventRecord:
    _validate_occurrence_date(occurrence_date)
    target = date.fromisoformat(occurrence_date)
    occurrences = occurrences_between(event, definition, target, target)
    if not occurrences:
        raise ValueError("Occurrence is not part of this Event series.")
    return occurrences[0].event


def _override_payload(values: dict[str, object]) -> dict[str, object]:
    return {key: values[key] for key in ("title", "notes", "calendar_id", "is_all_day", "start_utc", "end_utc", "start_date", "end_date_exclusive", "timezone", "date_precision")}


def _event_with_override(event: EventRecord, values: object) -> EventRecord:
    if not isinstance(values, dict):
        return event
    return replace(event, title=str(values.get("title", event.title)), notes=str(values.get("notes", event.notes)),
                   calendar_id=int(values.get("calendar_id", event.calendar_id)), is_all_day=bool(values.get("is_all_day", event.is_all_day)),
                   start_utc=str(values.get("start_utc", event.start_utc)), end_utc=str(values.get("end_utc", event.end_utc)),
                   start_date=str(values.get("start_date", event.start_date)), end_date_exclusive=str(values.get("end_date_exclusive", event.end_date_exclusive)),
                   timezone=str(values.get("timezone", event.timezone)), date_precision=str(values.get("date_precision", event.date_precision)))


def _definition_snapshot(definition: RecurrenceDefinition | None) -> dict[str, object]:
    if definition is None:
        return {}
    return {"version": definition.version, **definition.rule.__dict__}


def _record_recurrence_change(connection: sqlite3.Connection, event_id: int, event_type: str, before: object, after: object) -> None:
    details = json.dumps({"before": before, "after": after}, sort_keys=True)
    connection.execute("INSERT INTO entity_edit_history (entity_id, event_type, details, created_at) VALUES (?, ?, ?, ?)", (event_id, event_type, details, utc_now()))
    record_audit_event(connection, "edit", [("entity", event_id)], before=before, after=after, notes=event_type.replace("_", " ").capitalize())
    set_provenance(connection, "entity", event_id, "recurrence", "manual")


def _normalise_rule(rule: RecurrenceRule, anchor: date) -> RecurrenceRule:
    if rule.frequency not in FREQUENCIES:
        raise ValueError("Recurrence frequency is invalid.")
    if rule.interval < 1:
        raise ValueError("Recurrence interval must be positive.")
    weekdays = tuple(sorted(set(rule.weekdays)))
    if any(day not in range(7) for day in weekdays):
        raise ValueError("Recurrence weekdays must be Monday through Sunday.")
    if rule.monthly_ordinal and rule.monthly_ordinal not in (-1, 1, 2, 3, 4, 5):
        raise ValueError("Monthly ordinal must be first through fifth or last.")
    if rule.monthly_ordinal and rule.monthly_weekday not in range(7):
        raise ValueError("Ordinal monthly recurrence requires a weekday.")
    if rule.until_date:
        try:
            until = date.fromisoformat(rule.until_date)
        except ValueError:
            raise ValueError("Recurrence end date must be a valid ISO date.") from None
        if until < anchor:
            raise ValueError("Recurrence end date cannot precede the first Event.")
    return RecurrenceRule(rule.frequency, rule.interval, weekdays, rule.monthly_ordinal, rule.monthly_weekday, rule.until_date)


def _validate_occurrence_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError:
        raise ValueError("Occurrence date must be a valid ISO date.") from None


def _dates_for_rule(anchor: date, rule: RecurrenceRule, start: date, end: date):
    until = date.fromisoformat(rule.until_date) if rule.until_date else end
    limit = min(end, until)
    if limit < anchor:
        return
    current = anchor
    # Calendar views request bounded ranges; this simple progression stays deterministic.
    while current <= limit:
        if current >= start and _matches(current, anchor, rule):
            yield current
        current += timedelta(days=1)


def _matches(current: date, anchor: date, rule: RecurrenceRule) -> bool:
    days = (current - anchor).days
    if rule.frequency == "daily":
        return days % rule.interval == 0
    if rule.frequency == "weekly":
        weekdays = rule.weekdays or (anchor.weekday(),)
        return days // 7 % rule.interval == 0 and current.weekday() in weekdays
    if rule.frequency == "monthly":
        months = (current.year - anchor.year) * 12 + current.month - anchor.month
        return months >= 0 and months % rule.interval == 0 and _matches_month_day(current, anchor, rule)
    years = current.year - anchor.year
    return years >= 0 and years % rule.interval == 0 and current.month == anchor.month and current.day == min(anchor.day, calendar.monthrange(current.year, current.month)[1])


def _matches_month_day(current: date, anchor: date, rule: RecurrenceRule) -> bool:
    if rule.monthly_ordinal:
        return current == _ordinal_weekday(current.year, current.month, rule.monthly_weekday, rule.monthly_ordinal)
    return current.day == min(anchor.day, calendar.monthrange(current.year, current.month)[1])


def _ordinal_weekday(year: int, month: int, weekday: int, ordinal: int) -> date:
    if ordinal == -1:
        value = date(year, month, calendar.monthrange(year, month)[1])
        return value - timedelta(days=(value.weekday() - weekday) % 7)
    value = date(year, month, 1) + timedelta(days=(weekday - date(year, month, 1).weekday()) % 7 + (ordinal - 1) * 7)
    return value if value.month == month else _ordinal_weekday(year, month, weekday, -1)


def _anchor_date(event: EventRecord) -> date:
    if event.is_all_day:
        return date.fromisoformat(event.start_date)
    return datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(ZoneInfo(event.timezone)).date()


def _event_for_date(event: EventRecord, occurrence_day: date) -> EventRecord:
    anchor = _anchor_date(event)
    if event.is_all_day:
        span = date.fromisoformat(event.end_date_exclusive) - date.fromisoformat(event.start_date)
        return replace(event, start_date=occurrence_day.isoformat(), end_date_exclusive=(occurrence_day + span).isoformat())
    zone = ZoneInfo(event.timezone)
    original_start = datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    original_end = datetime.fromisoformat(event.end_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    start_local = datetime.combine(occurrence_day, original_start.timetz().replace(tzinfo=None))
    end_local = start_local + (original_end.replace(tzinfo=None) - original_start.replace(tzinfo=None))
    interval = normalise_timed_interval(start_local.isoformat(timespec="minutes"), end_local.isoformat(timespec="minutes"), event.timezone)
    return replace(event, start_utc=interval.start_utc, end_utc=interval.end_utc)


def _local_value(utc_value: str, timezone_name: str) -> str:
    return datetime.fromisoformat(utc_value.removesuffix("Z") + "+00:00").astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%dT%H:%M")
