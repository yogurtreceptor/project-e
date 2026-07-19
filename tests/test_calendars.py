import json
import tempfile
import unittest
from pathlib import Path

from app.audit import get_provenance, list_audit_events
from app.calendar_service import (
    CalendarInput,
    archive_calendar,
    create_calendar,
    delete_calendar,
    get_calendar,
    list_calendar_history,
    list_calendars,
    rename_calendar,
    set_default_calendar,
    unarchive_calendar,
    update_calendar,
)
from app.db import connect, initialise_database
from app.db_schema import create_schema
from app.event_service import EventInput, EventUpdate, create_event, get_event, update_event


class CalendarServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "calendars.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)
        self.general_id = self.connection.execute(
            "SELECT id FROM calendars WHERE is_default = 1"
        ).fetchone()[0]

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_create_retrieve_update_and_history(self) -> None:
        calendar_id = create_calendar(
            self.connection,
            CalendarInput(" Work ", "#10B981", "Australia/Sydney", 45, 8),
        )
        self.assertEqual(["General", "Work"], [item.name for item in list_calendars(self.connection)])
        self.assertEqual("Work", get_calendar(self.connection, calendar_id).name)
        self.assertTrue(rename_calendar(self.connection, calendar_id, "Office"))
        self.assertTrue(update_calendar(
            self.connection, calendar_id,
            CalendarInput("Office", "#EF4444", "Europe/London", 30, -2),
        ))
        calendar = get_calendar(self.connection, calendar_id)
        self.assertEqual(("Office", "#EF4444", "Europe/London", 30, -2),
                         (calendar.name, calendar.colour, calendar.timezone,
                          calendar.default_event_duration_minutes, calendar.sort_order))
        history = list_calendar_history(self.connection, calendar_id)
        self.assertEqual(["edit", "edit"], [row["event_type"] for row in history])
        self.assertEqual("Office", json.loads(history[0]["details"])["after"]["name"])
        self.assertEqual("manual", get_provenance(self.connection, "calendar", calendar_id)["timezone"])

    def test_default_must_be_active_before_archiving(self) -> None:
        work_id = create_calendar(self.connection, CalendarInput("Work"))
        with self.assertRaisesRegex(ValueError, "another active Calendar"):
            archive_calendar(self.connection, self.general_id)
        self.assertTrue(set_default_calendar(self.connection, work_id))
        self.assertFalse(set_default_calendar(self.connection, work_id))
        self.assertTrue(archive_calendar(self.connection, self.general_id))
        self.assertIsNone(get_calendar(self.connection, self.general_id))
        self.assertTrue(get_calendar(self.connection, self.general_id, include_archived=True).is_archived)
        self.assertTrue(unarchive_calendar(self.connection, self.general_id))
        self.assertFalse(unarchive_calendar(self.connection, self.general_id))
        self.assertEqual(["General", "Work"], [item.name for item in list_calendars(self.connection)])

    def test_archived_calendar_retains_events_but_cannot_be_newly_selected(self) -> None:
        work_id = create_calendar(self.connection, CalendarInput("Work"))
        event_id = create_event(self.connection, EventInput(
            title="Retained", calendar_id=work_id, all_day=True,
            start_date="2026-08-01", end_date="2026-08-01",
        ))
        self.assertTrue(archive_calendar(self.connection, work_id))
        self.assertEqual(work_id, get_event(self.connection, event_id).calendar_id)
        self.assertIsNone(get_calendar(self.connection, work_id))
        update_event(self.connection, event_id, EventUpdate(title="Still retained"))
        self.assertEqual(work_id, get_event(self.connection, event_id).calendar_id)
        with self.assertRaisesRegex(ValueError, "Archived calendar"):
            create_event(self.connection, EventInput(
                title="Unsafe", calendar_id=work_id, all_day=True,
                start_date="2026-08-02", end_date="2026-08-02",
            ))
        audit = list_audit_events(self.connection, "calendar", work_id)[0]
        self.assertEqual("archive", audit.action)
        self.assertIn("retained", audit.notes)

    def test_delete_refuses_default_or_any_event_assignment(self) -> None:
        work_id = create_calendar(self.connection, CalendarInput("Work"))
        with self.assertRaisesRegex(ValueError, "default"):
            delete_calendar(self.connection, self.general_id)
        create_event(self.connection, EventInput(
            title="Protected", calendar_id=work_id, all_day=True,
            start_date="2026-08-01", end_date="2026-08-01",
        ))
        with self.assertRaisesRegex(ValueError, "Events are assigned"):
            delete_calendar(self.connection, work_id)
        empty_id = create_calendar(self.connection, CalendarInput("Empty"))
        delete_calendar(self.connection, empty_id)
        self.assertIsNone(get_calendar(self.connection, empty_id, include_archived=True))

    def test_validation_rejects_invalid_configuration(self) -> None:
        with self.assertRaisesRegex(ValueError, "#RRGGBB"):
            create_calendar(self.connection, CalendarInput("Bad", "blue"))
        with self.assertRaisesRegex(ValueError, "Unknown IANA timezone"):
            create_calendar(self.connection, CalendarInput("Bad", timezone="Mars/Olympus"))
        with self.assertRaisesRegex(ValueError, "positive"):
            create_calendar(self.connection, CalendarInput("Bad", default_event_duration_minutes=0))

    def test_existing_canonical_event_database_upgrades_with_history(self) -> None:
        event_id = create_event(self.connection, EventInput(
            title="Kept through upgrade", all_day=True,
            start_date="2026-09-01", end_date="2026-09-01",
        ))
        self.connection.execute("DROP TABLE calendar_edit_history")
        self.connection.execute(
            "DELETE FROM schema_migrations WHERE migration_id = '20260719_19_calendar_management_history'"
        )
        self.connection.commit()

        create_schema(self.connection)

        self.assertIsNotNone(get_event(self.connection, event_id))
        self.assertIsNotNone(self.connection.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = '20260719_19_calendar_management_history'"
        ).fetchone())
        self.assertIsNotNone(self.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'calendar_edit_history'"
        ).fetchone())


if __name__ == "__main__":
    unittest.main()
