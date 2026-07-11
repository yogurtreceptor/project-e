import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import initialise_local_storage
from app.db import connect, initialise_database
from app.db_schema import SCHEMA_MIGRATION_IDS, create_schema


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
        self.assertIn("schema_migrations", tables)
        self.assertIn("journal_entries", tables)
        with connect(self.database_path) as connection:
            entity_columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
            project_columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
            document_columns = {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}
            asset_columns = {row["name"] for row in connection.execute("PRAGMA table_info(assets)")}
            relationship_columns = {row["name"] for row in connection.execute("PRAGMA table_info(relationships)")}
        self.assertIn("deleted_at", entity_columns)
        self.assertIn("ended_at", project_columns)
        self.assertTrue({"identifier", "expiry_date"} <= document_columns)
        self.assertTrue({"manufacturer", "model"} <= asset_columns)
        self.assertIn("deleted_at", relationship_columns)

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
        self.assertEqual(existing["display_name"], "Existing Person")
        self.assertEqual(existing["created_at"], "before")

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
