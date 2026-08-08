from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from app.db import connect, create_entity, get_mobility_profile, get_routing_policy
from app.entities import DEFINITIONS_BY_TYPE
from app.walking_journeys import (
    configure_avoid_steps_policy,
    list_journey_endpoint_options,
    review_walk_profile_measurements,
    save_reviewed_walk_profile,
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

    def measurement_values(self, profile_key="regular-walk", **changes):
        values = {
            "profile_key": profile_key,
            "distance_metres": "1000",
            "trial_1": "10:00",
            "trial_2": "10:20",
            "trial_3": "9:40",
            "measured_on": "2026-08-08",
            "course_note": "Fictional level test course",
            "maximum_distance_metres": "",
            "maximum_duration_minutes": "",
        }
        values.update(changes)
        return values

    def test_repeated_measurements_are_reviewed_before_stable_profile_save(self):
        review = review_walk_profile_measurements(self.measurement_values())
        with connect(self.database_path) as connection:
            saved = save_reviewed_walk_profile(connection, review)
            stored = get_mobility_profile(connection, "regular-walk")

        self.assertEqual("regular", saved.definition["preset_kind"])
        self.assertEqual(3, len(stored.definition["measurement_trials"]))
        self.assertAlmostEqual(1.666667, stored.definition["speed_metres_per_second"])
        self.assertEqual(600, review.pace_seconds_per_kilometre)
        self.assertEqual("repeated_user_measurement", stored.definition["source"])

    def test_profile_order_and_invalid_or_future_measurements_are_refused(self):
        with self.assertRaisesRegex(ValueError, "three|Trial 3"):
            review_walk_profile_measurements(self.measurement_values(trial_3=""))
        with self.assertRaisesRegex(ValueError, "future"):
            review_walk_profile_measurements(
                self.measurement_values(measured_on="2099-01-01")
            )

        with connect(self.database_path) as connection:
            regular = review_walk_profile_measurements(self.measurement_values())
            save_reviewed_walk_profile(connection, regular)
            slower_fast = review_walk_profile_measurements(
                self.measurement_values(
                    "fast-walk", trial_1="12:00", trial_2="12:10", trial_3="11:50"
                )
            )
            with self.assertRaisesRegex(ValueError, "must increase"):
                save_reviewed_walk_profile(connection, slower_fast)

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
