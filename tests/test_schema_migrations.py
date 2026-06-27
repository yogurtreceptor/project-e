import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db import connect, initialise_database
from app.db_schema import SCHEMA_MIGRATION_IDS


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


if __name__ == "__main__":
    unittest.main()
