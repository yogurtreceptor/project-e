import tempfile
import unittest
from pathlib import Path

from app.db import (
    connect,
    create_entity,
    create_reference_item,
    get_reference_item,
    initialise_database,
    list_entity_reference_values,
    list_reference_items,
    replace_entity_reference_values,
)
from app.entities import DEFINITIONS_BY_TYPE


class ReferenceDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "reference.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_minimum_local_catalogue_is_seeded_with_parent_relationships(self) -> None:
        countries = list_reference_items(self.connection, "country")
        languages = list_reference_items(self.connection, "language")
        regions = list_reference_items(self.connection, "region")

        self.assertGreaterEqual(len(countries), 240)
        self.assertGreaterEqual(len(languages), 180)
        self.assertIn("Australia", [item.name for item in countries])
        self.assertIn("United Kingdom", [item.name for item in countries])
        self.assertIn("English", [item.name for item in languages])
        self.assertIn("French", [item.name for item in languages])
        australia = next(item for item in countries if item.code == "AU")
        self.assertEqual(australia.id, regions[0].parent_id)

    def test_catalogue_is_extensible_without_schema_changes(self) -> None:
        item_id = create_reference_item(
            self.connection, "language", "example-language", "Example language", code="x-example"
        )
        item = get_reference_item(self.connection, item_id)

        self.assertEqual("Example language", item.name)
        self.assertIn(item, list_reference_items(self.connection, "language"))

    def test_entity_values_reference_catalogue_rows_and_preserve_order(self) -> None:
        person_id = create_entity(
            self.connection,
            DEFINITIONS_BY_TYPE["person"],
            {"given_name": "Example", "family_name": "Person"},
        )
        language_ids = [item.id for item in list_reference_items(self.connection, "language")]

        replace_entity_reference_values(
            self.connection, person_id, "spoken_languages", language_ids[::-1], "language"
        )

        values = list_entity_reference_values(
            self.connection, person_id, "spoken_languages"
        )
        self.assertEqual(language_ids[::-1], [item.id for item in values])
        with self.assertRaises(ValueError):
            replace_entity_reference_values(
                self.connection, person_id, "spoken_languages", [99999], "language"
            )


if __name__ == "__main__":
    unittest.main()
