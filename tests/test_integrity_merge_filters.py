import tempfile
import unittest
from pathlib import Path

from app.db import connect, create_entity, create_relationship, get_entity_by_id, initialise_database, search_entities
from app.entities import DEFINITIONS_BY_SLUG
from app.entity_merge import list_entity_history, merge_entities, preview_entity_merge
from app.integrity import audit_relationships


class DataIntegrityMergeAndFilterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "milestone.sqlite3"
        initialise_database(self.database_path)
        self.people = DEFINITIONS_BY_SLUG["people"]
        self.organisations = DEFINITIONS_BY_SLUG["organisations"]
        self.locations = DEFINITIONS_BY_SLUG["locations"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def person(self, name, birthday="", email="", notes=""):
        with connect(self.database_path) as connection:
            parts = name.split(maxsplit=1)
            return create_entity(connection, self.people, {"display_name": name, "given_name": parts[0], "family_name": parts[1] if len(parts) > 1 else "", "birthday": birthday, "email": email, "notes": notes, "sex": "Unknown"})

    def test_integrity_audit_detects_duplicates_broken_types_and_suspicious_roles(self):
        first = self.person("First")
        second = self.person("Second")
        with connect(self.database_path) as connection:
            base = {"source_entity_id": str(first), "target_entity_id": str(second), "status": "active", "started_at": "", "ended_at": "", "notes": ""}
            create_relationship(connection, {**base, "type": "spouse_of"})
            create_relationship(connection, {**base, "type": "spouse_of"})
            create_relationship(connection, {**base, "type": "parent_child"})
            now = "2026-01-01T00:00:00"
            connection.execute("INSERT INTO relationships (source_entity_id,target_entity_id,type,created_at,updated_at) VALUES (?,?,?,?,?)", (first, second, "missing_catalogue_type", now, now))
            connection.commit()
            codes = {warning.code for warning in audit_relationships(connection)}
        self.assertTrue({"duplicate_relationship", "broken_type", "suspicious_family_roles"} <= codes)

    def test_merge_fills_blanks_combines_notes_repoints_and_deduplicates(self):
        survivor = self.person("Ada Lovelace", email="", notes="First note")
        duplicate = self.person("Augusta Ada", email="ada@example.test", notes="Second note")
        other = self.person("Charles Babbage")
        with connect(self.database_path) as connection:
            values = {"target_entity_id": str(other), "type": "friend_of", "status": "active", "started_at": "", "ended_at": "", "notes": ""}
            create_relationship(connection, {**values, "source_entity_id": str(survivor)})
            create_relationship(connection, {**values, "source_entity_id": str(duplicate)})
            preview = preview_entity_merge(connection, survivor, duplicate)
            self.assertEqual(preview.duplicate_relationships_to_remove, 1)
            merge_entities(connection, survivor, duplicate)
            merged = get_entity_by_id(connection, survivor)
            relationships = connection.execute("SELECT * FROM relationships").fetchall()
            history = list_entity_history(connection, survivor)
        self.assertIsNone(self._get(duplicate))
        self.assertEqual(merged.metadata["email"], "ada@example.test")
        self.assertEqual(merged.notes, "First note\n\nSecond note")
        self.assertEqual(len(relationships), 1)
        self.assertEqual(history[0]["event_type"], "merge")
        self.assertIn("Augusta Ada", history[0]["details"])

    def test_merge_preserves_and_repoints_recycled_relationships(self):
        survivor = self.person("Survivor")
        duplicate = self.person("Duplicate")
        other = self.person("Other")
        with connect(self.database_path) as connection:
            relationship_id = create_relationship(connection, {"source_entity_id": str(duplicate), "target_entity_id": str(other), "type": "friend_of"})
            connection.execute("UPDATE relationships SET deleted_at='2026-01-01T00:00:00+00:00' WHERE id=?", (relationship_id,))
            connection.commit()
            preview = preview_entity_merge(connection, survivor, duplicate)
            self.assertEqual(0, preview.active_relationships_to_repoint)
            self.assertEqual(1, preview.recycled_relationships_to_repoint)
            merge_entities(connection, survivor, duplicate)
            row = connection.execute("SELECT * FROM relationships WHERE id=?", (relationship_id,)).fetchone()
        self.assertEqual(survivor, row["source_entity_id"])
        self.assertTrue(row["deleted_at"])

    def test_structured_filters_cover_birthdays_and_missing_locations(self):
        january = self.person("January", "1980-01-03")
        born_1980 = self.person("December", "1980-12-10")
        missing = self.person("Unknown")
        with connect(self.database_path) as connection:
            org_without = create_entity(connection, self.organisations, {"display_name": "No Address"})
            org_with = create_entity(connection, self.organisations, {"display_name": "Has Address"})
            location = create_entity(connection, self.locations, {"display_name": "Office"})
            create_relationship(connection, {"source_entity_id": str(org_with), "target_entity_id": str(location), "type": "located_at_org", "status": "active", "started_at": "", "ended_at": "", "notes": ""})
            jan_results = search_entities(connection, filter_key="birthday_month", filter_value="1")
            year_results = search_entities(connection, filter_key="birth_year", filter_value="1980")
            missing_results = search_entities(connection, filter_key="no_birthday")
            org_results = search_entities(connection, filter_key="no_location")
        self.assertEqual([item["entity"].id for item in jan_results], [january])
        self.assertEqual({item["entity"].id for item in year_results}, {january, born_1980})
        self.assertEqual([item["entity"].id for item in missing_results], [missing])
        self.assertEqual([item["entity"].id for item in org_results], [org_without])

    def _get(self, entity_id):
        with connect(self.database_path) as connection:
            return get_entity_by_id(connection, entity_id)


if __name__ == "__main__":
    unittest.main()
