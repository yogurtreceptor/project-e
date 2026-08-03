import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from app.automation_service import list_rules
from app.db import (
    connect,
    create_entity,
    create_relationship,
    delete_entity,
    get_entity_by_id,
    permanent_delete_entity,
    restore_entity,
)
from app.entities import DEFINITIONS_BY_TYPE, EVENT_DEFINITION
from app.event_recurrence import (
    RecurrenceRule,
    get_recurrence,
    occurrence_exceptions,
    override_occurrence,
    set_recurrence,
)
from app.event_service import (
    EventInput,
    archive_event,
    cancel_event,
    create_event,
    get_event,
)
from app.portability import apply_import_bundle, create_bundle, inspect_bundle
from app.reminder_service import get_override, get_policy, set_override, set_policy
from app.scheduler_service import recover_at_startup
from tests.database_test_support import initialise_test_database


class Phase2CloseoutWalkthroughTests(unittest.TestCase):
    def test_integrated_task_free_operational_workflow_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_database = root / "source" / "project-e.sqlite3"
            source_documents = source_database.parent / "documents"
            source_documents.mkdir(parents=True)
            initialise_test_database(source_database)

            with connect(source_database) as connection:
                project = create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["project"],
                    {
                        "display_name": "Community archive launch",
                        "project_type": "Civic",
                        "status": "Active",
                    },
                )
                first_person = create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["person"],
                    {
                        "given_name": "Ada",
                        "family_name": "Example",
                        "sex": "Unknown",
                        "birthday": "1815-12-10",
                    },
                )
                second_person = create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["person"],
                    {
                        "given_name": "Lin",
                        "family_name": "Example",
                        "sex": "Unknown",
                    },
                )
                location = create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["location"],
                    {
                        "display_name": "Fictional community hall",
                        "city": "Brisbane",
                        "country": "Australia",
                    },
                )
                event_id = create_event(
                    connection,
                    EventInput(
                        "Archive planning session",
                        False,
                        start_local="2026-08-01T11:00",
                        end_local="2026-08-01T12:00",
                    ),
                )
                for target, relationship_type in (
                    (project, "event_related_to_project"),
                    (first_person, "event_involves_person"),
                    (second_person, "event_involves_person"),
                    (location, "event_at_location"),
                ):
                    create_relationship(
                        connection,
                        {
                            "source_entity_id": str(event_id),
                            "target_entity_id": str(target),
                            "type": relationship_type,
                        },
                    )
                connection.commit()

                event = get_event(connection, event_id)
                recurrence = set_recurrence(
                    connection,
                    event,
                    RecurrenceRule("weekly", until_date="2026-08-31"),
                )
                override_occurrence(
                    connection,
                    event,
                    recurrence,
                    "2026-08-08",
                    EventInput(
                        "Archive planning session — later",
                        False,
                        start_local="2026-08-08T12:00",
                        end_local="2026-08-08T13:00",
                    ),
                )
                self.assertEqual(
                    "override",
                    occurrence_exceptions(connection, recurrence)["2026-08-08"]["type"],
                )

                birthday_event_id = int(
                    connection.execute(
                        "SELECT event_id FROM birthday_event_links WHERE person_id = ?",
                        (first_person,),
                    ).fetchone()["event_id"]
                )
                self.assertEqual(
                    "yearly", get_recurrence(connection, birthday_event_id).rule.frequency
                )

                calendar_id = get_event(connection, event_id).calendar_id
                set_policy(connection, "calendar", calendar_id, "event", ["1h"])
                set_override(
                    connection,
                    "event",
                    event_id,
                    mode="custom",
                    custom_timings=["30m"],
                    suppressed_timings=["1h"],
                )
                self.assertEqual(
                    ["1h"], get_policy(connection, "calendar", calendar_id, "event")
                )
                self.assertEqual(
                    {
                        "mode": "custom",
                        "custom_timings": ["30m"],
                        "suppressed_timings": ["1h"],
                    },
                    get_override(connection, "event", event_id),
                )

                before_automation = dict(
                    connection.execute(
                        """SELECT entity.display_name, event.*
                           FROM entities AS entity
                           JOIN events AS event ON event.entity_id = entity.id
                           WHERE entity.id = ?""",
                        (event_id,),
                    ).fetchone()
                )
                audit_before = int(
                    connection.execute(
                        """SELECT COUNT(*) FROM audit_event_records
                           WHERE record_kind = 'entity' AND record_id = ?""",
                        (event_id,),
                    ).fetchone()[0]
                )
                now = datetime(2026, 8, 1, 0, 30, tzinfo=UTC)
                self.assertEqual(1, recover_at_startup(connection, now=now))
                self.assertEqual(0, recover_at_startup(connection, now=now))
                self.assertEqual(
                    before_automation,
                    dict(
                        connection.execute(
                            """SELECT entity.display_name, event.*
                               FROM entities AS entity
                               JOIN events AS event ON event.entity_id = entity.id
                               WHERE entity.id = ?""",
                            (event_id,),
                        ).fetchone()
                    ),
                )
                self.assertEqual(
                    audit_before,
                    int(
                        connection.execute(
                            """SELECT COUNT(*) FROM audit_event_records
                               WHERE record_kind = 'entity' AND record_id = ?""",
                            (event_id,),
                        ).fetchone()[0]
                    ),
                )

                rules = list_rules(connection)
                self.assertEqual(
                    [("reminder_scan", "deliver_due_reminders")],
                    [(rule.trigger_name, rule.action_name) for rule in rules],
                )
                automation_columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(automation_rules)")
                }
                self.assertTrue(
                    {"code", "script", "python", "executable"}.isdisjoint(
                        automation_columns
                    )
                )
                self.assertEqual(
                    (1, 1, 1),
                    tuple(
                        int(connection.execute(query).fetchone()[0])
                        for query in (
                            "SELECT COUNT(*) FROM job_runs",
                            "SELECT COUNT(*) FROM automation_runs",
                            "SELECT COUNT(*) FROM inbox_items",
                        )
                    ),
                )
                self.assertGreaterEqual(
                    int(
                        connection.execute(
                            "SELECT COUNT(*) FROM inbox_item_actions"
                        ).fetchone()[0]
                    ),
                    1,
                )
                self.assertIsNotNone(
                    connection.execute(
                        """SELECT 1 FROM audit_event_records
                           WHERE record_kind = 'automation_run'"""
                    ).fetchone()
                )

                cancelled_id = self._event(connection, "Cancelled example", "2026-09-01")
                archived_id = self._event(connection, "Archived example", "2026-09-02")
                restored_id = self._event(connection, "Restored example", "2026-09-03")
                deleted_id = self._event(connection, "Deleted example", "2026-09-04")
                self.assertTrue(cancel_event(connection, cancelled_id))
                self.assertTrue(archive_event(connection, archived_id))
                delete_entity(connection, EVENT_DEFINITION, restored_id)
                self.assertTrue(restore_entity(connection, restored_id))
                delete_entity(connection, EVENT_DEFINITION, deleted_id)
                self.assertEqual(("event", ""), permanent_delete_entity(connection, deleted_id))
                self.assertTrue(get_event(connection, cancelled_id).is_cancelled)
                self.assertTrue(
                    get_event(connection, archived_id, include_archived=True).is_archived
                )
                self.assertIsNotNone(get_event(connection, restored_id))
                self.assertIsNone(
                    get_entity_by_id(connection, deleted_id, include_deleted=True)
                )

                source_counts = {
                    table: int(
                        connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    )
                    for table in (
                        "job_runs",
                        "automation_runs",
                        "inbox_items",
                        "inbox_item_actions",
                        "relationships",
                    )
                }

            bundle = create_bundle(source_database, source_documents)
            preview = inspect_bundle(bundle)
            self.assertGreaterEqual(preview.entities, 9)
            self.assertEqual(4, preview.relationships)

            target_database = root / "target" / "project-e.sqlite3"
            target_documents = target_database.parent / "documents"
            target_documents.mkdir(parents=True)
            initialise_test_database(target_database)
            self.assertEqual(
                preview,
                apply_import_bundle(
                    bundle,
                    target_database,
                    target_documents,
                    target_database.parent / "backups",
                ),
            )
            with connect(target_database) as connection:
                self.assertEqual(
                    "Archive planning session",
                    get_entity_by_id(connection, event_id).display_name,
                )
                self.assertEqual(
                    source_counts,
                    {
                        table: int(
                            connection.execute(
                                f"SELECT COUNT(*) FROM {table}"
                            ).fetchone()[0]
                        )
                        for table in source_counts
                    },
                )
                self.assertIsNotNone(
                    connection.execute(
                        """SELECT 1 FROM audit_events
                           WHERE event_type = 'import'"""
                    ).fetchone()
                )

    @staticmethod
    def _event(connection, title: str, event_date: str) -> int:
        return create_event(
            connection,
            EventInput(
                title,
                True,
                start_date=event_date,
                end_date=event_date,
            ),
        )


if __name__ == "__main__":
    unittest.main()
