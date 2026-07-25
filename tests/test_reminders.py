import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.db import connect, create_entity, delete_entity, initialise_database
from app.entities import DEFINITIONS_BY_TYPE, EVENT_DEFINITION
from app.event_service import EventInput, create_event
from app.event_recurrence import RecurrenceRule, cancel_occurrence, get_recurrence, set_recurrence, split_series
from app.reminder_service import (act_on_inbox_item, evaluate_due_reminders,
    clear_policy, get_policy, list_inbox_items, list_upcoming_reminders,
    list_inbox_actions, set_override, set_policy)
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
        now = datetime(2025, 12, 31, 23, 55, tzinfo=UTC)  # 09:55 Brisbane
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

    def test_upcoming_preview_does_not_create_a_delivery(self):
        event_id = create_event(self.connection, EventInput("Future planning", False,
            start_local="2026-01-10T10:00", end_local="2026-01-10T11:00"))
        upcoming = list_upcoming_reminders(self.connection, now=datetime(2026, 1, 1, tzinfo=UTC))
        self.assertEqual({"10m", "1h"}, {item.timing for item in upcoming if item.source_id == event_id})
        self.assertEqual([], list_inbox_items(self.connection))

    def test_recurring_event_uses_derived_occurrence_identity(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, 55, tzinfo=UTC))
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
        evaluate_due_reminders(self.connection, now=datetime(2025, 2, 27, 22, 55, tzinfo=UTC))
        items = [item for item in list_inbox_items(self.connection) if item.source_id == person_id]
        self.assertTrue(items)
        self.assertEqual({"2025-02-28"}, {item.occurrence_key for item in items})

    def test_override_can_disable_and_snooze_keeps_same_delivery(self):
        task_id = create_task(self.connection, TaskInput("Private", deadline_date="2026-01-02"))
        set_override(self.connection, "task_deadline", task_id, mode="disabled")
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, tzinfo=UTC))
        self.assertEqual([], [item for item in list_inbox_items(self.connection) if item.reason == "reminder"])
        set_override(self.connection, "task_deadline", task_id, mode="default")
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, tzinfo=UTC))
        item = next(item for item in list_inbox_items(self.connection) if item.reason == "reminder")
        self.assertTrue(act_on_inbox_item(self.connection, item.id, "snooze_30m"))
        row = self.connection.execute("SELECT delivery_key, due_at, state FROM inbox_items WHERE id=?", (item.id,)).fetchone()
        self.assertEqual("snoozed", row["state"])
        self.assertEqual(item.delivery_key, row["delivery_key"])
        self.assertEqual(item.due_at, row["due_at"])

    def test_policy_change_resolves_only_removed_pending_timing(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(self.connection, now=datetime(2025, 12, 31, 23, 55, tzinfo=UTC))
        set_override(self.connection, "event", event_id, suppressed_timings=["10m"])
        rows = self.connection.execute(
            "SELECT timing, state FROM inbox_items WHERE source_kind='event' AND source_id=? AND reason='reminder' ORDER BY timing",
            (event_id,),
        ).fetchall()
        self.assertEqual([("10m", "resolved"), ("1h", "active")], [(row["timing"], row["state"]) for row in rows])

    def test_disabling_reminders_resolves_existing_pending_delivery(self):
        task_id = create_task(self.connection, TaskInput("Private", deadline_local="2026-01-01T12:00", deadline_timezone="Australia/Brisbane"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 1, tzinfo=UTC))
        set_override(self.connection, "task_deadline", task_id, mode="disabled")
        states = self.connection.execute(
            "SELECT DISTINCT state FROM inbox_items WHERE source_kind='task_deadline' AND source_id=? AND reason='reminder'",
            (task_id,),
        ).fetchall()
        self.assertEqual(["resolved"], [row["state"] for row in states])

    def test_catch_up_uses_one_persistent_overdue_item_and_skips_past_event(self):
        task_id = create_task(self.connection, TaskInput("Late task", deadline_date="2026-01-01"))
        event_id = create_event(self.connection, EventInput("Past event", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 5, tzinfo=UTC))
        task_items = [item for item in list_inbox_items(self.connection) if item.source_id == task_id]
        self.assertEqual(["overdue"], [item.reason for item in task_items])
        self.assertEqual([], [item for item in list_inbox_items(self.connection) if item.source_id == event_id])

    def test_inbox_action_history_retains_delivery_snooze_and_acknowledgement(self):
        task_id = create_task(self.connection, TaskInput("Private", deadline_date="2026-01-02"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, tzinfo=UTC))
        item = next(item for item in list_inbox_items(self.connection) if item.source_id == task_id and item.reason == "reminder")
        act_on_inbox_item(self.connection, item.id, "snooze_30m")
        act_on_inbox_item(self.connection, item.id, "acknowledge")
        actions = list_inbox_actions(self.connection, item.id)
        self.assertEqual(["delivered", "snooze_30m", "acknowledge"], [action.action for action in actions])
        self.assertEqual("acknowledged", actions[-1].resulting_state)

    def test_recurring_series_split_resolves_moved_pending_delivery(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, 55, tzinfo=UTC))
        split_series(self.connection, event, get_recurrence(self.connection, event_id), "2026-01-02")
        states = self.connection.execute(
            "SELECT DISTINCT state FROM inbox_items WHERE source_kind='event' AND source_id=? AND occurrence_key='2026-01-02'",
            (event_id,),
        ).fetchall()
        self.assertEqual(["resolved"], [row["state"] for row in states])

    def test_recycling_event_resolves_pending_reminders(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(self.connection, now=datetime(2025, 12, 31, 23, 55, tzinfo=UTC))
        delete_entity(self.connection, EVENT_DEFINITION, event_id)
        states = self.connection.execute("SELECT DISTINCT state FROM inbox_items WHERE source_kind='event' AND source_id=?", (event_id,)).fetchall()
        self.assertEqual(["resolved"], [row["state"] for row in states])

    def test_cancelling_recurring_occurrence_resolves_its_pending_reminders(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        definition = set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, 55, tzinfo=UTC))
        cancel_occurrence(self.connection, definition, "2026-01-02")
        states = self.connection.execute("SELECT DISTINCT state FROM inbox_items WHERE source_kind='event' AND source_id=? AND occurrence_key='2026-01-02'", (event_id,)).fetchall()
        self.assertEqual(["resolved"], [row["state"] for row in states])

    def test_context_policy_can_be_configured_and_restored_to_inheritance(self):
        task_id = create_task(self.connection, TaskInput("Submit report", deadline_date="2026-01-10"))
        task_list_id = self.connection.execute("SELECT task_list_id FROM tasks WHERE entity_id=?", (task_id,)).fetchone()[0]
        set_policy(self.connection, "task_list", task_list_id, "task_deadline", ["2h"])
        self.assertEqual(["2h"], get_policy(self.connection, "task_list", task_list_id, "task_deadline"))
        self.assertEqual(1, evaluate_due_reminders(self.connection, now=datetime(2026, 1, 9, 22, 0, tzinfo=UTC)))
        clear_policy(self.connection, "task_list", task_list_id, "task_deadline")
        self.assertIsNone(get_policy(self.connection, "task_list", task_list_id, "task_deadline"))
