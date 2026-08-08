import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import initialise_local_storage
from app.db import connect, initialise_database
from app.db_schema import (
    SCHEMA_MIGRATIONS,
    SCHEMA_MIGRATION_IDS,
    create_schema,
    create_schema_migration_table,
)


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "migration-test.sqlite3"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def migration_rows(self) -> list[tuple[str, str]]:
        with connect(self.database_path) as connection:
            return [
                (row["migration_id"], row["applied_at"])
                for row in connection.execute(
                    "SELECT migration_id, applied_at FROM schema_migrations ORDER BY migration_id"
                )
            ]

    def test_fresh_database_records_ordered_schema_migrations(self) -> None:
        initialise_database(self.database_path)

        rows = self.migration_rows()

        self.assertEqual(tuple(row[0] for row in rows), SCHEMA_MIGRATION_IDS)
        self.assertTrue(all(row[1] for row in rows))
        with connect(self.database_path) as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
        self.assertIn("entities", tables)
        self.assertIn("relationships", tables)
        self.assertIn("location_addresses", tables)
        self.assertIn("location_geometries", tables)
        self.assertIn("location_provider_references", tables)
        self.assertIn("mobility_profiles", tables)
        self.assertIn("routing_policies", tables)
        self.assertIn("map_feature_lists", tables)
        self.assertIn("map_feature_list_memberships", tables)
        self.assertIn("schema_migrations", tables)
        self.assertIn("journal_entries", tables)
        self.assertIn("event_icalendar_identities", tables)
        self.assertIn("calendar_subscriptions", tables)
        self.assertIn("external_calendar_events", tables)
        self.assertTrue({"task_lists", "tasks", "task_deadlines", "task_sessions"}.isdisjoint(tables))
        self.assertNotIn("automation_review_items", tables)
        with connect(self.database_path) as connection:
            favourites = connection.execute(
                "SELECT list_key, name, kind FROM map_feature_lists"
            ).fetchall()
        self.assertEqual(
            [("favourites", "Favourites", "favourites")],
            [tuple(row) for row in favourites],
        )
        with connect(self.database_path) as connection:
            entity_columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
            project_columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
            document_columns = {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}
            asset_columns = {row["name"] for row in connection.execute("PRAGMA table_info(assets)")}
            relationship_columns = {row["name"] for row in connection.execute("PRAGMA table_info(relationships)")}
            reminder_policy_sql = connection.execute(
                """SELECT sql FROM sqlite_master
                   WHERE type = 'table' AND name = 'reminder_policies'"""
            ).fetchone()["sql"]
            entity_sql = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'entities'"
            ).fetchone()["sql"]
        self.assertIn("deleted_at", entity_columns)
        self.assertIn("ended_at", project_columns)
        self.assertTrue({"identifier", "expiry_date"} <= document_columns)
        self.assertTrue({"manufacturer", "model"} <= asset_columns)
        self.assertIn("deleted_at", relationship_columns)
        self.assertIn("'calendar_subscription'", reminder_policy_sql)
        self.assertNotIn("'task_list'", reminder_policy_sql)
        self.assertNotIn("'task_deadline'", reminder_policy_sql)
        self.assertNotIn("'task'", entity_sql)

        with connect(self.database_path) as connection:
            location_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(locations)")
            }
            place_indexes = {
                row["name"]
                for row in connection.execute(
                    """SELECT name FROM sqlite_master
                       WHERE type='index' AND name IN (
                           'idx_location_address_one_preferred',
                           'idx_location_geometry_one_preferred',
                           'idx_location_one_active_parent'
                       )"""
                )
            }
            containment_triggers = {
                row["name"]
                for row in connection.execute(
                    """SELECT name FROM sqlite_master
                       WHERE type='trigger'
                         AND name LIKE 'trg_location_containment_%'"""
                )
            }
        self.assertEqual({"entity_id"}, location_columns)
        self.assertEqual(
            {
                "idx_location_address_one_preferred",
                "idx_location_geometry_one_preferred",
                "idx_location_one_active_parent",
            },
            place_indexes,
        )
        self.assertEqual(
            {
                "trg_location_containment_insert",
                "trg_location_containment_update",
            },
            containment_triggers,
        )

    def test_place_foundation_upgrade_preserves_legacy_location_values(self) -> None:
        place_migration = "20260805_33_canonical_place_foundation"
        with connect(self.database_path) as connection:
            create_schema_migration_table(connection)
            for migration_id, migration in SCHEMA_MIGRATIONS:
                if migration_id == place_migration:
                    break
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, 'before')",
                    (migration_id,),
                )
            for definition in (
                "formatted_address TEXT NOT NULL DEFAULT ''",
                "address_line_1 TEXT NOT NULL DEFAULT ''",
                "address_line_2 TEXT NOT NULL DEFAULT ''",
                "suburb TEXT NOT NULL DEFAULT ''",
                "city TEXT NOT NULL DEFAULT ''",
                "state TEXT NOT NULL DEFAULT ''",
                "post_code TEXT NOT NULL DEFAULT ''",
                "country TEXT NOT NULL DEFAULT ''",
                "latitude TEXT NOT NULL DEFAULT ''",
                "longitude TEXT NOT NULL DEFAULT ''",
                "source TEXT NOT NULL DEFAULT ''",
            ):
                connection.execute(f"ALTER TABLE locations ADD COLUMN {definition}")
            cursor = connection.execute(
                """INSERT INTO entities (
                       type, display_name, summary, notes, created_at, updated_at
                   ) VALUES ('location', 'Fictional Hall', '', '', 'before', 'before')"""
            )
            location_id = int(cursor.lastrowid)
            connection.execute(
                """INSERT INTO locations (
                       entity_id, formatted_address, address_line_1, city,
                       state, post_code, country, latitude, longitude, source
                   ) VALUES (?, '1 Example Street, Example QLD 4000',
                             '1 Example Street', 'Example', 'Queensland',
                             '4000', 'Australia', '-27.5', '153.0',
                             'Fictional geocoder')""",
                (location_id,),
            )
            connection.executemany(
                """INSERT INTO provenance_metadata (
                       record_kind, record_id, field_name, provenance, updated_at
                   ) VALUES ('entity', ?, ?, 'manual', 'before')""",
                (
                    (location_id, "formatted_address"),
                    (location_id, "latitude"),
                    (location_id, "longitude"),
                ),
            )
            connection.commit()

            create_schema(connection)

            address = connection.execute(
                "SELECT * FROM location_addresses WHERE location_entity_id=?",
                (location_id,),
            ).fetchone()
            geometry = connection.execute(
                "SELECT * FROM location_geometries WHERE location_entity_id=?",
                (location_id,),
            ).fetchone()
            location_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(locations)")
            }
            migration = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_id=?",
                (place_migration,),
            ).fetchone()
            stale_provenance = connection.execute(
                """SELECT 1 FROM provenance_metadata
                   WHERE record_kind='entity' AND record_id=?
                     AND field_name IN ('formatted_address','latitude','longitude')""",
                (location_id,),
            ).fetchone()

        self.assertEqual("1 Example Street, Example QLD 4000", address["formatted_address"])
        self.assertEqual("physical", address["purpose"])
        self.assertEqual((1, 1), (address["is_current"], address["is_preferred"]))
        self.assertEqual("Source reported", address["confidence"])
        self.assertEqual("Point", geometry["geometry_type"])
        self.assertEqual("[153.0,-27.5]", geometry["coordinates_json"])
        self.assertEqual("representative_point", geometry["role"])
        self.assertEqual((1, 1), (geometry["is_current"], geometry["is_preferred"]))
        self.assertEqual({"entity_id"}, location_columns)
        self.assertIsNotNone(migration)
        self.assertIsNone(stale_provenance)

    def test_journey_contract_upgrade_adds_configuration_without_touching_entities(self) -> None:
        journey_migration = "20260805_34_journey_contract_foundation"
        with connect(self.database_path) as connection:
            create_schema_migration_table(connection)
            for migration_id, migration in SCHEMA_MIGRATIONS:
                if migration_id == journey_migration:
                    break
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, 'before')",
                    (migration_id,),
                )
            cursor = connection.execute(
                """INSERT INTO entities (
                       type, display_name, summary, notes, created_at, updated_at
                   ) VALUES ('person', 'Existing Fictional Person', '', '',
                             'before', 'before')"""
            )
            person_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO people (entity_id, given_name) VALUES (?, 'Existing')",
                (person_id,),
            )
            connection.commit()

            create_schema(connection)

            retained = connection.execute(
                "SELECT display_name FROM entities WHERE id=?", (person_id,)
            ).fetchone()
            tables = {
                row["name"]
                for row in connection.execute(
                    """SELECT name FROM sqlite_master
                       WHERE type='table' AND name IN (
                           'mobility_profiles', 'routing_policies'
                       )"""
                )
            }
            migration = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_id=?",
                (journey_migration,),
            ).fetchone()

        self.assertEqual("Existing Fictional Person", retained["display_name"])
        self.assertEqual({"mobility_profiles", "routing_policies"}, tables)
        self.assertIsNotNone(migration)

    def test_map_feature_list_upgrade_adds_portable_state_without_touching_entities(self) -> None:
        migration_id = "20260808_35_map_feature_lists"
        with connect(self.database_path) as connection:
            create_schema_migration_table(connection)
            for current_id, migration in SCHEMA_MIGRATIONS:
                if current_id == migration_id:
                    break
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, 'before')",
                    (current_id,),
                )
            cursor = connection.execute(
                """INSERT INTO entities (
                       type, display_name, summary, notes, created_at, updated_at
                   ) VALUES ('location', 'Existing Fictional Place', '', '',
                             'before', 'before')"""
            )
            location_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO locations (entity_id) VALUES (?)", (location_id,)
            )
            connection.commit()

            create_schema(connection)

            retained = connection.execute(
                "SELECT display_name FROM entities WHERE id=?", (location_id,)
            ).fetchone()
            favourites = connection.execute(
                "SELECT list_key, name, kind FROM map_feature_lists"
            ).fetchone()
            migration = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_id=?",
                (migration_id,),
            ).fetchone()

        self.assertEqual("Existing Fictional Place", retained["display_name"])
        self.assertEqual(
            ("favourites", "Favourites", "favourites"), tuple(favourites)
        )
        self.assertIsNotNone(migration)

    def test_task_retirement_refuses_to_remove_existing_task_data(self) -> None:
        with connect(self.database_path) as connection:
            create_schema_migration_table(connection)
            retirement_id = "20260801_31_retire_task_subsystem"
            for migration_id, migration in SCHEMA_MIGRATIONS:
                if migration_id == retirement_id:
                    break
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, 'before')",
                    (migration_id,),
                )
            task_list_id = int(connection.execute(
                "SELECT id FROM task_lists WHERE is_default = 1"
            ).fetchone()[0])
            connection.execute("PRAGMA ignore_check_constraints = ON")
            cursor = connection.execute(
                """INSERT INTO entities (
                       type, display_name, summary, notes, created_at, updated_at
                   ) VALUES ('task', 'Preserve me', '', '', 'before', 'before')"""
            )
            task_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO tasks (entity_id, task_list_id) VALUES (?, ?)",
                (task_id, task_list_id),
            )
            connection.execute("PRAGMA ignore_check_constraints = OFF")
            connection.commit()

            with self.assertRaisesRegex(RuntimeError, "Task retirement migration refused"):
                create_schema(connection)

            retained = connection.execute(
                "SELECT display_name FROM entities WHERE id = ?", (task_id,)
            ).fetchone()
            migration = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
                (retirement_id,),
            ).fetchone()

        self.assertEqual("Preserve me", retained["display_name"])
        self.assertIsNone(migration)

    def test_inbox_attention_upgrade_consolidates_active_timings(self) -> None:
        migration_id = "20260801_32_consolidate_inbox_attention"
        with connect(self.database_path) as connection:
            create_schema_migration_table(connection)
            for current_id, migration in SCHEMA_MIGRATIONS:
                if current_id == migration_id:
                    break
                migration(connection)
                connection.execute(
                    "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, 'before')",
                    (current_id,),
                )
            for delivery_key, timing in (("earlier", "1h"), ("later", "10m")):
                connection.execute(
                    """INSERT INTO inbox_items (
                           delivery_key, source_kind, source_id, occurrence_key,
                           reason, timing, title, due_at, delivered_at
                       ) VALUES (?, 'event', 42, '2026-08-02', 'reminder', ?,
                                 'Planning', '2026-08-02T00:00:00+00:00', 'before')""",
                    (delivery_key, timing),
                )
            connection.commit()

            create_schema(connection)

            rows = connection.execute(
                "SELECT timing, state FROM inbox_items ORDER BY timing"
            ).fetchall()
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(inbox_items)")
            }
            index = connection.execute(
                """SELECT sql FROM sqlite_master
                   WHERE type='index' AND name='idx_inbox_one_active_occurrence'"""
            ).fetchone()
            actions = connection.execute(
                "SELECT action FROM inbox_item_actions WHERE action='timing_superseded'"
            ).fetchall()

        self.assertEqual(
            [("10m", "active"), ("1h", "resolved")],
            [(row["timing"], row["state"]) for row in rows],
        )
        self.assertIn("attention_expires_at", columns)
        self.assertIn("WHERE state IN ('active', 'snoozed')", index["sql"])
        self.assertEqual(1, len(actions))

    def test_fresh_local_storage_creates_document_directory(self) -> None:
        documents_path = Path(self.temp_dir.name) / "instance" / "documents"

        with patch("app.config.DOCUMENT_STORAGE_DIR", documents_path):
            initialise_local_storage()

        self.assertTrue(documents_path.is_dir())

    def test_repeat_initialisation_does_not_reapply_migrations(self) -> None:
        initialise_database(self.database_path)
        first_rows = self.migration_rows()

        initialise_database(self.database_path)

        self.assertEqual(self.migration_rows(), first_rows)

    def test_external_calendar_reminder_context_upgrade_preserves_policies(
        self,
    ) -> None:
        initialise_database(self.database_path)
        with connect(self.database_path) as connection:
            connection.execute(
                """INSERT INTO reminder_policies (
                    context_kind, context_id, source_kind,
                    timings_json, updated_at
                ) VALUES ('calendar', 1, 'event', '["2h"]', 'before')"""
            )
            connection.executescript(
                """
                ALTER TABLE reminder_policies
                    RENAME TO reminder_policies_current;
                CREATE TABLE reminder_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_kind TEXT NOT NULL
                        CHECK (context_kind IN (
                            'global', 'calendar', 'task_list'
                        )),
                    context_id INTEGER NOT NULL DEFAULT 0,
                    source_kind TEXT NOT NULL
                        CHECK (source_kind IN (
                            'event', 'task_deadline', 'birthday',
                            'document_expiry'
                        )),
                    timings_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (context_kind, context_id, source_kind)
                );
                INSERT INTO reminder_policies
                SELECT * FROM reminder_policies_current;
                DROP TABLE reminder_policies_current;
                DELETE FROM schema_migrations
                WHERE migration_id =
                    '20260730_30_external_calendar_reminders';
                """
            )
            create_schema(connection)
            retained = connection.execute(
                """SELECT timings_json FROM reminder_policies
                   WHERE context_kind = 'calendar'
                     AND context_id = 1 AND source_kind = 'event'"""
            ).fetchone()
            connection.execute(
                """INSERT INTO reminder_policies (
                    context_kind, context_id, source_kind,
                    timings_json, updated_at
                ) VALUES (
                    'calendar_subscription', 7, 'event', '["1d"]', 'after'
                )"""
            )

        self.assertEqual('["2h"]', retained["timings_json"])

    def test_existing_database_is_adopted_without_losing_data(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('person', 'organisation', 'location')),
                    display_name TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_viewed_at TEXT NOT NULL DEFAULT '',
                    is_favourite INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO entities (
                    id, type, display_name, summary, notes, created_at, updated_at
                ) VALUES (1, 'person', 'Existing Person', '', '', 'before', 'before');
                """
            )

        initialise_database(self.database_path)

        self.assertEqual(
            tuple(row[0] for row in self.migration_rows()),
            SCHEMA_MIGRATION_IDS,
        )
        with connect(self.database_path) as connection:
            existing = connection.execute(
                "SELECT display_name, created_at FROM entities WHERE id = 1"
            ).fetchone()
            interchange_tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name IN ("
                    "'event_icalendar_identities', "
                    "'calendar_subscriptions', "
                    "'external_calendar_events'"
                    ")"
                )
            }
        self.assertEqual(existing["display_name"], "Existing Person")
        self.assertEqual(existing["created_at"], "before")
        self.assertEqual(
            interchange_tables,
            {
                "event_icalendar_identities",
                "calendar_subscriptions",
                "external_calendar_events",
            },
        )

    def test_existing_typed_tables_gain_new_domain_columns_additively(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('person','organisation','location','project','document','asset')),
                    display_name TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_viewed_at TEXT NOT NULL DEFAULT '',
                    is_favourite INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE projects (
                    entity_id INTEGER PRIMARY KEY, project_type TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE documents (
                    entity_id INTEGER PRIMARY KEY, document_type TEXT NOT NULL DEFAULT '',
                    document_date TEXT NOT NULL DEFAULT '', issuer TEXT NOT NULL DEFAULT '',
                    file_name TEXT NOT NULL DEFAULT '', file_path TEXT NOT NULL DEFAULT '',
                    mime_type TEXT NOT NULL DEFAULT '', file_size TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE assets (
                    entity_id INTEGER PRIMARY KEY, asset_type TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '', serial_number TEXT NOT NULL DEFAULT '',
                    acquisition_date TEXT NOT NULL DEFAULT '', value TEXT NOT NULL DEFAULT '',
                    latitude TEXT NOT NULL DEFAULT '', longitude TEXT NOT NULL DEFAULT ''
                );
                """
            )

        initialise_database(self.database_path)

        with connect(self.database_path) as connection:
            columns = {
                table: {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                for table in ("projects", "documents", "assets")
            }
        self.assertIn("ended_at", columns["projects"])
        self.assertTrue({"identifier", "expiry_date"} <= columns["documents"])
        self.assertTrue({"manufacturer", "model"} <= columns["assets"])

    def test_platform_audit_backfills_existing_canonical_timestamps(self) -> None:
        initialise_database(self.database_path)
        with connect(self.database_path) as connection:
            connection.execute("DELETE FROM schema_migrations WHERE migration_id = '20260628_07_backfill_platform_audit'")
            cursor = connection.execute("INSERT INTO entities(type,display_name,summary,notes,created_at,updated_at) VALUES('person','Historic Person','','','2020-01-01T00:00:00+00:00','2021-01-01T00:00:00+00:00')")
            entity_id = int(cursor.lastrowid)
            connection.execute("INSERT INTO people(entity_id,given_name,family_name) VALUES(?, 'Historic', 'Person')", (entity_id,))
            connection.commit()
            create_schema(connection)
            events = connection.execute(
                "SELECT event_type FROM audit_events a JOIN audit_event_records r ON r.event_id=a.id WHERE r.record_kind='entity' AND r.record_id=? ORDER BY a.id",
                (entity_id,),
            ).fetchall()
        self.assertEqual(["create", "edit"], [row["event_type"] for row in events])



if __name__ == "__main__":
    unittest.main()
