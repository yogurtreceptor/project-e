import tempfile
import unittest
from pathlib import Path

from app.audit import list_audit_events
from app.db import (
    connect,
    create_entity,
    create_relationship,
    delete_entity,
    delete_relationship,
    entity_dependency_counts,
    get_entity,
    get_entity_by_id,
    initialise_database,
    list_deleted_entities,
    list_entities,
    list_relationships,
    list_relationships_for_entity,
    list_deleted_relationships,
    list_all_entities,
    restore_relationship,
    permanent_delete_entity,
    restore_entity,
    search_entities,
)
from app.entities import DEFINITIONS_BY_TYPE, ENTITY_DEFINITIONS
from app import views
from app.timeline import registry as timeline_registry


def values_for(definition, name):
    values = {"display_name": name, "notes": ""}
    if definition.type == "person":
        values.update({"given_name": name, "family_name": "", "sex": "Unknown"})
    return values


class SoftDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "soft-delete.postgres"
        initialise_database(self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_entity_types_are_hidden_and_listed_in_recycle_bin(self):
        with connect(self.database_path) as connection:
            ids = []
            for definition in ENTITY_DEFINITIONS:
                entity_id = create_entity(connection, definition, values_for(definition, f"Deleted {definition.singular}"))
                delete_entity(connection, definition, entity_id)
                ids.append(entity_id)
                self.assertIsNone(get_entity(connection, definition, entity_id))
                self.assertEqual([], list_entities(connection, definition))
            self.assertEqual([], search_entities(connection, "Deleted"))
            self.assertEqual(set(ids), {record.id for record in list_deleted_entities(connection)})
            self.assertTrue(all(get_entity_by_id(connection, item, include_deleted=True).deleted_at for item in ids))

    def test_restore_reveals_only_relationships_whose_other_endpoint_is_active(self):
        person = DEFINITIONS_BY_TYPE["person"]
        with connect(self.database_path) as connection:
            first = create_entity(connection, person, values_for(person, "First"))
            second = create_entity(connection, person, values_for(person, "Second"))
            third = create_entity(connection, person, values_for(person, "Third"))
            create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(second), "type": "knows"})
            create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(third), "type": "knows"})
            delete_entity(connection, person, first)
            delete_entity(connection, person, third)
            self.assertEqual([], list_relationships(connection))
            self.assertTrue(restore_entity(connection, first))
            self.assertEqual(1, len(list_relationships_for_entity(connection, first)))
            self.assertIsNone(get_entity(connection, person, third))
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM relationships").fetchone()[0])

    def test_relationship_delete_restore_preserves_record_audit_and_timeline_dates(self):
        person = DEFINITIONS_BY_TYPE["person"]
        with connect(self.database_path) as connection:
            first = create_entity(connection, person, values_for(person, "First"))
            second = create_entity(connection, person, values_for(person, "Second"))
            relationship_id = create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(second), "type": "knows", "started_at": "2020-01-01"})
            self.assertTrue(delete_relationship(connection, relationship_id))
            self.assertEqual([], list_relationships(connection))
            self.assertEqual([], timeline_registry.derive_all(list_all_entities(connection), list_relationships(connection)))
            self.assertEqual([relationship_id], [record.id for record in list_deleted_relationships(connection)])
            self.assertTrue(restore_relationship(connection, relationship_id))
            self.assertEqual([relationship_id], [record.id for record in list_relationships(connection)])
            events = list_audit_events(connection, "relationship", relationship_id)
            self.assertEqual(["restore", "delete", "create"], [event.event_type for event in events])
            self.assertEqual("2020-01-01", list_relationships(connection)[0].started_at)
            self.assertEqual(["2020-01-01"], [event.date for event in timeline_registry.derive_all(list_all_entities(connection), list_relationships(connection))])

    def test_permanent_delete_requires_deleted_record_and_preserves_audit(self):
        person = DEFINITIONS_BY_TYPE["person"]
        with connect(self.database_path) as connection:
            first = create_entity(connection, person, values_for(person, "First"))
            second = create_entity(connection, person, values_for(person, "Second"))
            create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(second), "type": "knows"})
            with self.assertRaises(ValueError):
                permanent_delete_entity(connection, first)
            delete_entity(connection, person, first)
            self.assertEqual(1, entity_dependency_counts(connection, first)["relationships"])
            permanent_delete_entity(connection, first)
            self.assertIsNone(get_entity_by_id(connection, first, include_deleted=True))
            self.assertEqual(0, connection.execute("SELECT COUNT(*) FROM relationships").fetchone()[0])
            self.assertIn("permanent_delete", [event.event_type for event in list_audit_events(connection, "entity", first)])

    def test_recycle_bin_copy_distinguishes_archived_and_deleted_and_warns_about_dependencies(self):
        person = DEFINITIONS_BY_TYPE["person"]
        with connect(self.database_path) as connection:
            entity_id = create_entity(connection, person, values_for(person, "Deleted Person"))
            delete_entity(connection, person, entity_id)
            record = get_entity_by_id(connection, entity_id, include_deleted=True)
        page = views.recycle_bin_page([record])
        confirmation = views.permanent_delete_confirmation_page(record, {"relationships": 2, "active_relationships": 1, "recycled_relationships": 1, "journal_entries": 1})
        self.assertIn("Archived records remain active", page)
        self.assertIn("Deleted Person", page)
        self.assertIn("2 relationships", confirmation)
        self.assertIn("1 active, 1 recycled", confirmation)
        self.assertIn("1 journal entry", confirmation)
        self.assertIn("cannot be undone", confirmation)


if __name__ == "__main__":
    unittest.main()
