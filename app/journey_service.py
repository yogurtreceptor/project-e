"""Journey orchestration over canonical endpoints and replaceable adapters."""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import UTC, datetime
from typing import Protocol

from app.journey_cache import JourneyCache
from app.journey_contract import (
    AdapterOutcome,
    CacheStatus,
    CoverageState,
    EndpointReference,
    FailureCode,
    JourneyCapabilities,
    JourneyExecution,
    JourneyFailure,
    JourneyMode,
    JourneyRequest,
    JourneyResult,
    JourneyStageMode,
    JourneyTimeKind,
    MobilityProfile,
    PolicyKind,
    PreparedJourney,
    ResolvedEndpoint,
    RoutingPolicy,
    TransitInput,
    journey_fingerprint,
)
from app.journey_repository import get_mobility_profile, get_routing_policy


class JourneyAdapter(Protocol):
    def capabilities(self) -> JourneyCapabilities: ...

    def plan(self, prepared: PreparedJourney) -> AdapterOutcome: ...


_ENDPOINT_ROLE_ORDER = ("route_anchor", "entrance", "representative_point")
_DURATION_KINDS = {"scheduled", "estimated", "wait"}


def plan_journey(
    connection: sqlite3.Connection,
    request: JourneyRequest,
    adapter: JourneyAdapter,
    *,
    cache: JourneyCache | None = None,
    now: datetime | None = None,
) -> JourneyExecution:
    """Resolve, preflight, fingerprint, cache, call, and validate one request."""
    current = _normalise_now(now)
    request_failure = _validate_request(request)
    if request_failure:
        return _failed(request_failure)

    origin, failure = resolve_journey_endpoint(connection, request.origin)
    if failure:
        return _failed(failure)
    destination, failure = resolve_journey_endpoint(connection, request.destination)
    if failure:
        return _failed(failure)
    assert origin is not None and destination is not None

    profiles, failure = _load_profiles(connection, request)
    if failure:
        return _failed(failure)
    policies, failure = _load_policies(connection, request)
    if failure:
        return _failed(failure)

    try:
        capabilities = adapter.capabilities()
    except Exception:
        return _failed(
            JourneyFailure(
                FailureCode.PROVIDER_FAILURE,
                "The journey provider could not declare its capabilities.",
            )
        )
    if not isinstance(capabilities, JourneyCapabilities):
        return _failed(
            JourneyFailure(
                FailureCode.INCOMPATIBLE_DATA,
                "The journey provider returned an invalid capability declaration.",
            )
        )
    capability_failure = _validate_capabilities(capabilities)
    if capability_failure:
        return _failed(capability_failure)
    preflight_failure = _preflight(request, profiles, policies, capabilities)
    if preflight_failure:
        return _failed(preflight_failure)

    fingerprint = journey_fingerprint(
        request, origin, destination, profiles, policies, capabilities
    )
    prepared = PreparedJourney(
        request=request,
        origin=origin,
        destination=destination,
        profiles=profiles,
        policies=policies,
        capabilities=capabilities,
        fingerprint=fingerprint,
    )

    cache_status = CacheStatus.MISS
    cached_result = None
    if cache is not None:
        try:
            lookup = cache.lookup(fingerprint, now=current)
            cache_status = lookup.status
            cached_result = lookup.result
            if lookup.result is not None:
                cached_failure = _safe_validate_result(
                    prepared, lookup.result, current=current, allow_stale=True
                )
                if cached_failure:
                    cache.delete(fingerprint)
                    cache_status = CacheStatus.MISS
                    cached_result = None
                elif lookup.status == CacheStatus.FRESH:
                    return JourneyExecution(
                        cache_status=CacheStatus.FRESH,
                        result=lookup.result,
                        cached_result=lookup.result,
                    )
        except (OSError, sqlite3.Error):
            cache_status = CacheStatus.MISS
            cached_result = None

    try:
        outcome = adapter.plan(prepared)
    except Exception:
        return JourneyExecution(
            cache_status=cache_status,
            failure=JourneyFailure(
                FailureCode.PROVIDER_FAILURE,
                "The journey provider failed while calculating the request.",
            ),
            cached_result=cached_result,
            adapter_calls=1,
        )
    if not isinstance(outcome, AdapterOutcome):
        return JourneyExecution(
            cache_status=cache_status,
            failure=JourneyFailure(
                FailureCode.INVALID_RESULT,
                "The journey provider returned an invalid outcome.",
            ),
            cached_result=cached_result,
            adapter_calls=1,
        )
    if outcome.failure:
        if not isinstance(outcome.failure, JourneyFailure) or not isinstance(
            outcome.failure.code, FailureCode
        ):
            return JourneyExecution(
                cache_status=cache_status,
                failure=_invalid_result(
                    "The journey provider returned an invalid failure outcome."
                ),
                cached_result=cached_result,
                adapter_calls=1,
            )
        return JourneyExecution(
            cache_status=cache_status,
            failure=outcome.failure,
            cached_result=cached_result,
            adapter_calls=1,
        )
    assert outcome.result is not None
    if not isinstance(outcome.result, JourneyResult):
        result_failure = _invalid_result(
            "The journey provider returned an invalid result type."
        )
    else:
        result_failure = _safe_validate_result(
            prepared, outcome.result, current=current, allow_stale=False
        )
    if result_failure:
        return JourneyExecution(
            cache_status=cache_status,
            failure=result_failure,
            cached_result=cached_result,
            adapter_calls=1,
        )
    if cache is not None:
        try:
            cache.store(outcome.result, now=current)
        except (OSError, sqlite3.Error):
            pass
    return JourneyExecution(
        cache_status=cache_status,
        result=outcome.result,
        cached_result=cached_result,
        adapter_calls=1,
    )


def resolve_journey_endpoint(
    connection: sqlite3.Connection, reference: EndpointReference
) -> tuple[ResolvedEndpoint | None, JourneyFailure | None]:
    location = connection.execute(
        "SELECT type, deleted_at FROM entities WHERE id=?", (reference.location_id,)
    ).fetchone()
    if location is None or location["type"] != "location" or location["deleted_at"]:
        return None, JourneyFailure(
            FailureCode.INVALID_ENDPOINT,
            "Journey endpoint Location does not exist or is unavailable.",
            related_keys=(str(reference.location_id),),
        )

    if reference.geometry_id is not None:
        row = connection.execute(
            """SELECT * FROM location_geometries
               WHERE id=? AND location_entity_id=?""",
            (reference.geometry_id, reference.location_id),
        ).fetchone()
        if not _usable_endpoint_geometry(row):
            return None, JourneyFailure(
                FailureCode.INVALID_ENDPOINT,
                "The selected endpoint geometry is not a current routing point.",
                related_keys=(str(reference.geometry_id),),
            )
        return _resolved_endpoint(row), None

    for role in _ENDPOINT_ROLE_ORDER:
        rows = connection.execute(
            """SELECT * FROM location_geometries
               WHERE location_entity_id=? AND role=? AND geometry_type='Point'
                 AND is_current=1
               ORDER BY is_preferred DESC, id DESC""",
            (reference.location_id, role),
        ).fetchall()
        if not rows:
            continue
        preferred = [row for row in rows if row["is_preferred"]]
        if len(preferred) == 1:
            return _resolved_endpoint(preferred[0]), None
        if len(rows) == 1:
            return _resolved_endpoint(rows[0]), None
        candidate_ids = tuple(str(row["id"]) for row in rows)
        return None, JourneyFailure(
            FailureCode.AMBIGUOUS_ENDPOINT,
            "The Location has several possible access points; choose one explicitly.",
            related_keys=candidate_ids,
            details={"location_id": reference.location_id, "geometry_role": role},
        )
    return None, JourneyFailure(
        FailureCode.INVALID_ENDPOINT,
        "The Location has no current route anchor, entrance, or representative point.",
        related_keys=(str(reference.location_id),),
    )


def _validate_request(request: JourneyRequest) -> JourneyFailure | None:
    if (
        not isinstance(request.mode, JourneyMode)
        or any(not isinstance(mode, JourneyMode) for mode in request.access_modes)
        or not isinstance(request.time.kind, JourneyTimeKind)
    ):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST,
            "Journey mode and time semantics are invalid.",
        )
    if (
        len(set(request.access_modes)) != len(request.access_modes)
        or request.mode in request.access_modes
        or not isinstance(request.require_geometry, bool)
        or not isinstance(request.require_complete_coverage, bool)
    ):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST,
            "Journey access modes or completeness requirements are invalid.",
        )
    if (
        isinstance(request.origin.location_id, bool)
        or not isinstance(request.origin.location_id, int)
        or isinstance(request.destination.location_id, bool)
        or not isinstance(request.destination.location_id, int)
        or request.origin.location_id <= 0
        or request.destination.location_id <= 0
    ):
        return JourneyFailure(
            FailureCode.INVALID_ENDPOINT, "Journey endpoints must be deliberate Locations."
        )
    if (
        isinstance(request.requested_alternatives, bool)
        or not isinstance(request.requested_alternatives, int)
        or request.requested_alternatives <= 0
    ):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST,
            "Requested alternatives must be a positive number.",
        )
    if len(set(request.profile_keys)) != len(request.profile_keys):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST, "Mobility profiles must not be repeated."
        )
    if len(set(request.policy_keys)) != len(request.policy_keys):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST, "Routing policies must not be repeated."
        )
    if len(set(request.required_features)) != len(request.required_features):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST, "Required features must not be repeated."
        )
    if any(
        not isinstance(key, str) or not key.strip()
        for key in request.profile_keys + request.policy_keys + request.required_features
    ):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST,
            "Profile, policy and requirement keys must be non-empty text.",
        )
    try:
        _parse_timestamp(request.time.value)
    except (TypeError, ValueError):
        return JourneyFailure(
            FailureCode.INVALID_REQUEST,
            "Journey time must be an ISO timestamp with a timezone.",
        )
    buffer_keys: set[str] = set()
    for item in request.buffers:
        if (
            not isinstance(item.buffer_key, str)
            or not item.buffer_key.strip()
            or not isinstance(item.label, str)
            or not item.label.strip()
            or isinstance(item.seconds, bool)
            or not isinstance(item.seconds, int)
            or item.seconds < 0
        ):
            return JourneyFailure(
                FailureCode.INVALID_REQUEST,
                "Journey buffers require a key, label, and non-negative duration.",
            )
        if item.buffer_key in buffer_keys:
            return JourneyFailure(
                FailureCode.INVALID_REQUEST, "Journey buffer keys must be unique."
            )
        buffer_keys.add(item.buffer_key)
    return None


def _load_profiles(
    connection: sqlite3.Connection, request: JourneyRequest
) -> tuple[tuple[MobilityProfile, ...], JourneyFailure | None]:
    profiles: list[MobilityProfile] = []
    valid_modes = {request.mode, *request.access_modes}
    for key in request.profile_keys:
        profile = get_mobility_profile(connection, key)
        if profile is None:
            return (), JourneyFailure(
                FailureCode.UNSUPPORTED_PROFILE,
                "A requested mobility profile is unavailable.",
                related_keys=(key,),
            )
        if profile.primary_mode not in valid_modes:
            return (), JourneyFailure(
                FailureCode.UNSUPPORTED_PROFILE,
                "A mobility profile does not apply to the requested journey modes.",
                related_keys=(key,),
            )
        profiles.append(profile)
    return tuple(profiles), None


def _load_policies(
    connection: sqlite3.Connection, request: JourneyRequest
) -> tuple[tuple[RoutingPolicy, ...], JourneyFailure | None]:
    policies: list[RoutingPolicy] = []
    for key in request.policy_keys:
        policy = get_routing_policy(connection, key)
        if policy is None or not policy.is_enabled:
            return (), JourneyFailure(
                FailureCode.UNSUPPORTED_POLICY,
                "A requested routing policy is unavailable or disabled.",
                related_keys=(key,),
            )
        policies.append(policy)
    return tuple(policies), None


def _validate_capabilities(
    capabilities: JourneyCapabilities,
) -> JourneyFailure | None:
    if (
        not isinstance(capabilities.adapter_key, str)
        or not capabilities.adapter_key.strip()
        or not isinstance(capabilities.adapter_version, str)
        or not capabilities.adapter_version.strip()
        or capabilities.execution not in {"local", "network"}
        or not capabilities.modes
        or any(not isinstance(item, JourneyMode) for item in capabilities.modes)
        or not capabilities.stage_modes
        or any(
            not isinstance(item, JourneyStageMode) for item in capabilities.stage_modes
        )
        or not capabilities.time_semantics
        or any(
            not isinstance(item, JourneyTimeKind)
            for item in capabilities.time_semantics
        )
        or any(
            not isinstance(item, TransitInput)
            for item in capabilities.transit_inputs
        )
        or any(
            not isinstance(item, PolicyKind)
            for item in capabilities.supported_policy_kinds
        )
        or not isinstance(capabilities.supports_geometry, bool)
        or any(
            not isinstance(item, str) or not item.strip()
            for item in capabilities.supported_requirements
        )
        or isinstance(capabilities.maximum_alternatives, bool)
        or not isinstance(capabilities.maximum_alternatives, int)
        or capabilities.maximum_alternatives <= 0
    ):
        return JourneyFailure(
            FailureCode.INCOMPATIBLE_DATA,
            "The journey provider capability declaration is invalid.",
        )
    if (
        not capabilities.coverage_keys
        or any(not isinstance(key, str) or not key.strip() for key in capabilities.coverage_keys)
        or len(set(capabilities.coverage_keys)) != len(capabilities.coverage_keys)
        or len(set(capabilities.modes)) != len(capabilities.modes)
        or len(set(capabilities.stage_modes)) != len(capabilities.stage_modes)
        or len(set(capabilities.time_semantics)) != len(capabilities.time_semantics)
        or len(set(capabilities.transit_inputs)) != len(capabilities.transit_inputs)
        or len(set(capabilities.supported_requirements))
        != len(capabilities.supported_requirements)
        or len(set(capabilities.supported_policy_kinds))
        != len(capabilities.supported_policy_kinds)
        or not capabilities.sources
        or any(
            not isinstance(source.source_key, str)
            or not source.source_key.strip()
            or not isinstance(source.version, str)
            or not source.version.strip()
            or not isinstance(source.freshness, str)
            or not source.freshness.strip()
            for source in capabilities.sources
        )
        or len({source.source_key for source in capabilities.sources})
        != len(capabilities.sources)
        or (
            JourneyMode.PUBLIC_TRANSPORT in capabilities.modes
            and not capabilities.transit_inputs
        )
        or (
            JourneyMode.PUBLIC_TRANSPORT not in capabilities.modes
            and capabilities.transit_inputs
        )
    ):
        return JourneyFailure(
            FailureCode.INCOMPATIBLE_DATA,
            "The journey provider did not declare versioned source dependencies.",
        )
    return None


def _preflight(
    request: JourneyRequest,
    profiles: tuple[MobilityProfile, ...],
    policies: tuple[RoutingPolicy, ...],
    capabilities: JourneyCapabilities,
) -> JourneyFailure | None:
    requested_modes = {request.mode, *request.access_modes}
    unsupported_modes = requested_modes - set(capabilities.modes)
    if unsupported_modes:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_MODE,
            "The journey provider does not support every requested mode.",
            related_keys=tuple(sorted(mode.value for mode in unsupported_modes)),
        )
    if request.time.kind not in capabilities.time_semantics:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_REQUIREMENT,
            "The journey provider does not support the requested time semantics.",
            related_keys=(request.time.kind.value,),
        )
    if request.require_geometry and not capabilities.supports_geometry:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_REQUIREMENT,
            "The journey provider cannot return required route geometry.",
            related_keys=("geometry",),
        )
    if request.requested_alternatives > capabilities.maximum_alternatives:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_REQUIREMENT,
            "The journey provider cannot return the requested number of alternatives.",
            related_keys=("alternatives",),
        )
    unsupported_features = set(request.required_features) - set(
        capabilities.supported_requirements
    )
    if unsupported_features:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_REQUIREMENT,
            "The journey provider cannot satisfy every required feature.",
            related_keys=tuple(sorted(unsupported_features)),
        )
    unsupported_policy_keys = tuple(
        policy.policy_key
        for policy in policies
        if policy.kind not in capabilities.supported_policy_kinds
    )
    if unsupported_policy_keys:
        return JourneyFailure(
            FailureCode.UNSUPPORTED_POLICY,
            "The journey provider cannot apply every requested routing policy.",
            related_keys=unsupported_policy_keys,
        )
    if not capabilities.coverage_keys:
        return JourneyFailure(
            FailureCode.ABSENT_COVERAGE,
            "The journey provider declares no usable coverage.",
        )
    return None


def _validate_result(
    prepared: PreparedJourney,
    result: JourneyResult,
    *,
    current: datetime,
    allow_stale: bool,
) -> JourneyFailure | None:
    capabilities = prepared.capabilities
    if result.fingerprint != prepared.fingerprint:
        return _invalid_result("The journey result fingerprint does not match its request.")
    if not _same_endpoint(prepared.origin, result.origin) or not _same_endpoint(
        prepared.destination, result.destination
    ):
        return _invalid_result("The journey result changed a resolved endpoint.")
    if (
        result.provenance.adapter_key != capabilities.adapter_key
        or result.provenance.adapter_version != capabilities.adapter_version
        or result.provenance.execution != capabilities.execution
        or result.provenance.sources != capabilities.sources
    ):
        return _invalid_result("The journey result provenance does not match its provider.")
    try:
        calculated = _parse_timestamp(result.provenance.calculated_at)
        fresh_until = _parse_timestamp(result.provenance.fresh_until)
    except (TypeError, ValueError):
        return _invalid_result("The journey result freshness timestamps are invalid.")
    if fresh_until < calculated:
        return _invalid_result("The journey result is stale before it was calculated.")
    if fresh_until < current and not allow_stale:
        return JourneyFailure(
            FailureCode.STALE_DATA,
            "The journey provider returned data that is already stale.",
        )
    if not result.textual_itinerary.strip():
        return _invalid_result("The journey result has no textual itinerary.")
    if not _valid_result_endpoint(result.origin) or not _valid_result_endpoint(
        result.destination
    ):
        return _invalid_result("The journey result has invalid endpoint snapping.")
    if not result.alternatives or len(result.alternatives) > prepared.request.requested_alternatives:
        return _invalid_result("The journey result has an invalid number of alternatives.")
    if result.buffers != prepared.request.buffers:
        return _invalid_result("The journey result changed the named buffer assumptions.")
    if result.applied_profile_keys != prepared.request.profile_keys:
        return _invalid_result(
            "The journey result did not apply every requested mobility profile."
        )
    requested_policy_keys = set(prepared.request.policy_keys)
    policy_groups = (
        result.applied_policy_keys,
        result.conflicting_policy_keys,
        result.unsatisfied_policy_keys,
    )
    reported_policy_keys = set().union(*(set(group) for group in policy_groups))
    if (
        reported_policy_keys != requested_policy_keys
        or any(len(group) != len(set(group)) for group in policy_groups)
        or sum(len(group) for group in policy_groups) != len(reported_policy_keys)
    ):
        return _invalid_result(
            "Every requested policy must be reported exactly once as applied, "
            "conflicting, or unsatisfied."
        )
    if (
        not isinstance(result.coverage.state, CoverageState)
        or not result.coverage.explanation.strip()
        or not result.coverage.coverage_keys
        or not set(result.coverage.coverage_keys) <= set(capabilities.coverage_keys)
        or any(
            not isinstance(item, str) or not item.strip()
            for item in result.coverage.coverage_keys
            + result.coverage.missing_capabilities
            + result.warnings
        )
    ):
        return _invalid_result("The journey result reports undeclared coverage.")
    for alternative in result.alternatives:
        failure = _validate_alternative(prepared, alternative)
        if failure:
            return failure
    if result.coverage.state == CoverageState.PARTIAL and prepared.request.require_complete_coverage:
        return JourneyFailure(
            FailureCode.PARTIAL_COVERAGE,
            "The route has partial coverage but complete coverage was required.",
            related_keys=result.coverage.missing_capabilities,
        )
    if result.conflicting_policy_keys:
        return JourneyFailure(
            FailureCode.POLICY_CONFLICT,
            "Requested routing policies conflict and require a decision.",
            related_keys=result.conflicting_policy_keys,
        )
    hard_policy_keys = {
        policy.policy_key
        for policy in prepared.policies
        if policy.kind == PolicyKind.HARD_EXCLUSION
    }
    unsatisfied_hard = tuple(
        key for key in result.unsatisfied_policy_keys if key in hard_policy_keys
    )
    if unsatisfied_hard:
        return JourneyFailure(
            FailureCode.NO_POLICY_COMPLIANT_ROUTE,
            "No route satisfies every hard routing policy.",
            related_keys=unsatisfied_hard,
        )
    limit_failure = _profile_limit_failure(prepared.profiles, result)
    if limit_failure:
        return limit_failure
    return None


def _safe_validate_result(
    prepared: PreparedJourney,
    result: JourneyResult,
    *,
    current: datetime,
    allow_stale: bool,
) -> JourneyFailure | None:
    try:
        return _validate_result(
            prepared, result, current=current, allow_stale=allow_stale
        )
    except Exception:
        return _invalid_result("The journey provider returned a malformed result.")


def _validate_alternative(prepared: PreparedJourney, alternative) -> JourneyFailure | None:
    if (
        not alternative.alternative_key.strip()
        or not alternative.stages
        or not _finite_nonnegative(alternative.straight_line_distance_metres)
        or not _finite_nonnegative(alternative.route_distance_metres)
        or isinstance(alternative.elapsed_duration_seconds, bool)
        or not isinstance(alternative.elapsed_duration_seconds, int)
        or alternative.elapsed_duration_seconds < 0
    ):
        return _invalid_result("A journey alternative has invalid summary values.")
    for value in (
        alternative.scheduled_duration_seconds,
        alternative.estimated_duration_seconds,
    ):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            return _invalid_result("A journey alternative has a negative duration.")
    if any(
        not isinstance(warning, str) or not warning.strip()
        for warning in alternative.warnings
    ):
        return _invalid_result("A journey alternative contains an invalid warning.")
    for milestone in alternative.milestones:
        if (
            not isinstance(milestone, (list, tuple))
            or len(milestone) != 3
            or not isinstance(milestone[0], str)
            or not milestone[0].strip()
            or not isinstance(milestone[1], str)
            or not milestone[1].strip()
        ):
            return _invalid_result("A journey alternative contains an invalid milestone.")
        try:
            _parse_timestamp(milestone[2])
        except (TypeError, ValueError):
            return _invalid_result("A journey milestone timestamp is invalid.")
    for stage in alternative.stages:
        if stage.mode not in prepared.capabilities.stage_modes:
            return _invalid_result("A journey result contains an undeclared stage mode.")
        if (
            not stage.instruction.strip()
            or isinstance(stage.duration_seconds, bool)
            or not isinstance(stage.duration_seconds, int)
            or stage.duration_seconds < 0
            or stage.duration_kind not in _DURATION_KINDS
            or (
                stage.route_distance_metres is not None
                and not _finite_nonnegative(stage.route_distance_metres)
            )
        ):
            return _invalid_result("A journey stage has invalid distance or time values.")
        try:
            starts = _parse_timestamp(stage.starts_at)
            ends = _parse_timestamp(stage.ends_at)
        except (TypeError, ValueError):
            return _invalid_result("A journey stage timestamp is invalid.")
        if ends < starts or int((ends - starts).total_seconds()) != stage.duration_seconds:
            return _invalid_result("A journey stage duration does not match its boundaries.")
        if (
            prepared.request.require_geometry
            and stage.mode != JourneyStageMode.WAIT
            and not stage.geometry
        ):
            return _invalid_result("A journey stage omitted required route geometry.")
        for longitude, latitude in stage.geometry:
            if (
                not math.isfinite(longitude)
                or not math.isfinite(latitude)
                or not -180 <= longitude <= 180
                or not -90 <= latitude <= 90
            ):
                return _invalid_result("A journey stage contains invalid WGS84 geometry.")
    return None


def _profile_limit_failure(
    profiles: tuple[MobilityProfile, ...], result: JourneyResult
) -> JourneyFailure | None:
    stage_modes = {
        JourneyMode.WALK: JourneyStageMode.WALK,
        JourneyMode.CYCLE: JourneyStageMode.CYCLE,
        JourneyMode.DRIVE: JourneyStageMode.DRIVE,
    }
    for profile in profiles:
        stage_mode = stage_modes.get(profile.primary_mode)
        if stage_mode is None:
            continue
        maximum_distance = profile.definition.get(
            "maximum_contiguous_distance_metres"
        )
        maximum_duration = profile.definition.get(
            "maximum_contiguous_duration_seconds"
        )
        for alternative in result.alternatives:
            for stage in alternative.stages:
                if stage.mode != stage_mode:
                    continue
                if (
                    maximum_distance is not None
                    and stage.route_distance_metres is not None
                    and stage.route_distance_metres > float(maximum_distance)
                ) or (
                    maximum_duration is not None
                    and stage.duration_seconds > float(maximum_duration)
                ):
                    return JourneyFailure(
                        FailureCode.PROFILE_LIMIT_EXCEEDED,
                        "A contiguous route stage exceeds the selected mobility profile.",
                        related_keys=(profile.profile_key,),
                    )
    return None


def _usable_endpoint_geometry(row: sqlite3.Row | None) -> bool:
    return bool(
        row is not None
        and row["geometry_type"] == "Point"
        and row["role"] in _ENDPOINT_ROLE_ORDER
        and row["is_current"]
    )


def _resolved_endpoint(row: sqlite3.Row) -> ResolvedEndpoint:
    coordinates = json.loads(row["coordinates_json"])
    return ResolvedEndpoint(
        location_id=int(row["location_entity_id"]),
        geometry_id=int(row["id"]),
        geometry_role=row["role"],
        longitude=float(coordinates[0]),
        latitude=float(coordinates[1]),
    )


def _same_endpoint(expected: ResolvedEndpoint, actual: ResolvedEndpoint) -> bool:
    return (
        expected.location_id == actual.location_id
        and expected.geometry_id == actual.geometry_id
        and expected.geometry_role == actual.geometry_role
        and expected.longitude == actual.longitude
        and expected.latitude == actual.latitude
    )


def _valid_result_endpoint(endpoint: ResolvedEndpoint) -> bool:
    snapped = (endpoint.snapped_longitude, endpoint.snapped_latitude)
    if (snapped[0] is None) != (snapped[1] is None):
        return False
    if snapped[0] is not None and (
        not math.isfinite(snapped[0])
        or not math.isfinite(snapped[1])
        or not -180 <= snapped[0] <= 180
        or not -90 <= snapped[1] <= 90
    ):
        return False
    return not (
        endpoint.snap_distance_metres is not None
        and (
            snapped[0] is None
            or not math.isfinite(endpoint.snap_distance_metres)
            or endpoint.snap_distance_metres < 0
        )
    )


def _invalid_result(message: str) -> JourneyFailure:
    return JourneyFailure(FailureCode.INVALID_RESULT, message)


def _finite_nonnegative(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value >= 0
    )


def _failed(failure: JourneyFailure) -> JourneyExecution:
    return JourneyExecution(cache_status=CacheStatus.MISS, failure=failure)


def _normalise_now(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Journey calculation time must include a timezone.")
    return value.astimezone(UTC)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamp requires a timezone.")
    return parsed.astimezone(UTC)
