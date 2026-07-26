import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.automation_service import dispatch, list_review_items, list_rules
from app.db import connect, initialise_database


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "automation.sqlite3"
        initialise_database(self.path)
        self.connection = connect(self.path)

    def tearDown(self):
        self.connection.close()
        self.temporary.cleanup()

    def test_registered_actions_are_idempotent_for_a_logical_scan(self):
        now = datetime(2026, 1, 1, 12, tzinfo=UTC)
        self.assertEqual(1, dispatch(self.connection, "reminder_scan", "scan-1", now=now))
        self.assertEqual(0, dispatch(self.connection, "reminder_scan", "scan-1", now=now))
        rows = self.connection.execute("SELECT status FROM automation_runs WHERE trigger_key='scan-1'").fetchall()
        self.assertEqual(["completed"], [row["status"] for row in rows])

    def test_task_automation_and_proposals_are_dormant(self):
        self.assertEqual(["deliver-due-reminders"], [rule.rule_key for rule in list_rules(self.connection)])
        self.assertEqual([], list_review_items(self.connection))


if __name__ == "__main__":
    unittest.main()
