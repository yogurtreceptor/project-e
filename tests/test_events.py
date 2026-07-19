import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.audit import list_audit_events
from app.db import (
    connect,
    delete_entity,
    initialise_database,
    restore_entity,
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
from app.entities import DEFINITIONS_BY_SLUG, EVENT_DEFINITION
from app.temporal import TemporalValueError


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
