import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.automation_service import (dispatch, list_review_items, list_rules,
    reject_review_item, set_rule_enabled, approve_review_item)
from app.db import connect, create_entity, initialise_database
from app.entities import DEFINITIONS_BY_TYPE
from app.task_service import get_task


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
        self.assertEqual(2, dispatch(self.connection, "reminder_scan", "scan-1", now=now))
        self.assertEqual(0, dispatch(self.connection, "reminder_scan", "scan-1", now=now))
        rows = self.connection.execute("SELECT status FROM automation_runs WHERE trigger_key='scan-1'").fetchall()
        self.assertEqual(["completed", "completed"], [row["status"] for row in rows])

    def test_expiry_task_is_proposed_then_requires_explicit_approval(self):
        document_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["document"], {
            "display_name": "Passport", "document_type": "Identity document", "expiry_date": "2025-12-31",
        })
        rule = next(rule for rule in list_rules(self.connection) if rule.rule_key == "propose-expiry-follow-up")
        self.assertTrue(set_rule_enabled(self.connection, rule.id, True))
        dispatch(self.connection, "reminder_scan", "scan-expiry", now=datetime(2026, 1, 1, 12, tzinfo=UTC))

        item = list_review_items(self.connection)[0]
        self.assertEqual(document_id, item.source_id)
        self.assertEqual("pending", item.state)
        task_id = approve_review_item(self.connection, item.id)
        self.assertIsNotNone(task_id)
        self.assertEqual("Review expiring document: Passport", get_task(self.connection, task_id).title)
        self.assertEqual("automation", self.connection.execute("SELECT provenance FROM audit_events WHERE event_type='create' ORDER BY id DESC LIMIT 1").fetchone()["provenance"])

    def test_rejected_proposal_cannot_be_approved_later(self):
        document_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["document"], {
            "display_name": "Licence", "document_type": "Identity document", "expiry_date": "2025-12-31",
        })
        rule = next(rule for rule in list_rules(self.connection) if rule.rule_key == "propose-expiry-follow-up")
        set_rule_enabled(self.connection, rule.id, True)
        dispatch(self.connection, "reminder_scan", "scan-reject", now=datetime(2026, 1, 1, 12, tzinfo=UTC))
        item = next(item for item in list_review_items(self.connection) if item.source_id == document_id)
        self.assertTrue(reject_review_item(self.connection, item.id, "No follow-up needed"))
        self.assertIsNone(approve_review_item(self.connection, item.id))


if __name__ == "__main__":
    unittest.main()
