import tempfile
import unittest
from pathlib import Path

from app.db import connect, create_entity, create_relationship, get_entity, initialise_database
from app.entities import DEFINITIONS_BY_SLUG
from app.relationships import relationship_types_for_pair
from app.taxonomy import (
    archive_entry,
    create_entry,
    get_entry,
    list_entries,
    load_relationship_catalog,
    organisation_options,
    reparent_entry,
)
from app.view_pages.forms import taxonomy_field


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "taxonomy.sqlite3"
        initialise_database(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_seeded_organisation_paths_and_searchable_hierarchy(self):
        with connect(self.path) as connection:
            entries = list_entries(connection, "organisation_classification")
            bank = next(item for item in entries if item.key == "bank")
            html = taxonomy_field("organisation_type", "Organisation classification", organisation_options(connection), {"organisation_type": str(bank.id)})
        self.assertEqual("Business › Finance › Bank", bank.path)
        self.assertIn('type="search"', html)
        self.assertIn('data-taxonomy-level="1"', html)
        self.assertIn('data-taxonomy-level="2"', html)

    def test_creation_depth_duplicate_and_archival_rules(self):
        with connect(self.path) as connection:
            root = create_entry(connection, "organisation_classification", "Research")
            child = create_entry(connection, "organisation_classification", "Laboratory", root)
            leaf = create_entry(connection, "organisation_classification", "Robotics", child)
            with self.assertRaises(ValueError):
                create_entry(connection, "organisation_classification", "Too deep", leaf)
            with self.assertRaises(Exception):
                create_entry(connection, "organisation_classification", "Laboratory", root)
            with self.assertRaises(ValueError):
                reparent_entry(connection, root, leaf)
            archive_entry(connection, root)
            active_ids = {entry.id for entry in list_entries(connection, "organisation_classification")}
            all_ids = {entry.id for entry in list_entries(connection, "organisation_classification", include_archived=True)}
        self.assertNotIn(leaf, active_ids)
        self.assertIn(leaf, all_ids)

    def test_legacy_organisation_value_is_preserved_as_archived_assignment(self):
        definition = DEFINITIONS_BY_SLUG["organisations"]
        with connect(self.path) as connection:
            entity_id = create_entity(connection, definition, {"display_name": "Odd Society", "notes": "", "organisation_type": "Research collective", "website": "", "phone": "", "email": ""})
            record = get_entity(connection, definition, entity_id)
            entry_id = int(record.metadata["organisation_type__taxonomy_entry_id"])
            entry = get_entry(connection, entry_id)
        self.assertEqual("Research collective", record.metadata["organisation_type"])
        self.assertFalse(entry.active)

    def test_custom_relationship_definition_uses_existing_inverse_model(self):
        with connect(self.path) as connection:
            root = next(e for e in list_entries(connection, "relationship_type") if e.path == "Social")
            entry_id = create_entry(connection, "relationship_type", "Mentor", root.id, {
                "source_entity_type": "person", "target_entity_type": "person", "directional": "1",
                "source_role": "Mentor", "target_role": "Mentee", "source_label": "mentors", "target_label": "mentored by",
            })
            load_relationship_catalog(connection)
            entry = get_entry(connection, entry_id)
        types = {item.key: item for item in relationship_types_for_pair("person", "person")}
        relationship_type = types[entry.key]
        self.assertEqual("mentors", relationship_type.label_for_role("source"))
        self.assertEqual("mentored by", relationship_type.label_for_role("target"))

    def test_relationship_rows_receive_taxonomy_foreign_key(self):
        definition = DEFINITIONS_BY_SLUG["people"]
        with connect(self.path) as connection:
            values = {"notes": "", "middle_name": "", "email": "", "phone": "", "sex": "Unknown", "birthday": ""}
            first = create_entity(connection, definition, {**values, "display_name": "First Person", "given_name": "First", "family_name": "Person"})
            second = create_entity(connection, definition, {**values, "display_name": "Second Person", "given_name": "Second", "family_name": "Person"})
            relationship_id = create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(second), "type": "friend_of", "status": "active"})
            row = connection.execute("SELECT type,taxonomy_entry_id FROM relationships WHERE id=?", (relationship_id,)).fetchone()
            key = connection.execute("SELECT key FROM taxonomy_entries WHERE id=?", (row["taxonomy_entry_id"],)).fetchone()["key"]
        self.assertEqual("friend_of", row["type"])
        self.assertEqual("friend_of", key)


if __name__ == "__main__":
    unittest.main()
