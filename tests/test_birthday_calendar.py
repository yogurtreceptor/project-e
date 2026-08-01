import tempfile
import unittest
from pathlib import Path

from app.db import connect, create_entity, delete_entity, initialise_database, restore_entity
from app.db_schema import create_schema
from app.entities import DEFINITIONS_BY_TYPE
from app.event_recurrence import get_recurrence
from app.event_service import EventInput, create_event, get_event
from app.reminder_service import get_policy, set_policy


class BirthdayCalendarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "birthdays.sqlite3"
        initialise_database(self.path)
        self.connection = connect(self.path)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def create_person(self, name="Ada Lovelace", birthday="1815-12-10") -> int:
        given_name, family_name = name.split(" ", 1)
        return create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {
            "display_name": name, "given_name": given_name, "middle_name": "",
            "family_name": family_name, "sex": "Unknown", "birthday": birthday,
            "email": "", "phone": "", "notes": "", "summary": "",
        })

    def linked_event_id(self, person_id: int) -> int:
        return int(self.connection.execute(
            "SELECT event_id FROM birthday_event_links WHERE person_id = ?", (person_id,)
        ).fetchone()["event_id"])

    def test_person_birthday_is_a_linked_yearly_all_day_event(self) -> None:
        person_id = self.create_person()
        event_id = self.linked_event_id(person_id)
        event = get_event(self.connection, event_id, include_archived=True)
        calendar = self.connection.execute(
            "SELECT name, kind FROM calendars WHERE id = ?", (event.calendar_id,)
        ).fetchone()

        self.assertEqual("Ada Lovelace's birthday", event.title)
        self.assertTrue(event.is_all_day)
        self.assertEqual(("1815-12-10", "1815-12-11"), (event.start_date, event.end_date_exclusive))
        self.assertEqual(("Birthdays", "birthday"), (calendar["name"], calendar["kind"]))
        self.assertEqual("yearly", get_recurrence(self.connection, event_id).rule.frequency)

    def test_person_changes_keep_the_same_event_in_sync_and_lifecycle_safe(self) -> None:
        person_id = self.create_person()
        event_id = self.linked_event_id(person_id)
        from app.entity_service import update_entity
        update_entity(self.connection, DEFINITIONS_BY_TYPE["person"], person_id, {
            "display_name": "Ada King", "given_name": "Ada", "middle_name": "",
            "family_name": "King", "sex": "Unknown", "birthday": "1815-12-11",
            "email": "", "phone": "", "notes": "", "summary": "",
        })
        event = get_event(self.connection, event_id, include_archived=True)
        self.assertEqual("Ada King's birthday", event.title)
        self.assertEqual("1815-12-11", event.start_date)

        delete_entity(self.connection, DEFINITIONS_BY_TYPE["person"], person_id)
        self.assertTrue(get_event(self.connection, event_id, include_archived=True).is_archived)
        self.assertTrue(restore_entity(self.connection, person_id))
        self.assertFalse(get_event(self.connection, event_id, include_archived=True).is_archived)

    def test_birthdays_calendar_cannot_receive_ordinary_events(self) -> None:
        birthday_calendar_id = self.connection.execute(
            "SELECT id FROM calendars WHERE kind = 'birthday'"
        ).fetchone()["id"]
        with self.assertRaisesRegex(ValueError, "Birthdays"):
            create_event(self.connection, EventInput(
                "Not a birthday", True, int(birthday_calendar_id),
                start_date="2026-01-01", end_date="2026-01-01",
            ))

    def test_upgrade_migrates_existing_birthday_policy_and_people(self) -> None:
        person_id = self.create_person()
        event_id = self.linked_event_id(person_id)
        self.connection.execute("DELETE FROM entities WHERE id = ?", (event_id,))
        self.connection.execute("DROP TABLE birthday_event_links")
        self.connection.execute("DELETE FROM calendars WHERE kind = 'birthday'")
        set_policy(self.connection, "global", 0, "birthday", ["2w", "1d"])
        self.connection.execute(
            "DELETE FROM schema_migrations WHERE migration_id = '20260725_28_birthday_calendar'"
        )
        self.connection.commit()

        create_schema(self.connection)

        birthday_calendar_id = self.connection.execute(
            "SELECT id FROM calendars WHERE kind = 'birthday'"
        ).fetchone()["id"]
        self.assertEqual(["2w", "1d"], get_policy(
            self.connection, "calendar", int(birthday_calendar_id), "event"
        ))
        self.assertIsNone(get_policy(self.connection, "global", 0, "birthday"))
        self.assertIsNotNone(self.connection.execute(
            "SELECT 1 FROM birthday_event_links WHERE person_id = ?", (person_id,)
        ).fetchone())


if __name__ == "__main__":
    unittest.main()
