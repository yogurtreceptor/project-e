from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from app.db import (
    connect,
    create_entity,
    get_measurement,
    initialise_database,
    list_units,
    set_measurement,
)
from app.entities import DEFINITIONS_BY_TYPE


class UnitInfrastructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "units.postgres"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)
        self.person_id = create_entity(
            self.connection,
            DEFINITIONS_BY_TYPE["person"],
            {"given_name": "Example", "family_name": "Person"},
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.temp_dir.cleanup()

    def unit(self, category: str, key: str):
        return next(unit for unit in list_units(self.connection, category) if unit.key == key)

    def test_categories_have_one_canonical_unit_and_are_extensible(self) -> None:
        for category in ("length", "mass", "temperature"):
            units = list_units(self.connection, category)
            self.assertGreaterEqual(len(units), 2)
            self.assertEqual(1, sum(unit.canonical for unit in units))

    def test_length_is_stored_canonically_and_displayed_in_selected_unit(self) -> None:
        centimetres = self.unit("length", "centimetre")
        set_measurement(
            self.connection, self.person_id, "height", "length", "180", centimetres.id
        )

        stored = self.connection.execute(
            "SELECT canonical_value FROM entity_measurements WHERE entity_id=? AND field_name='height'",
            (self.person_id,),
        ).fetchone()
        measurement = get_measurement(self.connection, self.person_id, "height")
        self.assertEqual("1.8", stored["canonical_value"])
        self.assertEqual(Decimal("180"), measurement.display_value)
        self.assertEqual("180 cm", measurement.display_text)

    def test_mass_and_affine_temperature_conversions_round_trip(self) -> None:
        pounds = self.unit("mass", "pound")
        fahrenheit = self.unit("temperature", "fahrenheit")

        set_measurement(
            self.connection, self.person_id, "weight", "mass", "220", pounds.id
        )
        set_measurement(
            self.connection, self.person_id, "temperature", "temperature", "32", fahrenheit.id
        )

        weight = get_measurement(self.connection, self.person_id, "weight")
        temperature = get_measurement(self.connection, self.person_id, "temperature")
        self.assertEqual(Decimal("99.79032140"), weight.canonical_value)
        self.assertEqual(Decimal("220"), weight.display_value)
        self.assertAlmostEqual(Decimal("0"), temperature.canonical_value)
        self.assertAlmostEqual(Decimal("32"), temperature.display_value)

    def test_unit_category_must_match_measurement_category(self) -> None:
        kilograms = self.unit("mass", "kilogram")
        with self.assertRaisesRegex(ValueError, "Invalid length"):
            set_measurement(
                self.connection, self.person_id, "height", "length", "1.8", kilograms.id
            )


if __name__ == "__main__":
    unittest.main()
