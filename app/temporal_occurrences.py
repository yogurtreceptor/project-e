"""Shared temporal-occurrence providers for Calendar and reminder projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import sqlite3
from zoneinfo import ZoneInfo

from app.calendar_service import CalendarRecord, list_calendars
from app.calendar_subscription_service import subscription_projection
from app.defaults import PLATFORM_TIMEZONE
from app.entity_repository import list_entities
from app.entities import DEFINITIONS_BY_TYPE
from app.event_recurrence import (
    RecurrenceDefinition,
    get_recurrence,
    occurrence_exceptions,
    occurrences_between,
)
from app.event_service import EventRecord, list_events


@dataclass(frozen=True)
class TemporalOccurrence:
    """One traceable occurrence eligible for reminder attention."""

    source_kind: str
    source_id: int
    occurrence_key: str
    title: str
    due_at: datetime
    attention_expires_at: datetime | None
    context_kind: str
    context_id: int
    destination_kind: str
    persistent: bool = False

    @property
    def context(self) -> tuple[str, int]:
        return self.context_kind, self.context_id


@dataclass(frozen=True)
class CalendarTemporalProjection:
    """Projection-capable occurrences exposed through the shared provider boundary."""

    calendars: tuple[CalendarRecord, ...]
    events: tuple[EventRecord, ...]
    recurrences: dict[int, RecurrenceDefinition]
    recurrence_exceptions: dict[int, dict[str, dict[str, object]]]


@dataclass(frozen=True)
class _EventSource:
    event: EventRecord
    recurrence: RecurrenceDefinition | None
    exceptions: dict[str, dict[str, object]]
    context_kind: str
    context_id: int
    all_day_timezone: str
    external: bool


def calendar_temporal_projection(
    connection: sqlite3.Connection,
) -> CalendarTemporalProjection:
    """Return Calendar-visible local and cached external Event sources."""
    local_calendars = tuple(list_calendars(connection, include_archived=True))
    local_events = tuple(list_events(connection))
    recurrences = {
        event.id: recurrence
        for event in local_events
        if (recurrence := get_recurrence(connection, event.id)) is not None
    }
    exceptions = {
        event_id: occurrence_exceptions(connection, recurrence)
        for event_id, recurrence in recurrences.items()
    }
    external = subscription_projection(connection)
    recurrences.update(external.recurrences)
    return CalendarTemporalProjection(
        (*local_calendars, *external.calendars),
        (*local_events, *external.events),
        recurrences,
        exceptions,
    )


def reminder_occurrences(
    connection: sqlite3.Connection,
    now: datetime,
    *,
    horizon_days: int,
) -> list[TemporalOccurrence]:
    """Project reminder-eligible occurrences from every registered provider."""
    instant = now.astimezone(UTC)
    results: list[TemporalOccurrence] = []
    scan_start = _active_event_scan_start(connection, instant)
    scan_end = instant.date() + timedelta(days=max(1, horizon_days))

    for source in _event_sources(connection):
        event = source.event
        if event.is_cancelled or event.is_archived or event.date_precision != "exact":
            continue
        if source.recurrence is None:
            projected = [(event, _event_occurrence_key(event))]
        else:
            zone = ZoneInfo(event.timezone or source.all_day_timezone)
            local_start = min(scan_start, instant.astimezone(zone).date() - timedelta(days=1))
            projected = [
                (item.event, item.occurrence_date)
                for item in occurrences_between(
                    event,
                    source.recurrence,
                    local_start,
                    scan_end,
                    source.exceptions,
                )
            ]
        for occurrence, occurrence_key in projected:
            due_at, expires_at = _event_boundaries(
                occurrence, source.all_day_timezone
            )
            results.append(
                TemporalOccurrence(
                    "event",
                    event.id,
                    occurrence_key,
                    occurrence.title,
                    due_at,
                    expires_at,
                    source.context_kind,
                    source.context_id,
                    "external_event" if source.external else "event",
                )
            )

    zone = ZoneInfo(PLATFORM_TIMEZONE)
    for document in list_entities(connection, DEFINITIONS_BY_TYPE["document"]):
        expiry = document.metadata.get("expiry_date", "")
        if not expiry:
            continue
        due_at = datetime.combine(
            date.fromisoformat(expiry), datetime.min.time(), zone
        ).replace(hour=9).astimezone(UTC)
        results.append(
            TemporalOccurrence(
                "document_expiry",
                document.id,
                expiry,
                f"{document.title} expires",
                due_at,
                None,
                "global",
                0,
                "document",
                True,
            )
        )
    return results


def _event_sources(connection: sqlite3.Connection) -> list[_EventSource]:
    calendars = {
        calendar.id: calendar
        for calendar in list_calendars(connection, include_archived=True)
    }
    sources: list[_EventSource] = []
    for event in list_events(connection):
        recurrence = get_recurrence(connection, event.id)
        sources.append(
            _EventSource(
                event,
                recurrence,
                occurrence_exceptions(connection, recurrence) if recurrence else {},
                "calendar",
                event.calendar_id,
                calendars[event.calendar_id].timezone,
                False,
            )
        )
    external = subscription_projection(connection)
    external_calendars = {calendar.id: calendar for calendar in external.calendars}
    for event in external.events:
        sources.append(
            _EventSource(
                event,
                external.recurrences.get(event.id),
                {},
                "calendar_subscription",
                -event.calendar_id,
                external_calendars[event.calendar_id].timezone,
                True,
            )
        )
    return sources


def _event_boundaries(
    event: EventRecord, all_day_timezone: str
) -> tuple[datetime, datetime]:
    if not event.is_all_day:
        return _parse_utc(event.start_utc), _parse_utc(event.end_utc)
    zone = ZoneInfo(all_day_timezone or PLATFORM_TIMEZONE)
    due_at = datetime.combine(
        date.fromisoformat(event.start_date), datetime.min.time(), zone
    ).replace(hour=9).astimezone(UTC)
    expires_at = datetime.combine(
        date.fromisoformat(event.end_date_exclusive), datetime.min.time(), zone
    ).astimezone(UTC)
    return due_at, expires_at


def _event_occurrence_key(event: EventRecord) -> str:
    return event.start_date if event.is_all_day else event.start_utc


def _active_event_scan_start(
    connection: sqlite3.Connection, now: datetime
) -> date:
    row = connection.execute(
        """SELECT MIN(due_at) AS earliest
           FROM inbox_items
           WHERE source_kind='event' AND state IN ('active', 'snoozed')"""
    ).fetchone()
    if row is None or not row["earliest"]:
        return now.date() - timedelta(days=1)
    try:
        return _parse_utc(row["earliest"]).date() - timedelta(days=1)
    except ValueError:
        return now.date() - timedelta(days=1)


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
