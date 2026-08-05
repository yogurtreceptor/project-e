import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.audit import list_audit_events
from app.db import (
    connect,
    create_entity,
    create_location_address,
    create_location_geometry,
    create_location_provider_reference,
    create_relationship,
    delete_location_provider_reference,
    get_entity,
    list_location_addresses,
    list_location_geometries,
    list_location_provider_references,
    location_place_context,
    update_entity,
    validate_relationship_values,
)
from app.entities import DEFINITIONS_BY_TYPE
from app.geo import build_map_payload
from tests.database_test_support import initialise_test_database


class CanonicalPlaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "places.sqlite3"
        initialise_test_database(self.database_path)
        self.locations = DEFINITIONS_BY_TYPE["location"]

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_location(self, connection, name: str, **values) -> int:
        return create_entity(
            connection,
            self.locations,
            {
                "display_name": name,
                "notes": "",
                "address_confidence": "User confirmed",
                "geometry_confidence": "User confirmed",
                **values,
            },
        )

    def test_form_projection_retains_address_and_point_history(self) -> None:
        with connect(self.database_path) as connection:
            location_id = self.create_location(
                connection,
                "Fictional Library",
                formatted_address="1 First Street, Example QLD 4000",
                address_line_1="1 First Street",
                city="Example",
                state="Queensland",
                post_code="4000",
                latitude="-27.5001",
                longitude="153.0001",
                accuracy_radius_metres="8",
            )
            before = get_entity(connection, self.locations, location_id)
            values = before.to_form_values()
            values.update(
                {
                    "formatted_address": "2 Second Street, Example QLD 4000",
                    "address_line_1": "2 Second Street",
                    "latitude": "-27.5002",
                    "longitude": "153.0002",
                    "accuracy_radius_metres": "5",
                }
            )
            update_entity(connection, self.locations, location_id, values)

            addresses = list_location_addresses(connection, location_id)
            geometries = list_location_geometries(connection, location_id)
            current = get_entity(connection, self.locations, location_id)
            payload = build_map_payload(connection)
            audit = list_audit_events(connection, "entity", location_id)
            stale_entity_provenance = connection.execute(
                """SELECT 1 FROM provenance_metadata
                   WHERE record_kind='entity' AND record_id=?
                     AND field_name IN (
                         'formatted_address', 'latitude', 'longitude'
                     )""",
                (location_id,),
            ).fetchone()

        self.assertEqual(2, len(addresses))
        self.assertEqual(1, sum(item.is_current for item in addresses))
        self.assertEqual(1, sum(item.is_preferred for item in addresses))
        self.assertEqual("2 Second Street", current.metadata["address_line_1"])
        self.assertEqual(2, len(geometries))
        self.assertEqual(1, sum(item.is_current for item in geometries))
        self.assertEqual(1, sum(item.is_preferred for item in geometries))
        marker = next(item for item in payload["markers"] if item["entityId"] == location_id)
        self.assertEqual((-27.5002, 153.0002), (marker["latitude"], marker["longitude"]))
        self.assertEqual("User confirmed", marker["geometryConfidence"])
        self.assertIsNone(stale_entity_provenance)
        self.assertTrue(
            any(
                ("location_address", addresses[0].id) in event.records
                or ("location_geometry", geometries[0].id) in event.records
                for event in audit
            )
        )

    def test_geometry_encoding_supports_line_area_and_multi_part_cases(self) -> None:
        with connect(self.database_path) as connection:
            location_id = self.create_location(connection, "Fictional Reserve")
            boundary_id = create_location_geometry(
                connection,
                location_id,
                "Polygon",
                [[
                    [153.0, -27.5],
                    [153.1, -27.5],
                    [153.1, -27.6],
                    [153.0, -27.5],
                ]],
                role="boundary",
                confidence="Approximate",
                is_current=True,
                is_preferred=True,
            )
            path_id = create_location_geometry(
                connection,
                location_id,
                "MultiLineString",
                [
                    [[153.0, -27.5], [153.01, -27.51]],
                    [[153.02, -27.52], [153.03, -27.53]],
                ],
                role="path",
                confidence="Source reported",
                source_name="Fictional source",
            )
            with self.assertRaisesRegex(ValueError, "closed"):
                create_location_geometry(
                    connection,
                    location_id,
                    "Polygon",
                    [[[153.0, -27.5], [153.1, -27.5], [153.1, -27.6], [153.0, -27.6]]],
                    role="boundary",
                    confidence="Unknown",
                )
            geometries = list_location_geometries(connection, location_id)

        self.assertEqual({boundary_id, path_id}, {item.id for item in geometries})
        self.assertEqual(
            {"Polygon", "MultiLineString"},
            {item.geometry_type for item in geometries},
        )

    def test_preferred_assertions_are_current_and_unique_per_purpose_or_role(self) -> None:
        with connect(self.database_path) as connection:
            location_id = self.create_location(connection, "Invariant Place")
            create_location_address(
                connection,
                location_id,
                formatted_address="1 Example Street",
                is_preferred=True,
            )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "UNIQUE"):
                create_location_address(
                    connection,
                    location_id,
                    formatted_address="2 Example Street",
                    is_preferred=True,
                )
            with self.assertRaisesRegex(ValueError, "must be current"):
                create_location_geometry(
                    connection,
                    location_id,
                    "Point",
                    [153.0, -27.5],
                    role="entrance",
                    is_current=False,
                    is_preferred=True,
                )
            with self.assertRaisesRegex(ValueError, "must use Point"):
                create_location_geometry(
                    connection,
                    location_id,
                    "Polygon",
                    [[
                        [153.0, -27.5], [153.1, -27.5],
                        [153.1, -27.6], [153.0, -27.5],
                    ]],
                    role="representative_point",
                )

    def test_provider_reference_removal_cannot_change_canonical_geometry(self) -> None:
        with connect(self.database_path) as connection:
            location_id = self.create_location(connection, "Fictional Station")
            geometry_id = create_location_geometry(
                connection,
                location_id,
                "Point",
                [153.4, -27.9],
                role="representative_point",
                confidence="Source reported",
                source_name="Fictional provider",
                source_reference="station-7",
                source_version="v1",
                is_preferred=True,
            )
            first = create_location_provider_reference(
                connection,
                location_id,
                "fictional-provider",
                "station-7",
                feature_version="v1",
            )
            second = create_location_provider_reference(
                connection,
                location_id,
                "fictional-provider",
                "station-7",
                feature_version="v2",
            )
            delete_location_provider_reference(connection, first)
            delete_location_provider_reference(connection, second)
            geometry = next(
                item
                for item in list_location_geometries(connection, location_id)
                if item.id == geometry_id
            )
            references = list_location_provider_references(connection, location_id)

        self.assertEqual([], references)
        self.assertEqual([153.4, -27.9], geometry.coordinates)
        self.assertTrue(geometry.is_current)
        self.assertTrue(geometry.is_preferred)

    def test_containment_is_single_parent_cycle_safe_and_inherits_only_for_display(self) -> None:
        with connect(self.database_path) as connection:
            station_id = self.create_location(
                connection,
                "Fictional Station",
                formatted_address="10 Railway Parade, Example",
                address_line_1="10 Railway Parade",
            )
            entrance_id = self.create_location(
                connection,
                "South entrance",
                latitude="-27.91",
                longitude="153.41",
            )
            precinct_id = self.create_location(connection, "Fictional Precinct")
            relationship_id = create_relationship(
                connection,
                {
                    "source_entity_id": str(station_id),
                    "target_entity_id": str(entrance_id),
                    "type": "contains_location",
                    "status": "active",
                },
            )
            second_parent = {
                "source_entity_id": str(precinct_id),
                "target_entity_id": str(entrance_id),
                "type": "contains_location",
                "status": "active",
            }
            cycle = {
                "source_entity_id": str(entrance_id),
                "target_entity_id": str(station_id),
                "type": "contains_location",
                "status": "active",
            }
            self.assertIn(
                "A Location can have only one active parent Location.",
                validate_relationship_values(connection, second_parent),
            )
            self.assertIn(
                "This containment would create a Location cycle.",
                validate_relationship_values(connection, cycle),
            )
            with self.assertRaisesRegex(sqlite3.IntegrityError, "cycle"):
                create_relationship(connection, cycle)
            context = location_place_context(connection, entrance_id)
            child_addresses = list_location_addresses(connection, entrance_id)
            payload = build_map_payload(connection)

        self.assertGreater(relationship_id, 0)
        self.assertEqual([], child_addresses)
        self.assertEqual(station_id, context.inherited_address_location_id)
        self.assertEqual("10 Railway Parade, Example", context.display_address.display_text)
        marker = next(item for item in payload["markers"] if item["entityId"] == entrance_id)
        self.assertEqual("10 Railway Parade, Example", marker["address"])
        self.assertEqual(station_id, marker["addressInheritedFrom"])


if __name__ == "__main__":
    unittest.main()
