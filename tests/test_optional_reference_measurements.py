import tempfile
import unittest
from pathlib import Path

from app import views
from app.db import (
    connect,
    create_entity,
    get_entity,
    get_measurement,
    initialise_database,
    list_reference_items,
    list_units,
    normalise_form_values,
    update_entity,
    validate_entity_values,
)
from app.entities import DEFINITIONS_BY_TYPE


class OptionalReferenceMeasurementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "optional.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)
        self.people = DEFINITIONS_BY_TYPE["person"]

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def test_person_optional_fields_use_normalised_storage_and_display_labels(self) -> None:
        languages = [
            item for item in list_reference_items(self.connection, "language")
            if item.key in {"en", "fr"}
        ]
        countries = list_reference_items(self.connection, "country")
        centimetres = next(
            unit for unit in list_units(self.connection, "length") if unit.key == "centimetre"
        )
        kilograms = next(
            unit for unit in list_units(self.connection, "mass") if unit.key == "kilogram"
        )
        values = normalise_form_values(
            self.people,
            {
                "given_name": "Example",
                "family_name": "Person",
                "height": "180",
                "height__unit": str(centimetres.id),
                "weight": "75",
                "weight__unit": str(kilograms.id),
                "languages": ",".join(str(item.id) for item in languages),
                "nationalities": str(next(item.id for item in countries if item.key == "au")),
            },
        )
        self.assertEqual([], validate_entity_values(self.people, values, self.connection))

        person_id = create_entity(self.connection, self.people, values)
        person = get_entity(self.connection, self.people, person_id)

        self.assertEqual("1.8", get_measurement(self.connection, person_id, "height").canonical_value.to_eng_string())
        self.assertEqual("180 cm", person.metadata["height"])
        self.assertEqual("75 kg", person.metadata["weight"])
        self.assertEqual("English, French", person.metadata["languages"])
        self.assertEqual("Australia", person.metadata["nationalities"])
        detail = views.entity_detail_page(person, [])
        self.assertIn("180 cm", detail)
        self.assertIn("English, French", detail)

    def test_optional_fields_can_be_cleared_on_edit(self) -> None:
        english = list_reference_items(self.connection, "language")[0]
        metres = next(unit for unit in list_units(self.connection, "length") if unit.key == "metre")
        values = normalise_form_values(
            self.people,
            {"given_name": "Example", "height": "1.7", "height__unit": str(metres.id), "languages": str(english.id)},
        )
        person_id = create_entity(self.connection, self.people, values)

        cleared = normalise_form_values(self.people, {"given_name": "Example"})
        update_entity(self.connection, self.people, person_id, cleared)
        person = get_entity(self.connection, self.people, person_id)

        self.assertEqual("", person.metadata["height"])
        self.assertEqual("", person.metadata["languages"])
        self.assertIsNone(get_measurement(self.connection, person_id, "height"))

    def test_form_uses_catalogue_options_and_unit_pairs(self) -> None:
        options = {
            "languages": [("1", "English"), ("2", "French")],
            "nationalities": [("3", "Australia")],
            "height": [("4", "Centimetre (cm)")],
            "weight": [("5", "Kilogram (kg)")],
        }
        html = views.entity_form_page(self.people, {}, [], "Create", field_options=options)

        self.assertIn('id="languages__search" type="search"', html)
        self.assertIn('type="checkbox" name="languages" value="1"', html)
        self.assertIn('data-search-text="english"', html)
        self.assertIn("data-reference-search", html)
        self.assertIn('name="height__unit"', html)
        self.assertIn("Centimetre (cm)", html)
        for field in ("Height", "Weight", "Languages", "Nationalities"):
            self.assertIn(f">{field}</button>", html)

    def test_invalid_cross_type_reference_and_unit_are_rejected(self) -> None:
        country = list_reference_items(self.connection, "country")[0]
        kilograms = next(unit for unit in list_units(self.connection, "mass") if unit.key == "kilogram")
        values = normalise_form_values(
            self.people,
            {"given_name": "Example", "height": "180", "height__unit": str(kilograms.id), "languages": str(country.id)},
        )
        errors = validate_entity_values(self.people, values, self.connection)
        self.assertIn("Height unit is invalid.", errors)
        self.assertIn("Languages selection is invalid.", errors)


if __name__ == "__main__":
    unittest.main()
