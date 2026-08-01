"""Synchronise Person birthdays as canonical recurring all-day Events."""

from datetime import date
import sqlite3

from app.audit import record_audit_event
from app.db_support import utc_now
from app.event_recurrence import RecurrenceRule, set_recurrence
from app.event_service import get_event
from app.entity_repository import list_entities
from app.entities import DEFINITIONS_BY_TYPE
from app.inbox_repository import resolve_source_items


def sync_all_birthdays(connection: sqlite3.Connection) -> None:
    for person in list_entities(connection, DEFINITIONS_BY_TYPE["person"]):
        sync_person_birthday(connection, person.id, person.title, person.metadata.get("birthday", ""))


def person_for_birthday_event(connection: sqlite3.Connection, event_id: int) -> int | None:
    row = connection.execute(
        "SELECT person_id FROM birthday_event_links WHERE event_id = ?", (event_id,)
    ).fetchone()
    return int(row["person_id"]) if row is not None else None


def sync_person_birthday(connection: sqlite3.Connection, person_id: int, title: str, birthday: str) -> None:
    """Create, update, or archive the one calendar Event sourced by a Person."""
    link = connection.execute("SELECT event_id FROM birthday_event_links WHERE person_id = ?", (person_id,)).fetchone()
    if not birthday:
        if link:
            connection.execute("UPDATE events SET archived_at = ? WHERE entity_id = ?", (utc_now(), link["event_id"]))
            resolve_source_items(connection, "event", int(link["event_id"]))
        return
    try:
        born = date.fromisoformat(birthday)
    except ValueError:
        # Repository fixtures and pre-validation imports may retain an invalid
        # legacy value; the normal Person form prevents it from being saved.
        return
    # The original date is the recurrence anchor, including leap-day semantics.
    start = born.isoformat()
    event_title = f"{title}'s birthday"
    birthday_calendar = connection.execute("SELECT id FROM calendars WHERE kind = 'birthday' AND archived_at = ''").fetchone()
    if birthday_calendar is None:
        raise ValueError("The built-in Birthdays calendar is missing.")
    now = utc_now()
    if link is None:
        cursor = connection.execute("INSERT INTO entities (type, display_name, summary, notes, created_at, updated_at) VALUES ('event', ?, '', '', ?, ?)", (event_title, now, now))
        event_id = int(cursor.lastrowid)
        connection.execute("INSERT INTO events (entity_id, calendar_id, is_all_day, start_date, end_date_exclusive, date_precision, status, archived_at) VALUES (?, ?, 1, ?, date(?, '+1 day'), 'exact', 'planned', '')", (event_id, birthday_calendar["id"], start, start))
        connection.execute("INSERT INTO birthday_event_links (person_id, event_id) VALUES (?, ?)", (person_id, event_id))
        event = get_event(connection, event_id, include_archived=True)
        set_recurrence(connection, event, RecurrenceRule("yearly"), commit=False)
        record_audit_event(connection, "create", [("entity", event_id), ("entity", person_id)], after={"title": event_title, "calendar": "Birthdays"}, notes="Birthday Event synchronised from Person birthday")
    else:
        event_id = int(link["event_id"])
        connection.execute("UPDATE entities SET display_name = ?, updated_at = ? WHERE id = ?", (event_title, now, event_id))
        connection.execute("UPDATE events SET calendar_id = ?, is_all_day = 1, start_utc = '', end_utc = '', start_date = ?, end_date_exclusive = date(?, '+1 day'), timezone = '', date_precision = 'exact', archived_at = '' WHERE entity_id = ?", (birthday_calendar["id"], start, start, event_id))
