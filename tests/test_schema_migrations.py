import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import initialise_local_storage
from app.db import connect, initialise_database
from app.db_schema import SCHEMA_MIGRATION_IDS


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "postgres-test-id"

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_database_records_postgresql_baseline(self):
        initialise_database(self.database)
        with connect(self.database) as connection:
            rows = connection.execute(
                "SELECT migration_id,checksum,applied_at FROM schema_migrations ORDER BY migration_id"
            ).fetchall()
            tables = {
                row[0] for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema()"
                )
            }
        self.assertEqual(SCHEMA_MIGRATION_IDS, tuple(row["migration_id"] for row in rows))
        self.assertTrue(all(row["checksum"] and row["applied_at"] for row in rows))
        self.assertTrue({"entities", "relationships", "journal_entries", "schema_migrations"} <= tables)

    def test_repeat_initialisation_is_idempotent(self):
        initialise_database(self.database)
        with connect(self.database) as connection:
            before = connection.execute("SELECT * FROM schema_migrations").fetchall()
        initialise_database(self.database)
        with connect(self.database) as connection:
            after = connection.execute("SELECT * FROM schema_migrations").fetchall()
        self.assertEqual(before, after)

    def test_fresh_local_storage_creates_document_directory(self):
        documents = Path(self.temp.name) / "instance" / "documents"
        with patch("app.config.DOCUMENT_STORAGE_DIR", documents):
            initialise_local_storage()
        self.assertTrue(documents.is_dir())


if __name__ == "__main__":
    unittest.main()
