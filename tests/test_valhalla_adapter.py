from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest

from app.db import connect, create_entity, create_mobility_profile, create_routing_policy
from app.entities import DEFINITIONS_BY_TYPE
from app.journey_cache import JourneyCache
from app.journey_contract import (
    EndpointReference,
    FailureCode,
    JourneyBuffer,
    JourneyMode,
    JourneyRequest,
    JourneySource,
    JourneyTime,
    JourneyTimeKind,
    PolicyKind,
)
from app.journey_service import plan_journey
from app.routing_resources import LocalValhallaCapability
from app.valhalla_adapter import ValhallaWalkingAdapter
from tests.database_test_support import initialise_test_database


NOW = datetime(2026, 8, 8, 3, 0, tzinfo=UTC)


def encode_polyline6(points):
    result = []
    previous = [0, 0]
    for longitude, latitude in points:
        values = [round(latitude * 1_000_000), round(longitude * 1_000_000)]
        for index, value in enumerate(values):
            delta = value - previous[index]
            previous[index] = value
            encoded = ~(delta << 1) if delta < 0 else delta << 1
            while encoded >= 0x20:
                result.append(chr((0x20 | (encoded & 0x1F)) + 63))
                encoded >>= 5
            result.append(chr(encoded + 63))
    return "".join(result)


class FakeValhallaTransport:
    def __init__(self, *, route_status=200, route_body=None, snap_offset=0.0, steps=False):
        self.route_status = route_status
        self.route_body = route_body
        self.snap_offset = snap_offset
        self.steps = steps
        self.calls = []

    def __call__(self, path, payload):
        self.calls.append((path, payload))
        if path == "/status":
            return 200, {
                "version": "3.8.3",
                "available_actions": ["status", "locate", "route"],
            }
        if path == "/locate":
            return 200, [
                {
                    "input_lon": point["lon"],
                    "input_lat": point["lat"],
                    "edges": [
                        {
                            "correlated_lon": point["lon"] + self.snap_offset,
                            "correlated_lat": point["lat"],
                        }
                    ],
                }
                for point in payload["locations"]
            ]
        if path == "/route":
            if self.route_body is not None:
                return self.route_status, self.route_body
            locations = payload["locations"]
            points = [
                (locations[0]["lon"], locations[0]["lat"]),
                (153.405, -27.902),
                (locations[1]["lon"], locations[1]["lat"]),
            ]
            maneuvers = [
                {
                    "type": 40 if self.steps else 1,
                    "instruction": "Take the fictional stairs." if self.steps else "Walk east on Fictional Way.",
                    "time": 1120.0,
                    "length": 1.4,
                },
                {"type": 4, "instruction": "You have arrived.", "time": 0.0, "length": 0.0},
            ]
            trip = {
                "summary": {"length": 1.4, "time": 1120.0},
                "legs": [
                    {
                        "summary": {"length": 1.4, "time": 1120.0},
                        "shape": encode_polyline6(points),
                        "maneuvers": maneuvers,
                    }
                ],
            }
            body = {"trip": trip}
            if payload.get("alternates"):
                body["alternates"] = [{"trip": trip}]
            return 200, body
        raise AssertionError(path)


class ValhallaWalkingAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "journeys.sqlite3"
        initialise_test_database(self.database_path)
        with connect(self.database_path) as connection:
            self.origin_id = self.create_location(
                connection, "Fictional Origin", 153.4000, -27.9000
            )
            self.destination_id = self.create_location(
                connection, "Fictional Destination", 153.4100, -27.9050
            )
            create_mobility_profile(
                connection,
                "regular-walk",
                "Regular walk",
                JourneyMode.WALK,
                {
                    "preset_kind": "regular",
                    "speed_metres_per_second": 1.388889,
                    "source": "provisional_generic_reference",
                    "provisional": True,
                },
            )
            create_routing_policy(
                connection,
                "avoid-steps",
                "Prefer routes without steps",
                PolicyKind.SOFT_AVOIDANCE,
                {"modes": ["walk"], "attribute": "steps", "strength": "strong"},
            )
            self.origin_geometry_id = self.geometry_id(connection, self.origin_id)
            self.destination_geometry_id = self.geometry_id(connection, self.destination_id)
        self.cache = JourneyCache(self.root / "cache.sqlite3", maximum_entries=8)

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def create_location(connection, name, longitude, latitude):
        return create_entity(
            connection,
            DEFINITIONS_BY_TYPE["location"],
            {
                "display_name": name,
                "longitude": str(longitude),
                "latitude": str(latitude),
                "geometry_confidence": "User confirmed",
                "address_confidence": "User confirmed",
            },
        )

    @staticmethod
    def geometry_id(connection, location_id):
        return int(
            connection.execute(
                "SELECT id FROM location_geometries WHERE location_entity_id=?",
                (location_id,),
            ).fetchone()[0]
        )

    def capability(self, *, source_version="osm-v1"):
        return LocalValhallaCapability(
            base_url="http://127.0.0.1:18081",
            provider_version="3.8.3",
            service_binary=self.root / "valhalla_service",
            service_config=self.root / "valhalla.json",
            service_binary_sha256="a" * 64,
            service_config_sha256="b" * 64,
            graph_path=self.root / "tiles.tar",
            graph_sha256="c" * 64,
            graph_bytes=1,
            coverage_key="fictional-gold-coast-streets",
            coverage_bbox=(153.0, -28.4, 153.7, -27.5),
            coverage_timezone="Australia/Brisbane",
            maximum_snap_distance_metres=100,
            compatible_spatial_pack_id="fictional-coast",
            compatible_spatial_pack_version="1",
            maximum_cache_entries=8,
            cache_fresh_seconds=3600,
            sources=(
                JourneySource("osm-streets", source_version, "Fictional OSM snapshot"),
                JourneySource("valhalla-graph", "graph-v1", "Immutable local graph"),
            ),
        )

    def request(self, **changes):
        request = JourneyRequest(
            origin=EndpointReference(self.origin_id, self.origin_geometry_id),
            destination=EndpointReference(
                self.destination_id, self.destination_geometry_id
            ),
            mode=JourneyMode.WALK,
            access_modes=(),
            time=JourneyTime(
                JourneyTimeKind.ARRIVE_BY, "2026-08-08T09:00:00+10:00"
            ),
            profile_keys=("regular-walk",),
            policy_keys=("avoid-steps",),
            buffers=(
                JourneyBuffer("preparation", "Preparation", 300),
                JourneyBuffer("arrival", "Arrival", 180),
            ),
            requested_alternatives=1,
            require_geometry=True,
            require_complete_coverage=False,
            required_features=(),
        )
        return replace(request, **changes)

    def plan(self, transport, *, capability=None, request=None):
        adapter = ValhallaWalkingAdapter(
            capability or self.capability(), transport=transport, clock=lambda: NOW
        )
        with connect(self.database_path) as connection:
            return plan_journey(
                connection,
                request or self.request(),
                adapter,
                cache=self.cache,
                now=NOW,
            )

    def test_local_route_translates_profile_policy_snaps_geometry_time_and_buffers(self):
        transport = FakeValhallaTransport()
        execution = self.plan(transport)

        self.assertIsNone(execution.failure)
        result = execution.result
        alternative = result.alternatives[0]
        self.assertEqual(1400.0, alternative.route_distance_metres)
        self.assertGreater(alternative.route_distance_metres, alternative.straight_line_distance_metres)
        self.assertEqual(1120, alternative.estimated_duration_seconds)
        self.assertIsNone(alternative.scheduled_duration_seconds)
        self.assertEqual(1600, alternative.elapsed_duration_seconds)
        self.assertEqual("2026-08-08T08:33:20+10:00", alternative.milestones[0][2])
        self.assertEqual("2026-08-08T09:00:00+10:00", alternative.milestones[-1][2])
        self.assertAlmostEqual(153.4, result.origin.snapped_longitude)
        self.assertGreaterEqual(len(alternative.stages[0].geometry), 3)
        self.assertEqual(("regular-walk",), result.applied_profile_keys)
        self.assertEqual(("avoid-steps",), result.applied_policy_keys)
        route_payload = next(payload for path, payload in transport.calls if path == "/route")
        self.assertEqual(5.0, route_payload["costing_options"]["pedestrian"]["walking_speed"])
        self.assertEqual(43200, route_payload["costing_options"]["pedestrian"]["step_penalty"])
        self.assertNotIn("date_time", route_payload)
        self.assertIn("Static local street estimate only", result.textual_itinerary)

    def test_soft_step_avoidance_is_explicitly_unsatisfied_when_steps_remain(self):
        execution = self.plan(FakeValhallaTransport(steps=True))

        self.assertIsNone(execution.failure)
        self.assertEqual((), execution.result.applied_policy_keys)
        self.assertEqual(("avoid-steps",), execution.result.unsatisfied_policy_keys)
        self.assertIn("still uses steps", execution.result.alternatives[0].warnings[0])

    def test_distant_provider_snap_is_absent_coverage_not_a_route(self):
        transport = FakeValhallaTransport(snap_offset=0.01)
        execution = self.plan(transport)

        self.assertEqual(FailureCode.ABSENT_COVERAGE, execution.failure.code)
        self.assertNotIn("/route", [path for path, _payload in transport.calls])

    def test_covered_no_path_is_distinct_from_provider_failure(self):
        no_route = self.plan(
            FakeValhallaTransport(
                route_status=400,
                route_body={"error_code": 442, "error": "No path could be found"},
            )
        )
        provider_failure = self.plan(
            FakeValhallaTransport(
                route_status=500,
                route_body={"error_code": 500, "error": "worker failed"},
            )
        )

        self.assertEqual(FailureCode.NO_ROUTE, no_route.failure.code)
        self.assertEqual(FailureCode.PROVIDER_FAILURE, provider_failure.failure.code)

    def test_source_version_changes_fingerprint_and_deterministically_misses_cache(self):
        first_transport = FakeValhallaTransport()
        first = self.plan(first_transport)
        fresh_transport = FakeValhallaTransport()
        fresh = self.plan(fresh_transport)
        changed_transport = FakeValhallaTransport()
        changed = self.plan(
            changed_transport, capability=self.capability(source_version="osm-v2")
        )

        self.assertIsNotNone(first.result)
        self.assertEqual("fresh", fresh.cache_status.value)
        self.assertNotIn("/route", [path for path, _payload in fresh_transport.calls])
        self.assertEqual("miss", changed.cache_status.value)
        self.assertNotEqual(first.result.fingerprint, changed.result.fingerprint)
        self.assertIn("/route", [path for path, _payload in changed_transport.calls])

    def test_endpoint_outside_declared_bbox_is_refused_before_provider_call(self):
        transport = FakeValhallaTransport()
        narrow = replace(self.capability(), coverage_bbox=(153.0, -28.0, 153.2, -27.5))
        execution = self.plan(transport, capability=narrow)

        self.assertEqual(FailureCode.ABSENT_COVERAGE, execution.failure.code)
        self.assertEqual([], transport.calls)

    def test_route_geometry_outside_declared_extent_is_labelled_partial(self):
        locations = [(153.4, -27.9), (153.41, -27.905)]
        trip = {
            "summary": {"length": 1.5, "time": 1200.0},
            "legs": [
                {
                    "shape": encode_polyline6(
                        [locations[0], (153.405, -27.80), locations[1]]
                    ),
                    "maneuvers": [
                        {"type": 1, "instruction": "Walk north."},
                        {"type": 4, "instruction": "You have arrived."},
                    ],
                }
            ],
        }
        capability = replace(
            self.capability(), coverage_bbox=(153.39, -27.92, 153.42, -27.88)
        )
        execution = self.plan(
            FakeValhallaTransport(route_body={"trip": trip}), capability=capability
        )

        self.assertIsNone(execution.failure)
        self.assertEqual("partial", execution.result.coverage.state.value)
        self.assertIn("outside the declared", execution.result.warnings[-1])

    def test_faster_profile_is_refused_while_jogging_is_disabled(self):
        with connect(self.database_path) as connection:
            create_mobility_profile(
                connection,
                "fast-walk",
                "Fast walk / jog",
                JourneyMode.WALK,
                {
                    "preset_kind": "fast",
                    "speed_metres_per_second": 2.5,
                    "source": "repeated_user_measurement",
                    "measurement_effective_date": "2026-08-08",
                    "measurement_trials": [
                        {"distance_metres": 1000, "duration_seconds": 400},
                        {"distance_metres": 1000, "duration_seconds": 395},
                        {"distance_metres": 1000, "duration_seconds": 405},
                    ],
                },
            )
        transport = FakeValhallaTransport()
        execution = self.plan(
            transport, request=replace(self.request(), profile_keys=("fast-walk",))
        )

        self.assertEqual(FailureCode.UNSUPPORTED_PROFILE, execution.failure.code)
        self.assertNotIn("/route", [path for path, _payload in transport.calls])


if __name__ == "__main__":
    unittest.main()
