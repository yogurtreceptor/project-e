import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.audit import list_audit_events
from app.db import connect, initialise_database
from app.entity_merge import list_entity_history
from app.event_service import (
    EventInput,
    archive_event,
    create_event,
    get_event,
    list_events,
    unarchive_event,
    update_event,
)
from app.entities import DEFINITIONS_BY_SLUG
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

    def test_update_can_change_temporal_mode_and_records_history(self) -> None:
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
            EventInput(
                title="Conference day",
                all_day=True,
                start_date="2026-09-02",
                end_date="2026-09-02",
                status="cancelled",
            ),
        )

        event = get_event(self.connection, event_id)
        history = list_entity_history(self.connection, event_id)
        audits = list_audit_events(self.connection, "entity", event_id)
        details = json.loads(history[0]["details"])
        self.assertEqual("Conference day", event.title)
        self.assertTrue(event.is_all_day)
        self.assertTrue(event.is_cancelled)
        self.assertEqual("Conference", details["before"]["title"])
        self.assertEqual("Conference day", details["after"]["title"])
        self.assertEqual(["edit", "create"], [audit.action for audit in audits])

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

    def test_archived_reference_can_be_retained_but_not_newly_selected(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Existing",
                all_day=True,
                start_date="2026-02-01",
                end_date="2026-02-01",
            ),
        )
        event = get_event(self.connection, event_id)
        self.connection.execute(
            "UPDATE event_categories SET archived_at = 'archived' WHERE id = ?",
            (event.category_id,),
        )
        self.connection.commit()

        update_event(
            self.connection,
            event_id,
            EventInput(
                title="Existing renamed",
                all_day=True,
                category_id=event.category_id,
                start_date="2026-02-01",
                end_date="2026-02-01",
            ),
        )
        with self.assertRaisesRegex(ValueError, "Archived event category"):
            create_event(
                self.connection,
                EventInput(
                    title="New",
                    all_day=True,
                    category_id=event.category_id,
                    start_date="2026-02-02",
                    end_date="2026-02-02",
                ),
            )

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


if __name__ == "__main__":
    unittest.main()
