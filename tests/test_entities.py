import tempfile
import unittest
from pathlib import Path

from app.db import (
    connect,
    create_entity,
    delete_entity,
    get_entity,
    initialise_database,
    list_entities,
    normalise_form_values,
    update_entity,
    validate_entity_values,
)
from app.entities import DEFINITIONS_BY_SLUG, ENTITY_DEFINITIONS


class EntityDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        initialise_database(self.database_path)
        self.definition = DEFINITIONS_BY_SLUG["people"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_update_list_and_delete_person(self) -> None:
        with connect(self.database_path) as connection:
            entity_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "Mathematician",
                    "notes": "Known for early computing work.",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "email": "",
                    "phone": "",
                },
            )

            created = get_entity(connection, self.definition, entity_id)
            self.assertIsNotNone(created)
            self.assertEqual(created.display_name, "Ada Lovelace")
            self.assertEqual(created.field_value(self.definition.fields[0]), "Ada")

            update_entity(
                connection,
                self.definition,
                entity_id,
                {
                    "display_name": "Augusta Ada Lovelace",
                    "summary": "Computing pioneer",
                    "notes": "",
                    "given_name": "Augusta Ada",
                    "family_name": "Lovelace",
                    "email": "ada@example.test",
                    "phone": "",
                },
            )

            updated = get_entity(connection, self.definition, entity_id)
            self.assertEqual(updated.display_name, "Augusta Ada Lovelace")
            self.assertEqual(updated.metadata["email"], "ada@example.test")

            listed = list_entities(connection, self.definition)
            self.assertEqual(len(listed), 1)

            delete_entity(connection, self.definition, entity_id)
            self.assertIsNone(get_entity(connection, self.definition, entity_id))

    def test_all_entity_definitions_use_shared_crud_flow(self) -> None:
        with connect(self.database_path) as connection:
            for definition in ENTITY_DEFINITIONS:
                values = {
                    "display_name": f"Example {definition.singular}",
                    "summary": "Shared flow",
                    "notes": "",
                }
                values.update({field.name: f"{field.label} value" for field in definition.fields})

                entity_id = create_entity(connection, definition, values)
                record = get_entity(connection, definition, entity_id)

                self.assertIsNotNone(record)
                self.assertEqual(record.definition, definition)
                self.assertEqual(record.display_name, f"Example {definition.singular}")
                self.assertEqual(record.to_form_values()["summary"], "Shared flow")
                self.assertEqual(len(list_entities(connection, definition)), 1)

                delete_entity(connection, definition, entity_id)
                self.assertIsNone(get_entity(connection, definition, entity_id))

    def test_display_name_is_required(self) -> None:
        values = normalise_form_values(self.definition, {"display_name": "  "})
        errors = validate_entity_values(self.definition, values)
        self.assertEqual(errors, ["Person name is required."])


if __name__ == "__main__":
    unittest.main()

