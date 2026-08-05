from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.db import (
    connect,
    create_entity,
    create_location_geometry,
    create_mobility_profile,
    create_routing_policy,
)
from app.entities import DEFINITIONS_BY_TYPE
from app.journey_cache import JourneyCache
from app.journey_contract import (
    AdapterOutcome,
    CoverageReport,
    CoverageState,
    EndpointReference,
    FailureCode,
    JourneyAlternative,
    JourneyBuffer,
    JourneyCapabilities,
    JourneyFailure,
    JourneyMode,
    JourneyProvenance,
    JourneyRequest,
    JourneyResult,
    JourneySource,
    JourneyStage,
    JourneyStageMode,
    JourneyTime,
    JourneyTimeKind,
    MobilityProfile,
    PolicyKind,
    ResolvedEndpoint,
    RoutingPolicy,
    TransitInput,
    journey_fingerprint,
)
from app.journey_service import plan_journey
from tests.database_test_support import initialise_test_database


NOW = datetime(2026, 8, 5, 8, 0, tzinfo=UTC)


class FictionalJourneyAdapter:
    """Deterministic evidence adapter; it never performs I/O or pathfinding."""

    def __init__(
        self,
        *,
        behaviour: str = "success",
        supported_requirements: tuple[str, ...] = (),
        supported_policy_kinds: tuple[PolicyKind, ...] = (
            PolicyKind.HARD_EXCLUSION,
            PolicyKind.SOFT_AVOIDANCE,
        ),
        route_distance_metres: float = 900.0,
        adapter_version: str = "fixture-1",
        street_version: str = "fictional-streets-7",
    ) -> None:
        self.behaviour = behaviour
        self.route_distance_metres = route_distance_metres
        self.calls = 0
        self._capabilities = JourneyCapabilities(
            adapter_key="fictional-router",
            adapter_version=adapter_version,
            execution="local",
            modes=(JourneyMode.WALK, JourneyMode.PUBLIC_TRANSPORT),
            stage_modes=(
                JourneyStageMode.WALK,
                JourneyStageMode.WAIT,
                JourneyStageMode.BUS,
            ),
            time_semantics=(JourneyTimeKind.DEPART_AT, JourneyTimeKind.ARRIVE_BY),
            transit_inputs=(TransitInput.STATIC_TIMETABLE,),
            supports_geometry=True,
            supported_requirements=supported_requirements,
            supported_policy_kinds=supported_policy_kinds,
            maximum_alternatives=3,
            coverage_keys=("fictional-coast",),
            sources=(
                JourneySource("fictional-streets", street_version, "2026-08-01"),
            ),
        )

    def capabilities(self) -> JourneyCapabilities:
        return self._capabilities

    def plan(self, prepared) -> AdapterOutcome:
        self.calls += 1
        if self.behaviour == "no_route":
            return AdapterOutcome(
                failure=JourneyFailure(
                    FailureCode.NO_ROUTE,
                    "The fictional network contains no physical connection.",
                )
            )
        if self.behaviour == "provider_failure":
            return AdapterOutcome(
                failure=JourneyFailure(
                    FailureCode.PROVIDER_FAILURE,
                    "The fictional provider process stopped unexpectedly.",
                )
            )

        duration = int(self.route_distance_metres / 1.25)
        starts_at = NOW
        ends_at = NOW + timedelta(seconds=duration)
        coverage = CoverageReport(
            CoverageState.PARTIAL if self.behaviour == "partial" else CoverageState.COMPLETE,
            "The final 120 metres lack fictional street coverage."
            if self.behaviour == "partial"
            else "Fictional Coast street coverage is complete for this route.",
            coverage_keys=("fictional-coast",),
            missing_capabilities=("street_routing",)
            if self.behaviour == "partial"
            else (),
        )
        conflicts = (
            tuple(policy.policy_key for policy in prepared.policies)
            if self.behaviour == "policy_conflict"
            else ()
        )
        unsatisfied = (
            tuple(policy.policy_key for policy in prepared.policies)
            if self.behaviour == "policy_unsatisfied"
            else ()
        )
        result = JourneyResult(
            fingerprint=prepared.fingerprint,
            origin=replace(
                prepared.origin,
                snapped_longitude=prepared.origin.longitude + 0.00001,
                snapped_latitude=prepared.origin.latitude,
                snap_distance_metres=1.1,
            ),
            destination=replace(
                prepared.destination,
                snapped_longitude=prepared.destination.longitude,
                snapped_latitude=prepared.destination.latitude - 0.00001,
                snap_distance_metres=1.2,
            ),
            alternatives=(
                JourneyAlternative(
                    alternative_key="fixture-walk-1",
                    stages=(
                        JourneyStage(
                            mode=JourneyStageMode.WALK,
                            instruction="Walk through the fictional reserve.",
                            starts_at=starts_at.isoformat(),
                            ends_at=ends_at.isoformat(),
                            duration_seconds=duration,
                            duration_kind="estimated",
                            route_distance_metres=self.route_distance_metres,
                            geometry=(
                                (prepared.origin.longitude, prepared.origin.latitude),
                                (
                                    prepared.destination.longitude,
                                    prepared.destination.latitude,
                                ),
                            ),
                        ),
                    ),
                    straight_line_distance_metres=760.0,
                    route_distance_metres=self.route_distance_metres,
                    scheduled_duration_seconds=None,
                    estimated_duration_seconds=duration,
                    elapsed_duration_seconds=duration,
                    milestones=(
                        ("leave", "Leave origin", starts_at.isoformat()),
                        ("arrive", "Arrive at destination", ends_at.isoformat()),
                    ),
                ),
            ),
            coverage=coverage,
            applied_profile_keys=(
                ()
                if self.behaviour == "omit_profile"
                else tuple(profile.profile_key for profile in prepared.profiles)
            ),
            applied_policy_keys=(
                ()
                if self.behaviour in {
                    "omit_policy",
                    "policy_conflict",
                    "policy_unsatisfied",
                }
                else tuple(policy.policy_key for policy in prepared.policies)
            ),
            conflicting_policy_keys=conflicts,
            unsatisfied_policy_keys=unsatisfied,
            buffers=prepared.request.buffers,
            provenance=JourneyProvenance(
                adapter_key=self._capabilities.adapter_key,
                adapter_version=self._capabilities.adapter_version,
                execution=self._capabilities.execution,
                sources=self._capabilities.sources,
                calculated_at=NOW.isoformat(),
                fresh_until=(NOW + timedelta(minutes=10)).isoformat(),
            ),
            textual_itinerary=(
                "Walk 900 m through the fictional reserve. "
                "Estimated travel 12 minutes; total elapsed 12 minutes."
            ),
            warnings=(coverage.explanation,) if coverage.state == CoverageState.PARTIAL else (),
        )
        return AdapterOutcome(result=result)


class JourneyContractEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "journeys.sqlite3"
        initialise_test_database(self.database_path)
        with connect(self.database_path) as connection:
            self.origin_id = self._create_location(
                connection, "Fictional Origin", 153.4000, -27.9000
            )
            self.destination_id = self._create_location(
                connection, "Fictional Destination", 153.4100, -27.9050
            )
            create_mobility_profile(
                connection,
                "regular-walk-fixture",
                "Regular walk fixture",
                JourneyMode.WALK,
                {
                    "speed_metres_per_second": 1.25,
                    "maximum_contiguous_distance_metres": 1500,
                    "source": "repeated fictional measurement",
                    "effective_date": "2026-08-05",
                },
            )
            create_routing_policy(
                connection,
                "avoid-stairs-fixture",
                "Avoid fictional stairs",
                PolicyKind.SOFT_AVOIDANCE,
                {"modes": ["walk"], "attribute": "stairs"},
            )
        self.cache = JourneyCache(self.root / "journey-cache.sqlite3", maximum_entries=4)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _create_location(connection, name: str, longitude: float, latitude: float) -> int:
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

    def request(self, **changes) -> JourneyRequest:
        request = JourneyRequest(
            origin=EndpointReference(self.origin_id),
            destination=EndpointReference(self.destination_id),
            mode=JourneyMode.WALK,
            access_modes=(),
            time=JourneyTime(JourneyTimeKind.DEPART_AT, NOW.isoformat()),
            profile_keys=("regular-walk-fixture",),
            policy_keys=("avoid-stairs-fixture",),
            buffers=(JourneyBuffer("preparation", "Preparation", 300),),
            requested_alternatives=1,
            require_geometry=True,
            require_complete_coverage=False,
            required_features=(),
        )
        return replace(request, **changes)

    def plan(self, request: JourneyRequest, adapter: FictionalJourneyAdapter):
        with connect(self.database_path) as connection:
            return plan_journey(
                connection,
                request,
                adapter,
                cache=self.cache,
                now=NOW,
            )

    def test_success_is_provider_independent_and_does_not_create_events(self) -> None:
        adapter = FictionalJourneyAdapter()
        with connect(self.database_path) as connection:
            before_events = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            execution = plan_journey(
                connection,
                self.request(),
                adapter,
                cache=self.cache,
                now=NOW,
            )
            after_events = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        self.assertIsNone(execution.failure)
        self.assertEqual("miss", execution.cache_status.value)
        self.assertEqual(before_events, after_events)
        result = execution.result
        self.assertEqual(CoverageState.COMPLETE, result.coverage.state)
        self.assertEqual(JourneyStageMode.WALK, result.alternatives[0].stages[0].mode)
        self.assertEqual(760.0, result.alternatives[0].straight_line_distance_metres)
        self.assertEqual(900.0, result.alternatives[0].route_distance_metres)
        self.assertIsNone(result.alternatives[0].scheduled_duration_seconds)
        self.assertEqual(
            result.alternatives[0].estimated_duration_seconds,
            result.alternatives[0].elapsed_duration_seconds,
        )
        self.assertIn("total elapsed", result.textual_itinerary)
        self.assertEqual("fictional-router", result.provenance.adapter_key)

    def test_ambiguous_access_points_require_an_explicit_geometry(self) -> None:
        with connect(self.database_path) as connection:
            first = create_location_geometry(
                connection,
                self.origin_id,
                "Point",
                [153.4001, -27.9001],
                role="entrance",
                confidence="User confirmed",
            )
            create_location_geometry(
                connection,
                self.origin_id,
                "Point",
                [153.4002, -27.9002],
                role="entrance",
                confidence="User confirmed",
            )
        adapter = FictionalJourneyAdapter()

        ambiguous = self.plan(self.request(), adapter)
        explicit = self.plan(
            self.request(origin=EndpointReference(self.origin_id, first)), adapter
        )

        self.assertEqual(FailureCode.AMBIGUOUS_ENDPOINT, ambiguous.failure.code)
        self.assertEqual(0, ambiguous.adapter_calls)
        self.assertIsNone(explicit.failure)
        self.assertEqual(first, explicit.result.origin.geometry_id)

    def test_unsupported_requirements_and_policy_kinds_are_refused_preflight(self) -> None:
        requirement_adapter = FictionalJourneyAdapter()
        unsupported_requirement = self.plan(
            self.request(required_features=("step_free",)), requirement_adapter
        )
        policy_adapter = FictionalJourneyAdapter(supported_policy_kinds=())
        unsupported_policy = self.plan(self.request(), policy_adapter)

        self.assertEqual(
            FailureCode.UNSUPPORTED_REQUIREMENT, unsupported_requirement.failure.code
        )
        self.assertEqual(0, requirement_adapter.calls)
        self.assertEqual(FailureCode.UNSUPPORTED_POLICY, unsupported_policy.failure.code)
        self.assertEqual(0, policy_adapter.calls)

    def test_partial_coverage_is_labelled_or_refused_when_complete_is_required(self) -> None:
        partial = self.plan(self.request(), FictionalJourneyAdapter(behaviour="partial"))
        strict = self.plan(
            self.request(require_complete_coverage=True),
            FictionalJourneyAdapter(behaviour="partial"),
        )

        self.assertIsNone(partial.failure)
        self.assertEqual(CoverageState.PARTIAL, partial.result.coverage.state)
        self.assertIn("street_routing", partial.result.coverage.missing_capabilities)
        self.assertEqual(FailureCode.PARTIAL_COVERAGE, strict.failure.code)

    def test_no_route_is_distinct_from_provider_failure(self) -> None:
        no_route = self.plan(
            self.request(), FictionalJourneyAdapter(behaviour="no_route")
        )
        failure = self.plan(
            self.request(), FictionalJourneyAdapter(behaviour="provider_failure")
        )

        self.assertEqual(FailureCode.NO_ROUTE, no_route.failure.code)
        self.assertEqual(FailureCode.PROVIDER_FAILURE, failure.failure.code)

    def test_profile_contiguous_limit_is_checked_without_selecting_another_profile(self) -> None:
        with connect(self.database_path) as connection:
            create_mobility_profile(
                connection,
                "short-walk-fixture",
                "Short walk fixture",
                JourneyMode.WALK,
                {"maximum_contiguous_distance_metres": 500},
            )
        execution = self.plan(
            self.request(profile_keys=("short-walk-fixture",)),
            FictionalJourneyAdapter(route_distance_metres=900),
        )

        self.assertEqual(FailureCode.PROFILE_LIMIT_EXCEEDED, execution.failure.code)
        self.assertIn("short-walk-fixture", execution.failure.related_keys)

    def test_policy_conflicts_are_surfaced_and_never_silently_resolved(self) -> None:
        execution = self.plan(
            self.request(), FictionalJourneyAdapter(behaviour="policy_conflict")
        )

        self.assertEqual(FailureCode.POLICY_CONFLICT, execution.failure.code)
        self.assertEqual(
            ("avoid-stairs-fixture",), execution.failure.related_keys
        )

    def test_adapter_cannot_silently_omit_a_requested_profile_or_policy(self) -> None:
        omitted_profile = self.plan(
            self.request(), FictionalJourneyAdapter(behaviour="omit_profile")
        )
        omitted_policy = self.plan(
            self.request(), FictionalJourneyAdapter(behaviour="omit_policy")
        )

        self.assertEqual(FailureCode.INVALID_RESULT, omitted_profile.failure.code)
        self.assertEqual(FailureCode.INVALID_RESULT, omitted_policy.failure.code)

    def test_fresh_cache_avoids_adapter_while_stale_cache_is_only_a_candidate(self) -> None:
        first_adapter = FictionalJourneyAdapter()
        first = self.plan(self.request(), first_adapter)
        fresh_adapter = FictionalJourneyAdapter(behaviour="provider_failure")
        fresh = self.plan(self.request(), fresh_adapter)
        stale_adapter = FictionalJourneyAdapter()
        with connect(self.database_path) as connection:
            stale = plan_journey(
                connection,
                self.request(),
                stale_adapter,
                cache=self.cache,
                now=NOW + timedelta(minutes=11),
            )

        self.assertIsNotNone(first.result)
        self.assertEqual("fresh", fresh.cache_status.value)
        self.assertEqual(0, fresh_adapter.calls)
        self.assertEqual("stale", stale.cache_status.value)
        self.assertIsNotNone(stale.cached_result)
        self.assertEqual(1, stale_adapter.calls)

    def test_stale_cache_never_turns_provider_failure_into_no_route_or_success(self) -> None:
        self.plan(self.request(), FictionalJourneyAdapter())
        with connect(self.database_path) as connection:
            execution = plan_journey(
                connection,
                self.request(),
                FictionalJourneyAdapter(behaviour="provider_failure"),
                cache=self.cache,
                now=NOW + timedelta(minutes=11),
            )

        self.assertEqual("stale", execution.cache_status.value)
        self.assertEqual(FailureCode.PROVIDER_FAILURE, execution.failure.code)
        self.assertIsNone(execution.result)
        self.assertIsNotNone(execution.cached_result)

    def test_adapter_result_that_is_already_stale_has_a_typed_failure(self) -> None:
        with connect(self.database_path) as connection:
            execution = plan_journey(
                connection,
                self.request(),
                FictionalJourneyAdapter(),
                cache=JourneyCache(
                    self.root / "empty-stale-evidence.sqlite3", maximum_entries=2
                ),
                now=NOW + timedelta(minutes=11),
            )

        self.assertEqual(FailureCode.STALE_DATA, execution.failure.code)
        self.assertIsNone(execution.result)

    def test_unsatisfied_hard_policy_has_a_distinct_no_compliant_route_outcome(self) -> None:
        with connect(self.database_path) as connection:
            create_routing_policy(
                connection,
                "exclude-ferry-fixture",
                "Exclude fictional ferry",
                PolicyKind.HARD_EXCLUSION,
                {"modes": ["walk"], "attribute": "ferry"},
            )
        execution = self.plan(
            self.request(policy_keys=("exclude-ferry-fixture",)),
            FictionalJourneyAdapter(behaviour="policy_unsatisfied"),
        )

        self.assertEqual(
            FailureCode.NO_POLICY_COMPLIANT_ROUTE, execution.failure.code
        )

    def test_explicit_endpoint_rejects_foreign_or_historical_geometry(self) -> None:
        with connect(self.database_path) as connection:
            foreign = create_location_geometry(
                connection,
                self.destination_id,
                "Point",
                [153.4101, -27.9051],
                role="entrance",
                confidence="User confirmed",
            )
            historical = create_location_geometry(
                connection,
                self.origin_id,
                "Point",
                [153.4001, -27.9001],
                role="route_anchor",
                confidence="User confirmed",
                is_current=False,
            )

        foreign_result = self.plan(
            self.request(origin=EndpointReference(self.origin_id, foreign)),
            FictionalJourneyAdapter(),
        )
        historical_result = self.plan(
            self.request(origin=EndpointReference(self.origin_id, historical)),
            FictionalJourneyAdapter(),
        )

        self.assertEqual(FailureCode.INVALID_ENDPOINT, foreign_result.failure.code)
        self.assertEqual(FailureCode.INVALID_ENDPOINT, historical_result.failure.code)

    def test_fingerprint_changes_for_request_configuration_and_dependencies(self) -> None:
        request = self.request()
        origin = ResolvedEndpoint(
            self.origin_id, 10, "representative_point", 153.4, -27.9
        )
        destination = ResolvedEndpoint(
            self.destination_id, 11, "representative_point", 153.41, -27.905
        )
        profile = MobilityProfile(
            1,
            "fixture-profile",
            "Fixture",
            JourneyMode.WALK,
            1,
            {"speed_metres_per_second": 1.25},
        )
        policy = RoutingPolicy(
            1,
            "fixture-policy",
            "Fixture",
            PolicyKind.SOFT_AVOIDANCE,
            1,
            {"attribute": "stairs"},
        )
        capabilities = FictionalJourneyAdapter().capabilities()

        payloads = [
            (request, origin, destination, (profile,), (policy,), capabilities),
            (replace(request, mode=JourneyMode.PUBLIC_TRANSPORT), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, access_modes=(JourneyMode.CYCLE,)), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, time=JourneyTime(JourneyTimeKind.ARRIVE_BY, NOW.isoformat())), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, time=JourneyTime(JourneyTimeKind.DEPART_AT, (NOW + timedelta(minutes=1)).isoformat())), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, buffers=(JourneyBuffer("arrival", "Arrival", 60),)), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, requested_alternatives=2), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, require_geometry=False), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, require_complete_coverage=True), origin, destination, (profile,), (policy,), capabilities),
            (replace(request, required_features=("step_free",)), origin, destination, (profile,), (policy,), capabilities),
            (request, replace(origin, longitude=153.4001), destination, (profile,), (policy,), capabilities),
            (request, replace(origin, geometry_id=12), destination, (profile,), (policy,), capabilities),
            (request, origin, destination, (replace(profile, revision=2),), (policy,), capabilities),
            (request, origin, destination, (replace(profile, profile_key="fixture-profile-2"),), (policy,), capabilities),
            (request, origin, destination, (replace(profile, definition={"speed_metres_per_second": 1.5}),), (policy,), capabilities),
            (request, origin, destination, (profile,), (replace(policy, revision=2),), capabilities),
            (request, origin, destination, (profile,), (replace(policy, policy_key="fixture-policy-2"),), capabilities),
            (request, origin, destination, (profile,), (replace(policy, definition={"attribute": "ferry"}),), capabilities),
            (request, origin, destination, (profile,), (policy,), replace(capabilities, adapter_version="fixture-2")),
            (request, origin, destination, (profile,), (policy,), replace(capabilities, sources=(JourneySource("fictional-streets", "v8", "2026-08-02"),))),
            (request, origin, destination, (profile,), (policy,), replace(capabilities, sources=(JourneySource("fictional-streets", "fictional-streets-7", "2026-08-02"),))),
            (request, origin, destination, (profile,), (policy,), replace(capabilities, coverage_keys=("fictional-inland",))),
            (request, origin, destination, (profile,), (policy,), replace(capabilities, transit_inputs=(TransitInput.LIVE_ENRICHMENT,))),
        ]
        fingerprints = {
            journey_fingerprint(*payload) for payload in payloads
        }

        self.assertEqual(len(payloads), len(fingerprints))

    def test_cache_is_bounded_clearable_and_not_the_profile_store(self) -> None:
        for index in range(6):
            self.plan(
                self.request(
                    time=JourneyTime(
                        JourneyTimeKind.DEPART_AT,
                        (NOW + timedelta(minutes=index)).isoformat(),
                    )
                ),
                FictionalJourneyAdapter(adapter_version=f"fixture-{index}"),
            )

        self.assertEqual(4, self.cache.count())
        self.assertEqual(4, self.cache.clear())
        self.assertEqual(0, self.cache.count())
        with connect(self.database_path) as connection:
            retained = connection.execute(
                "SELECT profile_key FROM mobility_profiles"
            ).fetchall()
        self.assertEqual(["regular-walk-fixture"], [row[0] for row in retained])

    def test_corrupt_disposable_cache_entry_degrades_to_a_miss(self) -> None:
        execution = self.plan(self.request(), FictionalJourneyAdapter())
        with sqlite3.connect(self.cache.path) as connection:
            connection.execute(
                "UPDATE journey_results SET result_json='not-json' WHERE fingerprint=?",
                (execution.result.fingerprint,),
            )

        lookup = self.cache.lookup(execution.result.fingerprint, now=NOW)

        self.assertEqual("miss", lookup.status.value)
        self.assertIsNone(lookup.result)
        self.assertEqual(0, self.cache.count())

    def test_corrupt_disposable_cache_file_is_rebuilt_without_personal_data_loss(self) -> None:
        self.cache.path.write_bytes(b"not a sqlite database")

        lookup = self.cache.lookup("missing-fingerprint", now=NOW)

        self.assertEqual("miss", lookup.status.value)
        self.assertEqual(0, self.cache.count())
        with connect(self.database_path) as connection:
            self.assertIsNotNone(
                connection.execute(
                    "SELECT 1 FROM mobility_profiles WHERE profile_key=?",
                    ("regular-walk-fixture",),
                ).fetchone()
            )

    def test_unavailable_cache_never_blocks_a_local_journey_result(self) -> None:
        unavailable_path = self.root / "cache-is-a-directory"
        unavailable_path.mkdir()
        unavailable_cache = JourneyCache(unavailable_path, maximum_entries=2)
        with connect(self.database_path) as connection:
            execution = plan_journey(
                connection,
                self.request(),
                FictionalJourneyAdapter(),
                cache=unavailable_cache,
                now=NOW,
            )

        self.assertIsNone(execution.failure)
        self.assertIsNotNone(execution.result)
        self.assertEqual("miss", execution.cache_status.value)


if __name__ == "__main__":
    unittest.main()
