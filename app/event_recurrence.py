"""Deterministic recurrence definitions and derived Event occurrences."""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
import calendar
import json
import sqlite3
from zoneinfo import ZoneInfo

from app.db_support import utc_now
from app.event_service import EventRecord
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
    connection.commit()
    return RecurrenceDefinition(event.id, rule, version)


def remove_recurrence(connection: sqlite3.Connection, event_id: int) -> bool:
    cursor = connection.execute("DELETE FROM event_recurrences WHERE event_id = ?", (event_id,))
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
    connection.commit()


def exception_dates(connection: sqlite3.Connection, definition: RecurrenceDefinition) -> set[str]:
    return {row["occurrence_date"] for row in connection.execute(
        "SELECT occurrence_date FROM event_recurrence_exceptions WHERE event_id = ? AND recurrence_version = ? AND exception_type = 'cancelled'",
        (definition.event_id, definition.version),
    )}


def occurrences_between(event: EventRecord, definition: RecurrenceDefinition | None, start: date, end: date, cancelled_dates: set[str] | None = None) -> list[EventOccurrence]:
    """Generate only derived instances intersecting an inclusive display range."""
    if definition is None:
        return [EventOccurrence(event, _anchor_date(event).isoformat(), 0)] if _anchor_date(event) <= end else []
    results = []
    cancelled_dates = cancelled_dates or set()
    for occurrence_day in _dates_for_rule(_anchor_date(event), definition.rule, start, end):
        if occurrence_day.isoformat() in cancelled_dates:
            continue
        results.append(EventOccurrence(_event_for_date(event, occurrence_day), occurrence_day.isoformat(), definition.version))
    return results


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
