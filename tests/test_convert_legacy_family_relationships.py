import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from app.db_schema import create_schema
from app.db_support import utc_now
from tools.convert_legacy_family_relationships import main


class LegacyFamilyConverterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "project-e.sqlite3"
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            create_schema(connection)
            now = utc_now()
            for name in ("Older", "Younger", "Other"):
                cursor = connection.execute(
                    "INSERT INTO entities(type,display_name,created_at,updated_at) VALUES('person',?,?,?)", (name, now, now))
                connection.execute("INSERT INTO people(entity_id,given_name,sex) VALUES(?,?,?)", (cursor.lastrowid, name, "Unknown"))

    def tearDown(self):
        self.temporary.cleanup()

    def insert_relationship(self, source, target, key):
        with sqlite3.connect(self.path) as connection:
            now = utc_now()
            return connection.execute(
                """INSERT INTO relationships
                   (source_entity_id,target_entity_id,type,status,created_at,updated_at)
                   VALUES(?,?,?,'active',?,?)""", (source, target, key, now, now)).lastrowid

    def run_tool(self, *arguments):
        output = StringIO()
        with redirect_stdout(output):
            result = main([str(self.path), *arguments])
        return result, output.getvalue()

    def test_dry_run_does_not_modify_database(self):
        relationship_id = self.insert_relationship(1, 2, "father_of")
        result, output = self.run_tool()
        self.assertEqual(0, result)
        self.assertIn("father_of -> parent_child", output)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual("father_of", connection.execute("SELECT type FROM relationships WHERE id=?", (relationship_id,)).fetchone()[0])

    def test_apply_converts_and_reverses_direction_with_backup(self):
        relationship_id = self.insert_relationship(2, 1, "daughter_of")
        backup = Path(self.temporary.name) / "before.sqlite3"
        result, _ = self.run_tool("--apply", "--backup", str(backup))
        self.assertEqual(0, result)
        self.assertTrue(backup.is_file())
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                """SELECT r.source_entity_id,r.target_entity_id,r.type,e.key
                   FROM relationships r JOIN taxonomy_entries e ON e.id=r.taxonomy_entry_id WHERE r.id=?""",
                (relationship_id,)).fetchone()
            self.assertEqual((1, 2, "parent_child", "parent_child"), row)

    def test_duplicate_is_reported_and_left_unchanged(self):
        self.insert_relationship(1, 2, "parent_child")
        legacy_id = self.insert_relationship(1, 2, "mother_of")
        backup = Path(self.temporary.name) / "before.sqlite3"
        result, output = self.run_tool("--apply", "--backup", str(backup))
        self.assertEqual(1, result)
        self.assertIn("CONFLICT", output)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual("mother_of", connection.execute("SELECT type FROM relationships WHERE id=?", (legacy_id,)).fetchone()[0])


if __name__ == "__main__":
    unittest.main()
