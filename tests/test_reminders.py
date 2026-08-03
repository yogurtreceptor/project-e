import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.db import connect, create_entity, delete_entity
from app.entities import DEFINITIONS_BY_TYPE, EVENT_DEFINITION
from app.event_service import EventInput, create_event
from app.event_recurrence import RecurrenceRule, cancel_occurrence, get_recurrence, set_recurrence, split_series
from app.reminder_service import (act_on_inbox_item, disable_policy,
    evaluate_due_reminders, get_policy, list_inbox_items, open_inbox_item,
    set_override, set_policy)
from tests.database_test_support import initialise_test_database


class ReminderFoundationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "reminders.sqlite3"
        initialise_test_database(self.path)
        self.connection = connect(self.path)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_event_delivery_is_durable_and_deduplicated(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        now = datetime(2025, 12, 31, 23, 55, tzinfo=UTC)  # 09:55 Brisbane
        self.assertEqual(1, evaluate_due_reminders(self.connection, now=now))
        self.assertEqual(0, evaluate_due_reminders(self.connection, now=now))
        items = list_inbox_items(self.connection)
        self.assertEqual({"event"}, {item.source_kind for item in items})
        self.assertEqual({event_id}, {item.source_id for item in items})
        self.assertEqual(["10m"], [item.timing for item in items])

    def test_future_event_delivers_when_its_reminder_time_arrives(self):
        create_event(self.connection, EventInput("Future planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        self.assertEqual(1, evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC)))

    def test_future_attention_is_not_previewed_or_delivered_early(self):
        create_event(self.connection, EventInput("Future planning", False,
            start_local="2026-01-10T10:00", end_local="2026-01-10T11:00"))
        self.assertEqual(
            0,
            evaluate_due_reminders(
                self.connection, now=datetime(2026, 1, 1, tzinfo=UTC)
            ),
        )
        self.assertEqual([], list_inbox_items(self.connection))

    def test_later_timing_appears_once_after_earlier_timing_is_dismissed(self):
        create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        self.assertEqual(1, evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC)))
        first = list_inbox_items(self.connection)[0]
        self.assertEqual("1h", first.timing)
        self.assertTrue(act_on_inbox_item(self.connection, first.id, "dismiss"))

        later = datetime(2025, 12, 31, 23, 50, tzinfo=UTC)
        self.assertEqual(1, evaluate_due_reminders(self.connection, now=later))
        self.assertEqual(0, evaluate_due_reminders(self.connection, now=later))
        active = list_inbox_items(self.connection)
        self.assertEqual(["10m"], [item.timing for item in active])

    def test_later_timing_replaces_still_active_earlier_timing(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC))
        evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 50, tzinfo=UTC))
        rows = self.connection.execute(
            """SELECT timing, state FROM inbox_items
               WHERE source_kind='event' AND source_id=? ORDER BY timing""",
            (event_id,),
        ).fetchall()
        self.assertEqual(
            [("10m", "active"), ("1h", "resolved")],
            [(row["timing"], row["state"]) for row in rows],
        )

    def test_recurring_event_uses_derived_occurrence_identity(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(self.connection, now=datetime(2026, 1, 1, 22, 55, tzinfo=UTC))
        occurrences = {item.occurrence_key for item in list_inbox_items(self.connection)}
        self.assertIn("2026-01-02", occurrences)

    def test_birthday_uses_february_28_in_non_leap_year(self):
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {
            "display_name": "Leap Person", "given_name": "Leap", "middle_name": "",
            "family_name": "Person", "sex": "Unknown", "birthday": "2000-02-29",
            "email": "", "phone": "", "notes": "", "summary": "",
        })
        evaluate_due_reminders(self.connection, now=datetime(2025, 2, 27, 22, 55, tzinfo=UTC))
        event_id = self.connection.execute(
            "SELECT event_id FROM birthday_event_links WHERE person_id = ?", (person_id,)
        ).fetchone()["event_id"]
        items = [item for item in list_inbox_items(self.connection) if item.source_id == event_id]
        self.assertTrue(items)
        self.assertEqual({"event"}, {item.source_kind for item in items})
        self.assertEqual({"2025-02-28"}, {item.occurrence_key for item in items})

    def test_policy_change_resolves_only_removed_pending_timing(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(self.connection, now=datetime(2025, 12, 31, 23, 55, tzinfo=UTC))
        set_override(self.connection, "event", event_id, suppressed_timings=["10m"])
        rows = self.connection.execute(
            "SELECT timing, state FROM inbox_items WHERE source_kind='event' AND source_id=? AND reason='reminder' ORDER BY timing",
            (event_id,),
        ).fetchall()
        self.assertEqual([("10m", "resolved")], [(row["timing"], row["state"]) for row in rows])

    def test_event_attention_resolves_when_occurrence_ends(self):
        event_id = create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC))
        evaluate_due_reminders(
            self.connection, now=datetime(2026, 1, 1, 1, 1, tzinfo=UTC))
        row = self.connection.execute(
            "SELECT state, action_note, attention_expires_at FROM inbox_items WHERE source_id=?",
            (event_id,),
        ).fetchone()
        self.assertEqual("resolved", row["state"])
        self.assertEqual("Event occurrence ended", row["action_note"])
        self.assertEqual("2026-01-01T01:00:00+00:00", row["attention_expires_at"])

    def test_snooze_is_fixed_at_ten_minutes_and_keeps_original_due_time(self):
        create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        evaluate_due_reminders(
            self.connection, now=datetime(2025, 12, 31, 23, 0, tzinfo=UTC))
        item = list_inbox_items(self.connection)[0]

        self.assertTrue(act_on_inbox_item(
            self.connection,
            item.id,
            "snooze_10m",
            now=datetime(2025, 12, 31, 23, 1, tzinfo=UTC),
        ))

        row = self.connection.execute(
            "SELECT state, due_at, next_attention_at FROM inbox_items WHERE id=?",
            (item.id,),
        ).fetchone()
        self.assertEqual("snoozed", row["state"])
        self.assertEqual(item.due_at, row["due_at"])
        self.assertEqual("2025-12-31T23:11:00+00:00", row["next_attention_at"])
        with self.assertRaisesRegex(ValueError, "invalid"):
            act_on_inbox_item(self.connection, item.id, "acknowledge")

    def test_open_event_clears_attention_and_targets_exact_occurrence(self):
        event_id = create_event(self.connection, EventInput("Daily stand-up", True,
            start_date="2026-01-01", end_date="2026-01-01"))
        event = __import__("app.event_service", fromlist=["get_event"]).get_event(self.connection, event_id)
        set_recurrence(self.connection, event, RecurrenceRule("daily"))
        evaluate_due_reminders(
            self.connection, now=datetime(2026, 1, 1, 22, 55, tzinfo=UTC))
        item = next(
            item for item in list_inbox_items(self.connection)
            if item.occurrence_key == "2026-01-02"
        )

        destination = open_inbox_item(self.connection, item.id)

        self.assertEqual(
            f"/calendar?date=2026-01-02&preview={event_id}&occurrence=2026-01-02",
            destination,
        )
        state = self.connection.execute(
            "SELECT state FROM inbox_items WHERE id=?", (item.id,)
        ).fetchone()["state"]
        self.assertEqual("resolved", state)

    def test_document_expiry_remains_after_open_and_after_due_date(self):
        document_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["document"], {
            "display_name": "Fictional licence", "document_type": "Licence",
            "document_date": "2025-01-01", "expiry_date": "2026-01-02",
            "issuer": "Example Authority", "identifier": "TEST-1", "notes": "",
            "summary": "", "file_name": "", "file_path": "", "mime_type": "",
            "file_size": "",
        })
        evaluate_due_reminders(
            self.connection, now=datetime(2026, 1, 1, 22, 5, tzinfo=UTC))
        item = list_inbox_items(self.connection)[0]
        self.assertEqual("document_expiry", item.source_kind)
        self.assertEqual("reminder", item.reason)
        self.assertEqual(f"/documents/{document_id}", open_inbox_item(self.connection, item.id))
        self.assertEqual("active", self.connection.execute(
            "SELECT state FROM inbox_items WHERE id=?", (item.id,)
        ).fetchone()["state"])

        evaluate_due_reminders(
            self.connection, now=datetime(2026, 1, 2, 1, 0, tzinfo=UTC))
        active = list_inbox_items(self.connection)
        self.assertEqual(["overdue"], [entry.reason for entry in active])

    def test_long_lead_birthday_timing_is_projected(self):
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {
            "display_name": "Future Person", "given_name": "Future", "middle_name": "",
            "family_name": "Person", "sex": "Unknown", "birthday": "2000-09-01",
            "email": "", "phone": "", "notes": "", "summary": "",
        })
        created = evaluate_due_reminders(
            self.connection, now=datetime(2026, 7, 31, 23, 0, tzinfo=UTC))
        event_id = self.connection.execute(
            "SELECT event_id FROM birthday_event_links WHERE person_id=?", (person_id,)
        ).fetchone()["event_id"]
        items = [item for item in list_inbox_items(self.connection) if item.source_id == event_id]
        self.assertEqual(1, created)
        self.assertEqual(["1mo"], [item.timing for item in items])
        self.assertEqual(["2026-09-01"], [item.occurrence_key for item in items])

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

    def test_calendar_policy_can_disable_event_notifications_and_resolve_pending_items(self):
        event_id = create_event(self.connection, EventInput("Quiet planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        calendar_id = self.connection.execute("SELECT calendar_id FROM events WHERE entity_id=?", (event_id,)).fetchone()[0]
        evaluate_due_reminders(self.connection, now=datetime(2025, 12, 31, 23, 55, tzinfo=UTC))

        disable_policy(self.connection, "calendar", calendar_id, "event")

        self.assertEqual([], get_policy(self.connection, "calendar", calendar_id, "event"))
        rows = self.connection.execute(
            "SELECT DISTINCT state FROM inbox_items WHERE source_kind='event' AND source_id=? AND reason='reminder'",
            (event_id,),
        ).fetchall()
        self.assertEqual(["resolved"], [row["state"] for row in rows])
        self.assertEqual(0, evaluate_due_reminders(self.connection, now=datetime(2025, 12, 31, 23, 55, tzinfo=UTC)))

    def test_calendar_policy_rejects_more_than_ten_reminders(self):
        calendar_id = self.connection.execute("SELECT id FROM calendars WHERE kind='event' AND is_default=1").fetchone()[0]
        with self.assertRaisesRegex(ValueError, "10"):
            set_policy(self.connection, "calendar", calendar_id, "event", [f"{value}m" for value in range(1, 12)])

    def test_event_override_rejects_more_than_ten_effective_reminders(self):
        event_id = create_event(self.connection, EventInput("Busy", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        calendar_id = self.connection.execute("SELECT calendar_id FROM events WHERE entity_id=?", (event_id,)).fetchone()[0]
        set_policy(self.connection, "calendar", calendar_id, "event", [f"{value}m" for value in range(1, 11)])
        with self.assertRaisesRegex(ValueError, "Event can have at most 10"):
            set_override(self.connection, "event", event_id, custom_timings=["11m"])
