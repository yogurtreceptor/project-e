"""Provider-independent journey request, result, failure, and fingerprint types."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class JourneyMode(str, Enum):
    WALK = "walk"
    CYCLE = "cycle"
    DRIVE = "drive"
    PUBLIC_TRANSPORT = "public_transport"


class JourneyStageMode(str, Enum):
    WALK = "walk"
    WAIT = "wait"
    BUS = "bus"
    TRAIN = "train"
    TRAM = "tram"
    FERRY = "ferry"
    CYCLE = "cycle"
    DRIVE = "drive"


class JourneyTimeKind(str, Enum):
    DEPART_AT = "depart_at"
    ARRIVE_BY = "arrive_by"


class TransitInput(str, Enum):
    STATIC_TIMETABLE = "static_timetable"
    LIVE_ENRICHMENT = "live_enrichment"


class PolicyKind(str, Enum):
    HARD_EXCLUSION = "hard_exclusion"
    SOFT_AVOIDANCE = "soft_avoidance"
    PREFERENCE = "preference"
    ADDED_COST = "added_cost"
    ADDED_BUFFER = "added_buffer"


class CoverageState(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class CacheStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    MISS = "miss"


class FailureCode(str, Enum):
    INVALID_REQUEST = "invalid_request"
    INVALID_ENDPOINT = "invalid_endpoint"
    AMBIGUOUS_ENDPOINT = "ambiguous_endpoint"
    ABSENT_COVERAGE = "absent_coverage"
    PARTIAL_COVERAGE = "partial_coverage"
    UNSUPPORTED_MODE = "unsupported_mode"
    UNSUPPORTED_PROFILE = "unsupported_profile"
    UNSUPPORTED_POLICY = "unsupported_policy"
    UNSUPPORTED_REQUIREMENT = "unsupported_requirement"
    NO_ROUTE = "no_route"
    NO_POLICY_COMPLIANT_ROUTE = "no_policy_compliant_route"
    PROFILE_LIMIT_EXCEEDED = "profile_limit_exceeded"
    POLICY_CONFLICT = "policy_conflict"
    STALE_DATA = "stale_data"
    INCOMPATIBLE_DATA = "incompatible_data"
    PROVIDER_FAILURE = "provider_failure"
    INVALID_RESULT = "invalid_result"


@dataclass(frozen=True)
class EndpointReference:
    location_id: int
    geometry_id: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {"location_id": self.location_id, "geometry_id": self.geometry_id}


@dataclass(frozen=True)
class ResolvedEndpoint:
    location_id: int
    geometry_id: int
    geometry_role: str
    longitude: float
    latitude: float
    snapped_longitude: float | None = None
    snapped_latitude: float | None = None
    snap_distance_metres: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "location_id": self.location_id,
            "geometry_id": self.geometry_id,
            "geometry_role": self.geometry_role,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "snapped_longitude": self.snapped_longitude,
            "snapped_latitude": self.snapped_latitude,
            "snap_distance_metres": self.snap_distance_metres,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ResolvedEndpoint":
        return cls(
            location_id=int(value["location_id"]),
            geometry_id=int(value["geometry_id"]),
            geometry_role=str(value["geometry_role"]),
            longitude=float(value["longitude"]),
            latitude=float(value["latitude"]),
            snapped_longitude=_optional_float(value.get("snapped_longitude")),
            snapped_latitude=_optional_float(value.get("snapped_latitude")),
            snap_distance_metres=_optional_float(value.get("snap_distance_metres")),
        )


@dataclass(frozen=True)
class JourneyTime:
    kind: JourneyTimeKind
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "value": self.value}


@dataclass(frozen=True)
class JourneyBuffer:
    buffer_key: str
    label: str
    seconds: int

    def to_dict(self) -> dict[str, object]:
        return {
            "buffer_key": self.buffer_key,
            "label": self.label,
            "seconds": self.seconds,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneyBuffer":
        return cls(
            buffer_key=str(value["buffer_key"]),
            label=str(value["label"]),
            seconds=int(value["seconds"]),
        )


@dataclass(frozen=True)
class JourneyRequest:
    origin: EndpointReference
    destination: EndpointReference
    mode: JourneyMode
    access_modes: tuple[JourneyMode, ...]
    time: JourneyTime
    profile_keys: tuple[str, ...]
    policy_keys: tuple[str, ...]
    buffers: tuple[JourneyBuffer, ...]
    requested_alternatives: int = 1
    require_geometry: bool = True
    require_complete_coverage: bool = False
    required_features: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "mode": self.mode.value,
            "access_modes": [mode.value for mode in self.access_modes],
            "time": self.time.to_dict(),
            "profile_keys": list(self.profile_keys),
            "policy_keys": list(self.policy_keys),
            "buffers": [item.to_dict() for item in self.buffers],
            "requested_alternatives": self.requested_alternatives,
            "require_geometry": self.require_geometry,
            "require_complete_coverage": self.require_complete_coverage,
            "required_features": list(self.required_features),
        }


@dataclass(frozen=True)
class MobilityProfile:
    id: int
    profile_key: str
    display_name: str
    primary_mode: JourneyMode
    revision: int
    definition: Mapping[str, Any]
    created_at: str = ""
    updated_at: str = ""

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "profile_key": self.profile_key,
            "primary_mode": self.primary_mode.value,
            "revision": self.revision,
            "definition": _json_value(self.definition),
        }


@dataclass(frozen=True)
class RoutingPolicy:
    id: int
    policy_key: str
    display_name: str
    kind: PolicyKind
    revision: int
    definition: Mapping[str, Any]
    is_enabled: bool = True
    created_at: str = ""
    updated_at: str = ""

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "policy_key": self.policy_key,
            "kind": self.kind.value,
            "revision": self.revision,
            "definition": _json_value(self.definition),
        }


@dataclass(frozen=True)
class JourneySource:
    source_key: str
    version: str
    freshness: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_key": self.source_key,
            "version": self.version,
            "freshness": self.freshness,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneySource":
        return cls(
            source_key=str(value["source_key"]),
            version=str(value["version"]),
            freshness=str(value["freshness"]),
        )


@dataclass(frozen=True)
class JourneyCapabilities:
    adapter_key: str
    adapter_version: str
    execution: str
    modes: tuple[JourneyMode, ...]
    stage_modes: tuple[JourneyStageMode, ...]
    time_semantics: tuple[JourneyTimeKind, ...]
    transit_inputs: tuple[TransitInput, ...]
    supports_geometry: bool
    supported_requirements: tuple[str, ...]
    supported_policy_kinds: tuple[PolicyKind, ...]
    maximum_alternatives: int
    coverage_keys: tuple[str, ...]
    sources: tuple[JourneySource, ...]

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "adapter_key": self.adapter_key,
            "adapter_version": self.adapter_version,
            "execution": self.execution,
            "modes": [item.value for item in self.modes],
            "stage_modes": [item.value for item in self.stage_modes],
            "time_semantics": [item.value for item in self.time_semantics],
            "transit_inputs": [item.value for item in self.transit_inputs],
            "supports_geometry": self.supports_geometry,
            "supported_requirements": list(self.supported_requirements),
            "supported_policy_kinds": [
                item.value for item in self.supported_policy_kinds
            ],
            "maximum_alternatives": self.maximum_alternatives,
            "coverage_keys": list(self.coverage_keys),
            "sources": [item.to_dict() for item in self.sources],
        }


@dataclass(frozen=True)
class CoverageReport:
    state: CoverageState
    explanation: str
    coverage_keys: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "explanation": self.explanation,
            "coverage_keys": list(self.coverage_keys),
            "missing_capabilities": list(self.missing_capabilities),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CoverageReport":
        return cls(
            state=CoverageState(str(value["state"])),
            explanation=str(value["explanation"]),
            coverage_keys=tuple(
                str(item) for item in value.get("coverage_keys", [])
            ),
            missing_capabilities=tuple(
                str(item) for item in value.get("missing_capabilities", [])
            ),
        )


@dataclass(frozen=True)
class JourneyProvenance:
    adapter_key: str
    adapter_version: str
    execution: str
    sources: tuple[JourneySource, ...]
    calculated_at: str
    fresh_until: str

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_key": self.adapter_key,
            "adapter_version": self.adapter_version,
            "execution": self.execution,
            "sources": [item.to_dict() for item in self.sources],
            "calculated_at": self.calculated_at,
            "fresh_until": self.fresh_until,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneyProvenance":
        return cls(
            adapter_key=str(value["adapter_key"]),
            adapter_version=str(value["adapter_version"]),
            execution=str(value["execution"]),
            sources=tuple(
                JourneySource.from_dict(item)
                for item in value.get("sources", [])
                if isinstance(item, Mapping)
            ),
            calculated_at=str(value["calculated_at"]),
            fresh_until=str(value["fresh_until"]),
        )


@dataclass(frozen=True)
class JourneyStage:
    mode: JourneyStageMode
    instruction: str
    starts_at: str
    ends_at: str
    duration_seconds: int
    duration_kind: str
    route_distance_metres: float | None = None
    geometry: tuple[tuple[float, float], ...] = ()
    service_name: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "instruction": self.instruction,
            "starts_at": self.starts_at,
            "ends_at": self.ends_at,
            "duration_seconds": self.duration_seconds,
            "duration_kind": self.duration_kind,
            "route_distance_metres": self.route_distance_metres,
            "geometry": [list(point) for point in self.geometry],
            "service_name": self.service_name,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneyStage":
        return cls(
            mode=JourneyStageMode(str(value["mode"])),
            instruction=str(value["instruction"]),
            starts_at=str(value["starts_at"]),
            ends_at=str(value["ends_at"]),
            duration_seconds=int(value["duration_seconds"]),
            duration_kind=str(value["duration_kind"]),
            route_distance_metres=_optional_float(value.get("route_distance_metres")),
            geometry=tuple(
                (float(point[0]), float(point[1]))
                for point in value.get("geometry", [])
            ),
            service_name=str(value.get("service_name", "")),
        )


@dataclass(frozen=True)
class JourneyAlternative:
    alternative_key: str
    stages: tuple[JourneyStage, ...]
    straight_line_distance_metres: float
    route_distance_metres: float
    scheduled_duration_seconds: int | None
    estimated_duration_seconds: int | None
    elapsed_duration_seconds: int
    milestones: tuple[tuple[str, str, str], ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "alternative_key": self.alternative_key,
            "stages": [item.to_dict() for item in self.stages],
            "straight_line_distance_metres": self.straight_line_distance_metres,
            "route_distance_metres": self.route_distance_metres,
            "scheduled_duration_seconds": self.scheduled_duration_seconds,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "elapsed_duration_seconds": self.elapsed_duration_seconds,
            "milestones": [list(item) for item in self.milestones],
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneyAlternative":
        scheduled = value.get("scheduled_duration_seconds")
        estimated = value.get("estimated_duration_seconds")
        return cls(
            alternative_key=str(value["alternative_key"]),
            stages=tuple(
                JourneyStage.from_dict(item)
                for item in value.get("stages", [])
                if isinstance(item, Mapping)
            ),
            straight_line_distance_metres=float(
                value["straight_line_distance_metres"]
            ),
            route_distance_metres=float(value["route_distance_metres"]),
            scheduled_duration_seconds=None if scheduled is None else int(scheduled),
            estimated_duration_seconds=None if estimated is None else int(estimated),
            elapsed_duration_seconds=int(value["elapsed_duration_seconds"]),
            milestones=tuple(
                (str(item[0]), str(item[1]), str(item[2]))
                for item in value.get("milestones", [])
            ),
            warnings=tuple(str(item) for item in value.get("warnings", [])),
        )


@dataclass(frozen=True)
class JourneyResult:
    fingerprint: str
    origin: ResolvedEndpoint
    destination: ResolvedEndpoint
    alternatives: tuple[JourneyAlternative, ...]
    coverage: CoverageReport
    applied_profile_keys: tuple[str, ...]
    applied_policy_keys: tuple[str, ...]
    conflicting_policy_keys: tuple[str, ...]
    unsatisfied_policy_keys: tuple[str, ...]
    buffers: tuple[JourneyBuffer, ...]
    provenance: JourneyProvenance
    textual_itinerary: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "origin": self.origin.to_dict(),
            "destination": self.destination.to_dict(),
            "alternatives": [item.to_dict() for item in self.alternatives],
            "coverage": self.coverage.to_dict(),
            "applied_profile_keys": list(self.applied_profile_keys),
            "applied_policy_keys": list(self.applied_policy_keys),
            "conflicting_policy_keys": list(self.conflicting_policy_keys),
            "unsatisfied_policy_keys": list(self.unsatisfied_policy_keys),
            "buffers": [item.to_dict() for item in self.buffers],
            "provenance": self.provenance.to_dict(),
            "textual_itinerary": self.textual_itinerary,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "JourneyResult":
        origin = value.get("origin")
        destination = value.get("destination")
        coverage = value.get("coverage")
        provenance = value.get("provenance")
        if not all(isinstance(item, Mapping) for item in (
            origin, destination, coverage, provenance
        )):
            raise ValueError("Cached journey result has invalid structured fields.")
        return cls(
            fingerprint=str(value["fingerprint"]),
            origin=ResolvedEndpoint.from_dict(origin),
            destination=ResolvedEndpoint.from_dict(destination),
            alternatives=tuple(
                JourneyAlternative.from_dict(item)
                for item in value.get("alternatives", [])
                if isinstance(item, Mapping)
            ),
            coverage=CoverageReport.from_dict(coverage),
            applied_profile_keys=tuple(
                str(item) for item in value.get("applied_profile_keys", [])
            ),
            applied_policy_keys=tuple(
                str(item) for item in value.get("applied_policy_keys", [])
            ),
            conflicting_policy_keys=tuple(
                str(item) for item in value.get("conflicting_policy_keys", [])
            ),
            unsatisfied_policy_keys=tuple(
                str(item) for item in value.get("unsatisfied_policy_keys", [])
            ),
            buffers=tuple(
                JourneyBuffer.from_dict(item)
                for item in value.get("buffers", [])
                if isinstance(item, Mapping)
            ),
            provenance=JourneyProvenance.from_dict(provenance),
            textual_itinerary=str(value["textual_itinerary"]),
            warnings=tuple(str(item) for item in value.get("warnings", [])),
        )


@dataclass(frozen=True)
class JourneyFailure:
    code: FailureCode
    message: str
    related_keys: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterOutcome:
    result: JourneyResult | None = None
    failure: JourneyFailure | None = None

    def __post_init__(self) -> None:
        if (self.result is None) == (self.failure is None):
            raise ValueError("An adapter outcome requires exactly one result or failure.")


@dataclass(frozen=True)
class PreparedJourney:
    request: JourneyRequest
    origin: ResolvedEndpoint
    destination: ResolvedEndpoint
    profiles: tuple[MobilityProfile, ...]
    policies: tuple[RoutingPolicy, ...]
    capabilities: JourneyCapabilities
    fingerprint: str


@dataclass(frozen=True)
class JourneyExecution:
    cache_status: CacheStatus
    result: JourneyResult | None = None
    failure: JourneyFailure | None = None
    cached_result: JourneyResult | None = None
    adapter_calls: int = 0


def journey_fingerprint(
    request: JourneyRequest,
    origin: ResolvedEndpoint,
    destination: ResolvedEndpoint,
    profiles: tuple[MobilityProfile, ...],
    policies: tuple[RoutingPolicy, ...],
    capabilities: JourneyCapabilities,
) -> str:
    """Hash every semantic request and dependency input using canonical JSON."""
    payload = {
        "contract_version": 1,
        "request": request.to_dict(),
        "resolved_origin": origin.to_dict(),
        "resolved_destination": destination.to_dict(),
        "profiles": [item.fingerprint_payload() for item in profiles],
        "policies": [item.fingerprint_payload() for item in policies],
        "capabilities": capabilities.fingerprint_payload(),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    """Validate and serialise a provider-independent JSON object deterministically."""
    normalised = _json_value(value)
    if not isinstance(normalised, dict):
        raise ValueError("Journey configuration must be a JSON object.")
    return json.dumps(
        normalised, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Journey configuration numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Journey configuration object keys must be text.")
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    raise ValueError("Journey configuration must contain only JSON values.")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)
