import json
import http.client
import sqlite3
import tempfile
import threading
from datetime import date
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.audit import list_audit_events
from app.db import (
    connect,
    create_entity,
    create_relationship,
    delete_entity,
    get_entity,
    initialise_database,
    list_relationships_for_entity,
    restore_entity,
    search_entities,
)
from app.db_schema import (
    create_entity_table,
    create_initial_event_table,
    create_initial_temporal_foundation_tables,
    create_schema,
    create_schema_migration_table,
)
from app.entity_merge import list_entity_history
from app.event_service import (
    EventInput,
    EventSchedule,
    EventUpdate,
    archive_event,
    cancel_event,
    create_event,
    get_event,
    list_events,
    reinstate_event,
    reschedule_event,
    unarchive_event,
    update_event,
)
from app.event_recurrence import RecurrenceRule, cancel_occurrence, exception_dates, get_recurrence, occurrences_between, set_recurrence, split_series
from app.entities import DEFINITIONS_BY_SLUG, DEFINITIONS_BY_TYPE, EVENT_DEFINITION
from app.temporal import TemporalValueError
from app import views
from app.calendar_service import CalendarInput, create_calendar, get_calendar
from app.web import EddyRequestHandler, ThreadingHTTPServer


class EventServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "events.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_create_timed_event_uses_defaults_and_normalises_to_utc(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="  Dentist  ",
                notes="  Annual check-up  ",
                all_day=False,
                start_local="2026-08-01T09:00",
                end_local="2026-08-01T10:00",
            ),
        )

        event = get_event(self.connection, event_id)

        self.assertEqual("Dentist", event.title)
        self.assertEqual("Annual check-up", event.notes)
        self.assertEqual("2026-07-31T23:00:00Z", event.start_utc)
        self.assertEqual("2026-08-01T00:00:00Z", event.end_utc)
        self.assertEqual("Australia/Brisbane", event.timezone)
        self.assertFalse(event.is_all_day)
        self.assertEqual("", event.start_date)
        self.assertNotIn("events", DEFINITIONS_BY_SLUG)

    def test_create_all_day_event_persists_date_boundaries_only(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Regional holiday",
                all_day=True,
                start_date="2026-08-10",
                end_date="2026-08-12",
                date_precision="approximate",
            ),
        )

        event = get_event(self.connection, event_id)

        self.assertTrue(event.is_all_day)
        self.assertEqual("2026-08-10", event.start_date)
        self.assertEqual("2026-08-13", event.end_date_exclusive)
        self.assertEqual("", event.start_utc)
        self.assertEqual("", event.timezone)
        self.assertEqual("approximate", event.date_precision)

    def test_event_uses_standard_relationships_with_multiple_peer_entities(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Project kickoff", all_day=False, start_local="2026-08-10T09:00", end_local="2026-08-10T10:00"))
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {"given_name": "Ada", "middle_name": "", "family_name": "", "sex": "Unknown", "birthday": "", "email": "", "phone": "", "display_name": "", "summary": "", "notes": ""})
        location_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["location"], {"display_name": "Meeting room", "summary": "", "notes": ""})
        project_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["project"], {"display_name": "Launch", "summary": "", "notes": "", "project_type": "", "status": "Active", "started_at": "", "target_date": "", "ended_at": ""})

        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(person_id), "type": "event_involves_person"})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(location_id), "type": "event_at_location"})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(project_id), "type": "event_related_to_project"})
        self.connection.commit()

        event_relationships = list_relationships_for_entity(self.connection, event_id)
        self.assertEqual({"event_involves_person", "event_at_location", "event_related_to_project"}, {relationship.type_key for relationship in event_relationships})
        self.assertEqual({person_id, location_id, project_id}, {relationship.other_entity(event_id).id for relationship in event_relationships})
        self.assertEqual("involved in", list_relationships_for_entity(self.connection, person_id)[0].label_from(person_id))

    def test_event_search_and_related_record_projection_use_shared_conventions(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Project kickoff", notes="Discuss launch plan", all_day=False, start_local="2026-08-10T09:00", end_local="2026-08-10T10:00"))
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {"given_name": "Ada", "middle_name": "", "family_name": "", "sex": "Unknown", "birthday": "", "email": "", "phone": "", "display_name": "", "summary": "", "notes": ""})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(person_id), "type": "event_involves_person"})

        event_results = search_entities(self.connection, "kickoff", entity_type="event")
        relationship_results = search_entities(self.connection, "Ada")
        person_record = get_entity(
            self.connection, DEFINITIONS_BY_TYPE["person"], person_id
        )
        relationships = list_relationships_for_entity(self.connection, person_id)
        event = get_event(self.connection, event_id)
        calendar = get_calendar(self.connection, event.calendar_id)

        self.assertEqual([event_id], [result["entity"].id for result in event_results])
        self.assertIn(event_id, {result["entity"].id for result in relationship_results})
        self.assertIn(f'href="/events/{event_id}"', views.entity_detail_page(person_record, relationships))
        projection = views.event_projection_page(event, calendar, list_relationships_for_entity(self.connection, event_id), [], [])
        self.assertIn("Project kickoff", projection)
        self.assertIn("Australia/Brisbane", projection)
        self.assertIn("Ada", projection)
        self.assertNotIn("/events/new", projection)

    def test_event_projection_route_is_read_only(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Read-only event", all_day=True, start_date="2026-08-10", end_date="2026-08-10"))
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", f"/events/{event_id}")
            response = client.getresponse()
            page = response.read().decode()
            self.assertEqual(200, response.status)
            self.assertIn("Read-only event", page)
            self.assertNotIn("/events/new", page)
            client.request("GET", "/events")
            self.assertEqual(404, client.getresponse().status)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_calendar_originates_event_creation_and_editing(self) -> None:
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", "/calendar")
            page = client.getresponse().read().decode()
            self.assertIn('href="/calendar/events/new"', page)
            self.assertNotIn("Current Events", page)
            client.request("GET", "/calendar/events/new")
            form_page = client.getresponse().read().decode()
            self.assertIn('action="/calendar/events/new"', form_page)
            self.assertIn("data-event-all-day", form_page)

            create_body = urlencode({
                "title": "Calendar-created Event", "calendar_id": "1",
                "start_date": "2026-09-10", "end_date": "2026-09-10",
                "start_local": "2026-09-10T09:00", "end_local": "2026-09-10T10:00",
                "timezone": "Australia/Brisbane", "notes": "Created in Calendar",
            })
            client.request("POST", "/calendar/events/new", create_body, {
                "Content-Type": "application/x-www-form-urlencoded",
            })
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar?created=1", response.getheader("Location"))

            client.request("GET", "/calendar/events/1/edit")
            edit_page = client.getresponse().read().decode()
            self.assertIn('value="2026-09-10T09:00"', edit_page)
            self.assertIn("add a relationship", edit_page)

            edit_body = urlencode({
                "title": "Calendar-edited Event", "calendar_id": "1",
                "start_date": "2026-09-11", "end_date": "2026-09-11",
                "start_local": "2026-09-11T11:00", "end_local": "2026-09-11T12:00",
                "timezone": "Australia/Brisbane", "notes": "Rescheduled in Calendar",
            })
            client.request("POST", "/calendar/events/1/edit", edit_body, {
                "Content-Type": "application/x-www-form-urlencoded",
            })
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar/events/1/edit?saved=1", response.getheader("Location"))
            event = get_event(self.connection, 1)
            self.assertEqual("Calendar-edited Event", event.title)
            self.assertEqual("2026-09-11T01:00:00Z", event.start_utc)
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_calendar_renders_month_week_filters_and_event_preview(self) -> None:
        work_calendar_id = create_calendar(
            self.connection, CalendarInput("Work", "#EF4444", "Europe/London")
        )
        all_day_id = create_event(
            self.connection,
            EventInput("Conference", True, start_date="2026-09-14", end_date="2026-09-16"),
        )
        create_event(
            self.connection,
            EventInput(
                "London call", False, work_calendar_id,
                timezone="Europe/London", start_local="2026-09-15T09:00",
                end_local="2026-09-15T10:00",
            ),
        )
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            client.request("GET", "/calendar?view=month&date=2026-09-15")
            month_page = client.getresponse().read().decode()
            self.assertIn("September 2026", month_page)
            self.assertIn("Conference", month_page)
            self.assertIn("18:00 · </span>London call", month_page)
            self.assertIn("Visible Calendars", month_page)

            client.request("GET", "/calendar?view=month&date=2026-09-15&calendars=1")
            filtered_page = client.getresponse().read().decode()
            self.assertNotIn("--calendar-colour:#EF4444", filtered_page)

            client.request("GET", "/calendar?view=week&date=2026-09-15")
            week_page = client.getresponse().read().decode()
            self.assertIn("Week of 14 September 2026", week_page)
            self.assertIn("calendar-week-grid", week_page)

            client.request("GET", f"/calendar?view=month&date=2026-09-15&preview={all_day_id}")
            preview_page = client.getresponse().read().decode()
            self.assertIn("Event preview", preview_page)
            self.assertIn(f'/calendar/events/{all_day_id}/delete', preview_page)

            client.request("POST", f"/calendar/events/{all_day_id}/delete")
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar", response.getheader("Location"))
            self.assertIsNone(get_event(self.connection, all_day_id))
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_monthly_recurrence_projects_clamped_dates_without_duplicate_events(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput("Month end", True, start_date="2026-01-31", end_date="2026-01-31"),
        )
        event = get_event(self.connection, event_id)
        definition = set_recurrence(
            self.connection, event, RecurrenceRule("monthly", until_date="2026-04-30")
        )
        occurrences = occurrences_between(event, definition, date(2026, 1, 1), date(2026, 5, 1))
        self.assertEqual(
            ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
            [item.occurrence_date for item in occurrences],
        )
        self.assertEqual(1, self.connection.execute("SELECT COUNT(*) FROM entities WHERE type = 'event'").fetchone()[0])

        cancel_occurrence(self.connection, definition, "2026-03-31")
        remaining = occurrences_between(event, definition, date(2026, 1, 1), date(2026, 5, 1), exception_dates(self.connection, definition))
        self.assertNotIn("2026-03-31", [item.occurrence_date for item in remaining])

    def test_split_series_creates_traceable_successor(self) -> None:
        event_id = create_event(self.connection, EventInput("Stand-up", True, start_date="2026-01-05", end_date="2026-01-05"))
        event = get_event(self.connection, event_id)
        definition = set_recurrence(self.connection, event, RecurrenceRule("weekly"))
        successor_id = split_series(self.connection, event, definition, "2026-01-19")
        source = get_recurrence(self.connection, event_id)
        successor = get_event(self.connection, successor_id)
        self.assertEqual("2026-01-12", source.rule.until_date)
        self.assertEqual("2026-01-19", successor.start_date)
        self.assertIsNotNone(get_recurrence(self.connection, successor_id))
        self.assertEqual((event_id, successor_id, "2026-01-19"), tuple(self.connection.execute("SELECT source_event_id, successor_event_id, split_occurrence_date FROM event_recurrence_splits").fetchone()))

    def test_create_rejects_invalid_time_and_rolls_back_identity(self) -> None:
        with self.assertRaises(TemporalValueError):
            create_event(
                self.connection,
                EventInput(
                    title="Invalid",
                    all_day=False,
                    timezone="Australia/Sydney",
                    start_local="2026-10-04T02:30",
                    end_local="2026-10-04T03:30",
                ),
            )

        count = self.connection.execute(
            "SELECT COUNT(*) FROM entities WHERE type = 'event'"
        ).fetchone()[0]
        self.assertEqual(0, count)

    def test_update_changes_details_without_rescheduling(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Conference",
                all_day=False,
                start_local="2026-09-01T09:00",
                end_local="2026-09-01T10:00",
            ),
        )

        update_event(
            self.connection,
            event_id,
            EventUpdate(
                title="Conference day",
                notes="Updated details",
            ),
        )

        event = get_event(self.connection, event_id)
        history = list_entity_history(self.connection, event_id)
        audits = list_audit_events(self.connection, "entity", event_id)
        details = json.loads(history[0]["details"])
        self.assertEqual("Conference day", event.title)
        self.assertFalse(event.is_all_day)
        self.assertFalse(event.is_cancelled)
        self.assertEqual("Conference", details["before"]["title"])
        self.assertEqual("Conference day", details["after"]["title"])
        self.assertEqual(["edit", "create"], [audit.action for audit in audits])

    def test_cancel_reinstate_and_reschedule_are_dedicated_operations(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Conference",
                all_day=False,
                start_local="2026-09-01T09:00",
                end_local="2026-09-01T10:00",
            ),
        )

        self.assertTrue(cancel_event(self.connection, event_id))
        self.assertFalse(cancel_event(self.connection, event_id))
        self.assertTrue(get_event(self.connection, event_id).is_cancelled)
        self.assertTrue(reinstate_event(self.connection, event_id))
        self.assertFalse(reinstate_event(self.connection, event_id))
        self.assertTrue(
            reschedule_event(
                self.connection,
                event_id,
                EventSchedule(
                    all_day=True,
                    start_date="2026-09-02",
                    end_date="2026-09-02",
                ),
            )
        )
        event = get_event(self.connection, event_id)
        self.assertTrue(event.is_all_day)
        self.assertEqual("2026-09-02", event.start_date)
        actions = [
            audit.action
            for audit in list_audit_events(self.connection, "entity", event_id)
        ]
        self.assertEqual(
            ["reschedule", "reinstate", "cancel", "create"], actions
        )

    def test_archive_is_distinct_recoverable_state(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Old plan",
                all_day=True,
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        )

        self.assertTrue(archive_event(self.connection, event_id))
        self.assertFalse(archive_event(self.connection, event_id))
        self.assertIsNone(get_event(self.connection, event_id))
        archived = get_event(self.connection, event_id, include_archived=True)
        self.assertTrue(archived.is_archived)
        self.assertEqual("", archived.deleted_at)
        self.assertEqual([], list_events(self.connection))
        self.assertEqual(1, len(list_events(self.connection, include_archived=True)))

        self.assertTrue(unarchive_event(self.connection, event_id))
        self.assertFalse(unarchive_event(self.connection, event_id))
        self.assertIsNotNone(get_event(self.connection, event_id))
        history_types = [
            row["event_type"] for row in list_entity_history(self.connection, event_id)
        ]
        self.assertEqual(["unarchive", "archive"], history_types)
        audit_actions = [
            event.action
            for event in list_audit_events(self.connection, "entity", event_id)
        ]
        self.assertEqual(["unarchive", "archive", "create"], audit_actions)

    def test_archived_calendar_can_be_retained_but_not_newly_selected(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Existing",
                all_day=True,
                start_date="2026-02-01",
                end_date="2026-02-01",
            ),
        )
        self.connection.execute(
            "UPDATE calendars SET archived_at = 'archived' WHERE is_default = 1"
        )
        self.connection.commit()

        update_event(
            self.connection,
            event_id,
            EventUpdate(
                title="Existing renamed",
            ),
        )
        with self.assertRaisesRegex(ValueError, "default calendar"):
            create_event(
                self.connection,
                EventInput(
                    title="New",
                    all_day=True,
                    start_date="2026-02-02",
                    end_date="2026-02-02",
                ),
            )

    def test_recycle_bin_restore_preserves_archive_and_cancellation(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Preserved state",
                all_day=True,
                start_date="2026-04-01",
                end_date="2026-04-01",
            ),
        )
        cancel_event(self.connection, event_id)
        archive_event(self.connection, event_id)

        delete_entity(self.connection, EVENT_DEFINITION, event_id)
        self.assertTrue(restore_entity(self.connection, event_id))

        event = get_event(self.connection, event_id, include_archived=True)
        self.assertTrue(event.is_archived)
        self.assertTrue(event.is_cancelled)

    def test_database_constraints_keep_temporal_modes_exclusive(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Constrained",
                all_day=True,
                start_date="2026-03-01",
                end_date="2026-03-01",
            ),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "UPDATE events SET start_utc = '2026-03-01T00:00:00Z' "
                "WHERE entity_id = ?",
                (event_id,),
            )
        self.connection.rollback()

    def test_corrective_migration_preserves_existing_event_identity_and_state(
        self,
    ) -> None:
        legacy_path = Path(self.directory.name) / "legacy-events.sqlite3"
        with connect(legacy_path) as connection:
            create_entity_table(connection)
            create_initial_temporal_foundation_tables(connection)
            create_initial_event_table(connection)
            create_schema_migration_table(connection)
            connection.executemany(
                """
                INSERT INTO schema_migrations (migration_id, applied_at)
                VALUES (?, 'already-applied')
                """,
                (
                    ("20260719_16_temporal_foundation",),
                    ("20260719_17_canonical_events",),
                ),
            )
            connection.execute(
                """
                INSERT INTO entities (
                    id, type, display_name, summary, notes,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    41, 'event', 'Legacy Event', '', '',
                    'created', 'updated', ''
                )
                """
            )
            calendar_id = connection.execute(
                "SELECT id FROM calendars WHERE is_default = 1"
            ).fetchone()[0]
            category_id = connection.execute(
                "SELECT id FROM event_categories WHERE is_default = 1"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO events (
                    entity_id, calendar_id, category_id, is_all_day,
                    start_date, end_date_exclusive, date_precision,
                    status, archived_at
                ) VALUES (
                    41, ?, ?, 1, '2026-05-01', '2026-05-02',
                    'exact', 'cancelled', 'archived'
                )
                """,
                (calendar_id, category_id),
            )
            create_schema(connection)
            columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(events)"
                )
            }
            category_table = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'event_categories'
                """
            ).fetchone()
            event = connection.execute(
                "SELECT * FROM events WHERE entity_id = 41"
            ).fetchone()
            calendar = connection.execute(
                "SELECT * FROM calendars WHERE id = ?", (calendar_id,)
            ).fetchone()
        self.assertNotIn("category_id", columns)
        self.assertIsNone(category_table)
        self.assertEqual("cancelled", event["status"])
        self.assertEqual("archived", event["archived_at"])
        self.assertEqual(calendar_id, event["calendar_id"])
        self.assertEqual("General", calendar["name"])


if __name__ == "__main__":
    unittest.main()
