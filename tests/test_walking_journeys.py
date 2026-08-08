from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from app.db import connect, create_entity, get_mobility_profile, get_routing_policy
from app.entities import DEFINITIONS_BY_TYPE
from app.walking_journeys import (
    configure_avoid_steps_policy,
    ensure_default_walk_profile,
    list_journey_endpoint_options,
    walking_request_from_form,
)
from tests.database_test_support import initialise_test_database


class WalkingJourneyConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "walking.sqlite3"
        initialise_test_database(self.database_path)

    def tearDown(self):
        self.temporary.cleanup()

    def test_provisional_regular_walk_profile_is_created_once_at_five_kmh(self):
        with connect(self.database_path) as connection:
            created = ensure_default_walk_profile(connection)
            repeated = ensure_default_walk_profile(connection)
            stored = get_mobility_profile(connection, "regular-walk")
            audit = connection.execute(
                """SELECT actor, provenance FROM audit_events
                   WHERE notes='Provisional generic Regular walk profile initialised'"""
            ).fetchone()

        self.assertEqual(created.id, repeated.id)
        self.assertEqual("regular", stored.definition["preset_kind"])
        self.assertAlmostEqual(1.388889, stored.definition["speed_metres_per_second"])
        self.assertEqual(5.0, stored.definition["source_speed_kilometres_per_hour"])
        self.assertEqual("provisional_generic_reference", stored.definition["source"])
        self.assertTrue(stored.definition["provisional"])
        self.assertEqual(("system", "source_reported"), tuple(audit))

    def test_jog_and_run_form_profiles_are_refused(self):
        base = {
            "origin": "1:1",
            "destination": "2:2",
            "time_kind": "depart_at",
            "journey_time": "2026-08-10T09:00",
            "preparation_minutes": "0",
            "arrival_minutes": "0",
            "alternatives": "1",
        }
        for profile_key in ("fast-walk", "run"):
            with self.subTest(profile_key=profile_key):
                with self.assertRaisesRegex(ValueError, "not enabled"):
                    walking_request_from_form(
                        {**base, "profile_key": profile_key}
                    )

    def test_supported_avoid_steps_policy_is_user_enabled_and_revisioned(self):
        with connect(self.database_path) as connection:
            created = configure_avoid_steps_policy(connection, enabled=True)
            disabled = configure_avoid_steps_policy(connection, enabled=False)
            stored = get_routing_policy(connection, "avoid-steps")

        self.assertEqual("soft_avoidance", created.kind.value)
        self.assertEqual("steps", created.definition["attribute"])
        self.assertFalse(disabled.is_enabled)
        self.assertEqual(2, stored.revision)

    def test_route_form_uses_explicit_geometry_local_timezone_and_named_buffers(self):
        with connect(self.database_path) as connection:
            origin = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["location"],
                {
                    "display_name": "Fictional Origin",
                    "longitude": "153.40",
                    "latitude": "-27.90",
                    "geometry_confidence": "User confirmed",
                    "address_confidence": "User confirmed",
                },
            )
            destination = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["location"],
                {
                    "display_name": "Fictional Destination",
                    "longitude": "153.41",
                    "latitude": "-27.91",
                    "geometry_confidence": "User confirmed",
                    "address_confidence": "User confirmed",
                },
            )
            options = list_journey_endpoint_options(connection)
        by_location = {item.location_id: item for item in options}
        request = walking_request_from_form(
            {
                "origin": by_location[origin].value,
                "destination": by_location[destination].value,
                "time_kind": "arrive_by",
                "journey_time": "2026-08-10T09:00",
                "profile_key": "regular-walk",
                "policy_keys": "avoid-steps",
                "preparation_minutes": "5",
                "arrival_minutes": "3",
                "alternatives": "2",
            }
        )

        self.assertEqual(by_location[origin].geometry_id, request.origin.geometry_id)
        self.assertEqual("arrive_by", request.time.kind.value)
        parsed = datetime.fromisoformat(request.time.value)
        self.assertEqual(timedelta(hours=10), parsed.utcoffset())
        self.assertEqual([300, 180], [item.seconds for item in request.buffers])
        self.assertEqual(2, request.requested_alternatives)


if __name__ == "__main__":
    unittest.main()
