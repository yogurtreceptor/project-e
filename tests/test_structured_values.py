import tempfile
import unittest
from pathlib import Path

from app import views
from app.db import (
    connect,
    create_entity,
    initialise_database,
    normalise_form_values,
    normalise_relationship_values,
    validate_entity_values,
    validate_relationship_values,
)
from app.entities import DEFINITIONS_BY_SLUG


class StructuredValueTests(unittest.TestCase):
    def test_entity_dates_require_real_iso_calendar_dates(self) -> None:
        definition = DEFINITIONS_BY_SLUG["people"]
        values = normalise_form_values(
            definition,
            {"given_name": "Example", "birthday": "2025-02-29"},
        )
        self.assertEqual(
            validate_entity_values(definition, values),
            ["Birthday must be a valid date in YYYY-MM-DD format."],
        )

        values["birthday"] = "2024-02-29"
        self.assertEqual(validate_entity_values(definition, values), [])

    def test_coordinates_are_normalised_and_range_checked(self) -> None:
        definition = DEFINITIONS_BY_SLUG["locations"]
        values = normalise_form_values(
            definition,
            {
                "display_name": "Brisbane",
                "latitude": " -27.4700 ",
                "longitude": "+153.025100",
            },
        )
        self.assertEqual(values["latitude"], "-27.47")
        self.assertEqual(values["longitude"], "153.0251")
        self.assertEqual(validate_entity_values(definition, values), [])

        values["latitude"] = "90.01"
        values["longitude"] = "not-a-number"
        self.assertEqual(
            validate_entity_values(definition, values),
            [
                "Latitude must be between -90 and 90.",
                "Longitude must be a valid number.",
            ],
        )

    def test_coordinate_form_controls_expose_geographic_limits(self) -> None:
        definition = DEFINITIONS_BY_SLUG["locations"]
        html = views.entity_form_page(definition, {}, [], "Create")
        self.assertIn('id="latitude" name="latitude" type="number" value="" min="-90" max="90" step="any"', html)
        self.assertIn('id="longitude" name="longitude" type="number" value="" min="-180" max="180" step="any"', html)

    def test_blank_optional_structured_values_remain_valid(self) -> None:
        definition = DEFINITIONS_BY_SLUG["assets"]
        values = normalise_form_values(definition, {"display_name": "Laptop"})
        self.assertEqual(values["acquisition_date"], "")
        self.assertEqual(values["value"], "")
        self.assertEqual(values["latitude"], "")
        self.assertEqual(validate_entity_values(definition, values), [])

    def test_asset_whole_number_is_normalised_without_accepting_currency_text(self) -> None:
        definition = DEFINITIONS_BY_SLUG["assets"]
        values = normalise_form_values(
            definition, {"display_name": "Laptop", "value": "001200"}
        )
        self.assertEqual(values["value"], "1200")
        self.assertEqual(validate_entity_values(definition, values), [])

        values["value"] = "$1200"
        self.assertEqual(
            validate_entity_values(definition, values),
            ["Value must be a whole number without a dollar sign."],
        )

    def test_relationship_dates_use_the_same_calendar_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "relationships.sqlite3"
            initialise_database(database_path)
            person = DEFINITIONS_BY_SLUG["people"]
            with connect(database_path) as connection:
                first_id = create_entity(connection, person, {"display_name": "First"})
                second_id = create_entity(connection, person, {"display_name": "Second"})
                values = normalise_relationship_values(
                    {
                        "source_entity_id": str(first_id),
                        "target_entity_id": str(second_id),
                        "type": "friend_of",
                        "status": "active",
                        "started_at": "2026-13-01",
                        "ended_at": "",
                    }
                )
                errors = validate_relationship_values(connection, values)

        self.assertIn(
            "Started must be a valid date in YYYY-MM-DD format.", errors
        )


if __name__ == "__main__":
    unittest.main()
