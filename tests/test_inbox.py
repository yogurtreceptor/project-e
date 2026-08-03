import http.client
import json
import tempfile
import threading
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app import views
from app.db import connect
from app.event_service import EventInput, create_event
from app.reminder_service import InboxItem, evaluate_due_reminders, list_inbox_items
from tests.database_test_support import initialise_test_database
from tests.web_test_support import make_test_server


class InboxViewTests(unittest.TestCase):
    def item(self, **changes) -> InboxItem:
        values = {
            "id": 7,
            "delivery_key": "delivery",
            "source_kind": "event",
            "source_id": 4,
            "occurrence_key": "2026-08-02T00:00:00Z",
            "reason": "reminder",
            "timing": "1h",
            "title": "Planning",
            "due_at": "2026-08-02T00:00:00+00:00",
            "delivered_at": "2026-08-01T23:00:00+00:00",
            "state": "active",
            "next_attention_at": "",
            "attention_expires_at": "2026-08-02T01:00:00+00:00",
            "acted_at": "",
            "action_note": "",
        }
        values.update(changes)
        return InboxItem(**values)

    def test_active_queue_uses_date_groups_and_restrained_reminder_actions(self):
        html = views.inbox_page(
            [self.item()],
            archived=False,
            now=datetime(2026, 8, 1, 23, 30, tzinfo=UTC),
        )

        self.assertIn(">Today<", html)
        self.assertIn("Open event", html)
        self.assertIn('aria-label="Snooze 10 minutes"', html)
        self.assertIn('title="Snooze 10 minutes"', html)
        self.assertIn('src="/static/icons/snooze.svg"', html)
        self.assertIn(">Dismiss<", html)
        self.assertNotIn("Active items", html)
        self.assertNotIn("Upcoming", html)
        self.assertNotIn("Evaluate reminders", html)
        self.assertNotIn("Acknowledge", html)

    def test_empty_queue_is_calm_and_archive_remains_available(self):
        html = views.inbox_page([], archived=False)
        self.assertIn("You’re all caught up", html)
        self.assertIn('href="/inbox?archived=1">Archive</a>', html)

    def test_navigation_badge_has_exact_scope_and_semantic_hook(self):
        html = views.layout("Home", "<h1>Home</h1>", inbox_count=3)
        self.assertIn('data-inbox-count', html)
        self.assertIn('aria-label="3 active Inbox reminders"', html)
        self.assertIn(">3</span>", html)
        self.assertIn('src="/static/inbox-count.js"', html)


class InboxRouteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "inbox.sqlite3"
        initialise_test_database(self.path)
        with connect(self.path) as connection:
            self.event_id = create_event(
                connection,
                EventInput(
                    "Planning",
                    False,
                    start_local="2026-08-02T10:00",
                    end_local="2026-08-02T11:00",
                ),
            )
            evaluate_due_reminders(
                connection, now=datetime(2026, 8, 1, 23, 0, tzinfo=UTC)
            )
            self.item_id = list_inbox_items(connection)[0].id
        self.server = make_test_server(self.path)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.client = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def test_count_route_and_open_action_use_exact_occurrence(self):
        self.client.request("GET", "/inbox/count")
        response = self.client.getresponse()
        payload = json.loads(response.read())
        self.assertEqual(200, response.status)
        self.assertEqual({"count": 1}, payload)

        self.client.request("POST", f"/inbox/{self.item_id}/open", body="")
        response = self.client.getresponse()
        response.read()
        self.assertEqual(303, response.status)
        self.assertEqual(
            f"/calendar?date=2026-08-02&preview={self.event_id}&occurrence=2026-08-02",
            response.getheader("Location"),
        )
        with connect(self.path) as connection:
            state = connection.execute(
                "SELECT state FROM inbox_items WHERE id=?", (self.item_id,)
            ).fetchone()["state"]
        self.assertEqual("resolved", state)

    def test_inbox_assets_are_served_locally(self):
        for path, content_type in (
            ("/static/inbox-count.js", "text/javascript"),
            ("/static/icons/snooze.svg", "image/svg+xml"),
        ):
            with self.subTest(path=path):
                self.client.request("GET", path)
                response = self.client.getresponse()
                data = response.read()
                self.assertEqual(200, response.status)
                self.assertEqual(content_type, response.headers.get_content_type())
                self.assertTrue(data)


if __name__ == "__main__":
    unittest.main()
