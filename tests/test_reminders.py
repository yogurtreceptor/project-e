import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.db import connect, create_entity, initialise_database
from app.entities import DEFINITIONS_BY_TYPE
from app.event_service import EventInput, create_event
from app.event_recurrence import RecurrenceRule, set_recurrence
from app.reminder_service import (act_on_inbox_item, evaluate_due_reminders,
    list_inbox_items, set_override)
from app.task_service import TaskInput, create_task


class ReminderFoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "reminders.sqlite3"
        initialise_database(self.path)
        self.connection = connect(self.path)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_event_delivery_is_durable_and_deduplicated(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        now = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)  # 11:00 Brisbane
        self.assertEqual(2, evaluate_due_reminders(self.connection, now=now))
        self.assertEqual(0, evaluate_due_reminders(self.connection, now=now))
        items = list_inbox_items(self.connection)
        self.assertEqual({"event"}, {item.source_kind for item in items})
        self.assertEqual({event_id}, {item.source_id for item in items})

    def test_future_event_delivers_when_its_reminder_time_arrives(self):
        create_event(self.connection, EventInput("Future planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        self.assertEqual(1, evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC)))

    def test_recurring_event_uses_derived_occurrence_identity(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 2, 0, 0, tzinfo=UTC))
        occurrences = {item.occurrence_key for item in list_inbox_items(self.connection)}
        self.assertIn("2026-01-02", occurrences)

    def test_task_overdue_is_one_distinct_delivery(self):
        task_id = create_task(self.connection, TaskInput("Send proposal", deadline_date="2026-01-01"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 5, tzinfo=UTC))
        overdue = [item for item in list_inbox_items(self.connection) if item.reason == "overdue"]
        self.assertEqual(1, len(overdue))
        self.assertEqual(task_id, overdue[0].source_id)
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 6, tzinfo=UTC))
        self.assertEqual(1, len([item for item in list_inbox_items(self.connection) if item.reason == "overdue"]))

    def test_birthday_uses_february_28_in_non_leap_year(self):
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {
            "display_name": "Leap Person", "given_name": "Leap", "middle_name": "",
            "family_name": "Person", "sex": "Unknown", "birthday": "2000-02-29",
            "email": "", "phone": "", "notes": "", "summary": "",
        })
        evaluate_due_reminders(self.connection, now=datetime(2025, 2, 27, 23, 0, tzinfo=UTC))
        items = [item for item in list_inbox_items(self.connection) if item.source_id == person_id]
        self.assertTrue(items)
        self.assertEqual({"2025-02-28"}, {item.occurrence_key for item in items})

    def test_override_can_disable_and_snooze_keeps_same_delivery(self):
        task_id = create_task(self.connection, TaskInput("Private", deadline_date="2026-01-01"))
        set_override(self.connection, "task_deadline", task_id, mode="disabled")
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 2, tzinfo=UTC))
        self.assertEqual([], [item for item in list_inbox_items(self.connection) if item.reason == "reminder"])
        set_override(self.connection, "task_deadline", task_id, mode="default")
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 2, tzinfo=UTC))
        item = next(item for item in list_inbox_items(self.connection) if item.reason == "reminder")
        self.assertTrue(act_on_inbox_item(self.connection, item.id, "snooze_30m"))
        row = self.connection.execute("SELECT delivery_key, due_at, state FROM inbox_items WHERE id=?", (item.id,)).fetchone()
        self.assertEqual("snoozed", row["state"])
        self.assertEqual(item.delivery_key, row["delivery_key"])
        self.assertEqual(item.due_at, row["due_at"])
