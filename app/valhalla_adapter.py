"""Production walking adapter for one verified local Valhalla capability."""

from __future__ import annotations

import json
import math
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Callable, Iterator, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.journey_contract import (
    AdapterOutcome,
    CoverageReport,
    CoverageState,
    FailureCode,
    JourneyAlternative,
    JourneyCapabilities,
    JourneyFailure,
    JourneyMode,
    JourneyProvenance,
    JourneyResult,
    JourneyStage,
    JourneyStageMode,
    JourneyTimeKind,
    PolicyKind,
    PreparedJourney,
    ResolvedEndpoint,
)
from app.routing_resources import (
    LocalValhallaCapability,
    verify_local_valhalla_resources,
)


ProviderTransport = Callable[[str, Mapping[str, object] | None], tuple[int, object]]
_RUNTIME_LOCK = threading.Lock()
_SUPPORTED_BUFFER_KEYS = {"preparation", "arrival"}
_SUPPORTED_STEP_STRENGTH = "strong"
_STRONG_STEP_PENALTY_SECONDS = 43_200
_REVIEWED_PROFILE_PRESETS = {
    "regular-walk": "regular",
    "fast-walk": "fast",
    "run": "run",
}


class ValhallaWalkingAdapter:
    """Translate Project E walking meaning to a local-only Valhalla process."""

    def __init__(
        self,
        capability: LocalValhallaCapability,
        *,
        transport: ProviderTransport | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.capability = capability
        self._transport = transport
        self._clock = clock or (lambda: datetime.now(UTC))

    def capabilities(self) -> JourneyCapabilities:
        return JourneyCapabilities(
            adapter_key="valhalla-local-walking",
            adapter_version=self.capability.adapter_version,
            execution="local",
            modes=(JourneyMode.WALK,),
            stage_modes=(JourneyStageMode.WALK,),
            time_semantics=(
                JourneyTimeKind.DEPART_AT,
                JourneyTimeKind.ARRIVE_BY,
            ),
            transit_inputs=(),
            supports_geometry=True,
            supported_requirements=(),
            supported_policy_kinds=(PolicyKind.SOFT_AVOIDANCE,),
            maximum_alternatives=3,
            coverage_keys=(self.capability.coverage_key,),
            sources=self.capability.sources,
        )

    def plan(self, prepared: PreparedJourney) -> AdapterOutcome:
        profile, profile_failure = self._walking_profile(prepared)
        if profile_failure:
            return AdapterOutcome(failure=profile_failure)
        policy_options, policy_keys, policy_failure = self._policy_options(prepared)
        if policy_failure:
            return AdapterOutcome(failure=policy_failure)
        unsupported_buffers = tuple(
            item.buffer_key
            for item in prepared.request.buffers
            if item.buffer_key not in _SUPPORTED_BUFFER_KEYS
        )
        if unsupported_buffers:
            return AdapterOutcome(
                failure=JourneyFailure(
                    FailureCode.UNSUPPORTED_REQUIREMENT,
                    "The local walking adapter does not understand every named buffer.",
                    related_keys=unsupported_buffers,
                )
            )
        coverage_failure = self._coverage_preflight(prepared)
        if coverage_failure:
            return AdapterOutcome(failure=coverage_failure)

        speed_metres_per_second = float(profile.definition["speed_metres_per_second"])
        locations = [
            {"lat": prepared.origin.latitude, "lon": prepared.origin.longitude},
            {"lat": prepared.destination.latitude, "lon": prepared.destination.longitude},
        ]
        costing_options: dict[str, object] = {
            "walking_speed": round(speed_metres_per_second * 3.6, 6),
            **policy_options,
        }
        maximum_distance = profile.definition.get(
            "maximum_contiguous_distance_metres"
        )
        if maximum_distance is not None:
            costing_options["max_distance"] = round(float(maximum_distance) / 1000, 6)

        try:
            with self._provider_session():
                failure = self._validate_provider_status()
                if failure:
                    return AdapterOutcome(failure=failure)
                status, locate_body = self._request_json(
                    "/locate",
                    {
                        "locations": locations,
                        "costing": "pedestrian",
                        "costing_options": {"pedestrian": costing_options},
                        "verbose": False,
                    },
                )
                if status < 200 or status >= 300:
                    return AdapterOutcome(
                        failure=self._provider_failure(status, locate_body, prepared, locate=True)
                    )
                snapped, locate_warnings = self._normalise_snaps(
                    locate_body, prepared.origin, prepared.destination
                )
                if isinstance(snapped, JourneyFailure):
                    return AdapterOutcome(failure=snapped)

                route_payload: dict[str, object] = {
                    "locations": locations,
                    "costing": "pedestrian",
                    "costing_options": {"pedestrian": costing_options},
                    "units": "kilometers",
                    "language": "en-GB",
                    "directions_type": "instructions",
                }
                if prepared.request.requested_alternatives > 1:
                    route_payload["alternates"] = (
                        prepared.request.requested_alternatives - 1
                    )
                status, route_body = self._request_json("/route", route_payload)
                if status < 200 or status >= 300:
                    return AdapterOutcome(
                        failure=self._provider_failure(status, route_body, prepared)
                    )
        except (OSError, RuntimeError, subprocess.SubprocessError, TimeoutError) as error:
            return AdapterOutcome(
                failure=JourneyFailure(
                    FailureCode.PROVIDER_FAILURE,
                    "The local walking provider could not be started or reached.",
                    details={"provider_error": str(error)},
                )
            )

        try:
            result = self._normalise_result(
                prepared,
                route_body,
                snapped,
                profile.display_name,
                policy_keys,
                locate_warnings,
            )
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as error:
            return AdapterOutcome(
                failure=JourneyFailure(
                    FailureCode.INCOMPATIBLE_DATA,
                    "The local walking provider returned an incompatible response.",
                    details={"provider_error": str(error)},
                )
            )
        return AdapterOutcome(result=result)

    def _walking_profile(
        self, prepared: PreparedJourney
    ) -> tuple[object | None, JourneyFailure | None]:
        if len(prepared.profiles) != 1:
            return None, JourneyFailure(
                FailureCode.UNSUPPORTED_PROFILE,
                "Choose exactly one reviewed walking profile.",
                related_keys=tuple(profile.profile_key for profile in prepared.profiles),
            )
        profile = prepared.profiles[0]
        definition = profile.definition
        speed = definition.get("speed_metres_per_second")
        preset = definition.get("preset_kind")
        measurements = definition.get("measurement_trials")
        if (
            profile.primary_mode != JourneyMode.WALK
            or _REVIEWED_PROFILE_PRESETS.get(profile.profile_key) != preset
            or isinstance(speed, bool)
            or not isinstance(speed, (int, float))
            or not math.isfinite(float(speed))
            or not 0.5 / 3.6 <= float(speed) <= 25 / 3.6
            or not isinstance(measurements, list)
            or len(measurements) < 3
        ):
            return None, JourneyFailure(
                FailureCode.UNSUPPORTED_PROFILE,
                "The selected Walk profile has not been reviewed from repeated measurements.",
                related_keys=(profile.profile_key,),
            )
        return profile, None

    def _policy_options(
        self, prepared: PreparedJourney
    ) -> tuple[dict[str, object], tuple[str, ...], JourneyFailure | None]:
        options: dict[str, object] = {}
        keys: list[str] = []
        for policy in prepared.policies:
            definition = policy.definition
            modes = definition.get("modes")
            if (
                policy.kind != PolicyKind.SOFT_AVOIDANCE
                or definition.get("attribute") != "steps"
                or definition.get("strength") != _SUPPORTED_STEP_STRENGTH
                or not isinstance(modes, list)
                or "walk" not in modes
            ):
                return {}, (), JourneyFailure(
                    FailureCode.UNSUPPORTED_POLICY,
                    "The local walking provider cannot translate a requested policy exactly.",
                    related_keys=(policy.policy_key,),
                )
            options["step_penalty"] = _STRONG_STEP_PENALTY_SECONDS
            keys.append(policy.policy_key)
        return options, tuple(keys), None

    def _coverage_preflight(self, prepared: PreparedJourney) -> JourneyFailure | None:
        west, south, east, north = self.capability.coverage_bbox
        outside = []
        for label, endpoint in (
            ("origin", prepared.origin),
            ("destination", prepared.destination),
        ):
            if not (
                west <= endpoint.longitude <= east
                and south <= endpoint.latitude <= north
            ):
                outside.append(label)
        if outside:
            return JourneyFailure(
                FailureCode.ABSENT_COVERAGE,
                "A selected endpoint is outside the declared local walking graph.",
                related_keys=tuple(outside),
                details={"coverage_key": self.capability.coverage_key},
            )
        return None

    def _validate_provider_status(self) -> JourneyFailure | None:
        status, body = self._request_json("/status", None)
        if status < 200 or status >= 300:
            return JourneyFailure(
                FailureCode.PROVIDER_FAILURE,
                "The local walking provider did not report ready status.",
            )
        if (
            not isinstance(body, Mapping)
            or body.get("version") != self.capability.provider_version
            or not {"route", "locate", "status"}
            <= set(body.get("available_actions", []))
        ):
            return JourneyFailure(
                FailureCode.INCOMPATIBLE_DATA,
                "The running local provider does not match the activated capability.",
            )
        return None

    def _normalise_snaps(
        self,
        body: object,
        origin: ResolvedEndpoint,
        destination: ResolvedEndpoint,
    ) -> tuple[
        tuple[ResolvedEndpoint, ResolvedEndpoint] | JourneyFailure,
        tuple[str, ...],
    ]:
        if not isinstance(body, list) or len(body) != 2:
            raise ValueError("Locate response must contain both endpoints.")
        resolved: list[ResolvedEndpoint] = []
        warnings: list[str] = []
        for label, endpoint, item in (
            ("origin", origin, body[0]),
            ("destination", destination, body[1]),
        ):
            if not isinstance(item, Mapping) or not isinstance(item.get("edges"), list):
                raise ValueError("Locate response has invalid endpoint structure.")
            candidates = []
            for edge in item["edges"]:
                if not isinstance(edge, Mapping):
                    continue
                try:
                    longitude = float(edge["correlated_lon"])
                    latitude = float(edge["correlated_lat"])
                except (KeyError, TypeError, ValueError):
                    continue
                distance = _haversine_metres(
                    endpoint.longitude,
                    endpoint.latitude,
                    longitude,
                    latitude,
                )
                candidates.append((distance, longitude, latitude))
            if not candidates:
                return (
                    JourneyFailure(
                        FailureCode.ABSENT_COVERAGE,
                        "The local walking graph has no usable edge near an endpoint.",
                        related_keys=(label,),
                    ),
                    (),
                )
            distance, longitude, latitude = min(candidates)
            if distance > self.capability.maximum_snap_distance_metres:
                return (
                    JourneyFailure(
                        FailureCode.ABSENT_COVERAGE,
                        "A walking endpoint would snap too far from its canonical point.",
                        related_keys=(label,),
                        details={
                            "snap_distance_metres": round(distance, 3),
                            "maximum_snap_distance_metres": self.capability.maximum_snap_distance_metres,
                        },
                    ),
                    (),
                )
            if distance > 25:
                warnings.append(
                    f"The {label} snapped {distance:.0f} m to the local walking network."
                )
            resolved.append(
                replace(
                    endpoint,
                    snapped_longitude=longitude,
                    snapped_latitude=latitude,
                    snap_distance_metres=round(distance, 3),
                )
            )
            raw_warnings = item.get("warnings", [])
            if isinstance(raw_warnings, list):
                warnings.extend(_provider_warning_text(value) for value in raw_warnings)
        return (resolved[0], resolved[1]), tuple(item for item in warnings if item)

    def _normalise_result(
        self,
        prepared: PreparedJourney,
        body: object,
        snapped: tuple[ResolvedEndpoint, ResolvedEndpoint],
        profile_name: str,
        policy_keys: tuple[str, ...],
        locate_warnings: tuple[str, ...],
    ) -> JourneyResult:
        if not isinstance(body, Mapping) or not isinstance(body.get("trip"), Mapping):
            raise ValueError("Route response has no trip.")
        trips: list[Mapping[str, object]] = [body["trip"]]
        raw_alternates = body.get("alternates", [])
        if not isinstance(raw_alternates, list):
            raise ValueError("Route alternatives are invalid.")
        for alternative in raw_alternates:
            if isinstance(alternative, Mapping) and isinstance(
                alternative.get("trip"), Mapping
            ):
                trips.append(alternative["trip"])
        trips = trips[: prepared.request.requested_alternatives]
        if not trips:
            raise ValueError("Route response contains no alternatives.")

        now = self._normalise_clock()
        fresh_until = now + timedelta(seconds=self.capability.cache_fresh_seconds)
        alternatives: list[JourneyAlternative] = []
        itinerary_sections: list[str] = []
        any_step_free = False
        provider_warnings = list(locate_warnings)
        route_within_declared_extent = True
        for index, trip in enumerate(trips, start=1):
            alternative, instructions, uses_steps, trip_warnings = self._normalise_trip(
                prepared, trip, index
            )
            alternatives.append(alternative)
            route_within_declared_extent = route_within_declared_extent and all(
                self._point_in_declared_extent(longitude, latitude)
                for stage in alternative.stages
                for longitude, latitude in stage.geometry
            )
            any_step_free = any_step_free or not uses_steps
            provider_warnings.extend(trip_warnings)
            summary = (
                f"Alternative {index}: walk {alternative.route_distance_metres / 1000:.2f} km "
                f"in about {_duration_label(alternative.estimated_duration_seconds or 0)}; "
                f"total elapsed {_duration_label(alternative.elapsed_duration_seconds)}."
            )
            itinerary_sections.append(
                summary
                + "\n"
                + "\n".join(
                    f"{instruction_index}. {instruction}"
                    for instruction_index, instruction in enumerate(instructions, start=1)
                )
            )

        if policy_keys and any_step_free:
            applied_policy_keys = policy_keys
            unsatisfied_policy_keys: tuple[str, ...] = ()
            policy_explanation = "The strong preference to avoid steps produced a step-free option."
        elif policy_keys:
            applied_policy_keys = ()
            unsatisfied_policy_keys = policy_keys
            policy_explanation = (
                "The strong preference to avoid steps was applied, but every returned option still uses steps."
            )
            provider_warnings.append(policy_explanation)
        else:
            applied_policy_keys = ()
            unsatisfied_policy_keys = ()
            policy_explanation = "No saved walking policy was requested."

        static_warning = (
            "Static local street estimate only; no live conditions, traffic, safety, lighting or accessibility claim is included."
        )
        provider_warnings.append(static_warning)
        if not route_within_declared_extent:
            provider_warnings.append(
                "Part of the returned route falls outside the declared rectangular graph extent."
            )
        provider_warnings = list(dict.fromkeys(item for item in provider_warnings if item))
        textual_itinerary = (
            f"Profile: {profile_name}. {policy_explanation}\n"
            f"Coverage: {self.capability.coverage_key}; source versions are listed below.\n"
            + "\n\n".join(itinerary_sections)
            + f"\n\n{static_warning}"
        )
        return JourneyResult(
            fingerprint=prepared.fingerprint,
            origin=snapped[0],
            destination=snapped[1],
            alternatives=tuple(alternatives),
            coverage=CoverageReport(
                CoverageState.COMPLETE
                if route_within_declared_extent
                else CoverageState.PARTIAL,
                (
                    "Both endpoints and the returned route are within the declared "
                    "versioned local street-graph extent; this is routing coverage, not "
                    "an administrative or safety guarantee."
                    if route_within_declared_extent
                    else "Both endpoints are covered, but part of the returned route lies outside the declared rectangular graph extent."
                ),
                coverage_keys=(self.capability.coverage_key,),
            ),
            applied_profile_keys=prepared.request.profile_keys,
            applied_policy_keys=applied_policy_keys,
            conflicting_policy_keys=(),
            unsatisfied_policy_keys=unsatisfied_policy_keys,
            buffers=prepared.request.buffers,
            provenance=JourneyProvenance(
                adapter_key=prepared.capabilities.adapter_key,
                adapter_version=prepared.capabilities.adapter_version,
                execution=prepared.capabilities.execution,
                sources=prepared.capabilities.sources,
                calculated_at=now.isoformat(),
                fresh_until=fresh_until.isoformat(),
            ),
            textual_itinerary=textual_itinerary,
            warnings=tuple(provider_warnings),
        )

    def _point_in_declared_extent(self, longitude: float, latitude: float) -> bool:
        west, south, east, north = self.capability.coverage_bbox
        return west <= longitude <= east and south <= latitude <= north

    def _normalise_trip(
        self,
        prepared: PreparedJourney,
        trip: Mapping[str, object],
        index: int,
    ) -> tuple[JourneyAlternative, tuple[str, ...], bool, tuple[str, ...]]:
        summary = trip.get("summary")
        legs = trip.get("legs")
        if not isinstance(summary, Mapping) or not isinstance(legs, list) or not legs:
            raise ValueError("Trip summary or legs are missing.")
        route_distance = float(summary["length"]) * 1000
        duration = max(0, int(round(float(summary["time"]))))
        if not math.isfinite(route_distance) or route_distance < 0:
            raise ValueError("Trip distance is invalid.")
        geometry: list[tuple[float, float]] = []
        instructions: list[str] = []
        uses_steps = False
        warnings: list[str] = []
        for leg in legs:
            if not isinstance(leg, Mapping):
                raise ValueError("Trip leg is invalid.")
            points = _decode_polyline6(str(leg["shape"]))
            if geometry and points and geometry[-1] == points[0]:
                points = points[1:]
            geometry.extend(points)
            maneuvers = leg.get("maneuvers", [])
            if not isinstance(maneuvers, list):
                raise ValueError("Trip maneuvers are invalid.")
            for maneuver in maneuvers:
                if not isinstance(maneuver, Mapping):
                    continue
                instruction = str(maneuver.get("instruction", "")).strip()
                if instruction:
                    instructions.append(instruction)
                uses_steps = uses_steps or maneuver.get("type") == 40
        if len(geometry) < 2 or not instructions:
            raise ValueError("Trip geometry or instructions are incomplete.")
        raw_warnings = trip.get("warnings", [])
        if isinstance(raw_warnings, list):
            warnings.extend(_provider_warning_text(value) for value in raw_warnings)

        preparation = sum(
            item.seconds
            for item in prepared.request.buffers
            if item.buffer_key == "preparation"
        )
        arrival = sum(
            item.seconds
            for item in prepared.request.buffers
            if item.buffer_key == "arrival"
        )
        anchor = datetime.fromisoformat(prepared.request.time.value)
        if prepared.request.time.kind == JourneyTimeKind.DEPART_AT:
            journey_start = anchor
            walk_start = journey_start + timedelta(seconds=preparation)
            walk_end = walk_start + timedelta(seconds=duration)
            journey_end = walk_end + timedelta(seconds=arrival)
        else:
            journey_end = anchor
            walk_end = journey_end - timedelta(seconds=arrival)
            walk_start = walk_end - timedelta(seconds=duration)
            journey_start = walk_start - timedelta(seconds=preparation)
        milestones = (
            ("start", "Start preparation", journey_start.isoformat()),
            ("leave", "Leave origin", walk_start.isoformat()),
            ("arrive", "Arrive at destination", walk_end.isoformat()),
            ("ready", "Arrival buffer complete", journey_end.isoformat()),
        )
        elapsed = preparation + duration + arrival
        alternative_warnings = (
            ("This option still uses steps despite the selected soft avoidance.",)
            if uses_steps and prepared.policies
            else ()
        )
        return (
            JourneyAlternative(
                alternative_key=f"walk-{index}",
                stages=(
                    JourneyStage(
                        mode=JourneyStageMode.WALK,
                        instruction=(
                            "Walk from the selected canonical origin to the selected canonical destination."
                        ),
                        starts_at=walk_start.isoformat(),
                        ends_at=walk_end.isoformat(),
                        duration_seconds=duration,
                        duration_kind="estimated",
                        route_distance_metres=round(route_distance, 3),
                        geometry=tuple(geometry),
                    ),
                ),
                straight_line_distance_metres=round(
                    _haversine_metres(
                        prepared.origin.longitude,
                        prepared.origin.latitude,
                        prepared.destination.longitude,
                        prepared.destination.latitude,
                    ),
                    3,
                ),
                route_distance_metres=round(route_distance, 3),
                scheduled_duration_seconds=None,
                estimated_duration_seconds=duration,
                elapsed_duration_seconds=elapsed,
                milestones=milestones,
                warnings=alternative_warnings,
            ),
            tuple(instructions),
            uses_steps,
            tuple(item for item in warnings if item),
        )

    def _provider_failure(
        self,
        status: int,
        body: object,
        prepared: PreparedJourney,
        *,
        locate: bool = False,
    ) -> JourneyFailure:
        code = body.get("error_code") if isinstance(body, Mapping) else None
        message = str(body.get("error", "")) if isinstance(body, Mapping) else ""
        if locate or code in {171} or "No data found" in message:
            return JourneyFailure(
                FailureCode.ABSENT_COVERAGE,
                "The local walking graph has no usable coverage near an endpoint.",
                details={"provider_status": status, "provider_code": code},
            )
        if code in {170, 441, 442, 443}:
            return JourneyFailure(
                FailureCode.NO_ROUTE,
                "No connected walking path was found between the covered endpoints.",
                details={"provider_status": status, "provider_code": code},
            )
        if code == 154:
            related = tuple(profile.profile_key for profile in prepared.profiles)
            if any(
                "maximum_contiguous_distance_metres" in profile.definition
                for profile in prepared.profiles
            ):
                return JourneyFailure(
                    FailureCode.PROFILE_LIMIT_EXCEEDED,
                    "The requested walking distance exceeds the selected profile limit.",
                    related_keys=related,
                )
            return JourneyFailure(
                FailureCode.UNSUPPORTED_REQUIREMENT,
                "The walking request exceeds the reviewed provider search bound.",
                related_keys=("provider-distance-bound",),
            )
        if status >= 500:
            return JourneyFailure(
                FailureCode.PROVIDER_FAILURE,
                "The local walking provider failed while calculating the route.",
                details={"provider_status": status, "provider_code": code},
            )
        return JourneyFailure(
            FailureCode.INCOMPATIBLE_DATA,
            "The local walking provider rejected an adapter request it should support.",
            details={"provider_status": status, "provider_code": code},
        )

    @contextmanager
    def _provider_session(self) -> Iterator[None]:
        if self._transport is not None:
            yield
            return
        with _RUNTIME_LOCK:
            if self._provider_is_listening():
                yield
                return
            verify_local_valhalla_resources(self.capability)
            process = subprocess.Popen(
                [
                    str(self.capability.service_binary),
                    str(self.capability.service_config),
                    "1",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("Valhalla exited before its loopback service was ready.")
                    if self._provider_is_listening():
                        break
                    time.sleep(0.025)
                else:
                    raise TimeoutError("Valhalla did not become ready within five seconds.")
                yield
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)

    def _provider_is_listening(self) -> bool:
        try:
            status, _body = self._request_json("/status", None, timeout=0.25)
            return 200 <= status < 300
        except (OSError, TimeoutError):
            return False

    def _request_json(
        self,
        path: str,
        payload: Mapping[str, object] | None,
        *,
        timeout: float = 10,
    ) -> tuple[int, object]:
        if self._transport is not None:
            return self._transport(path, payload)
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.capability.base_url}{path}",
            data=data,
            headers={
                "Accept": "application/json",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            try:
                return error.code, json.loads(error.read())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return error.code, {"error": "non_json_provider_error"}
        except URLError as error:
            raise OSError(str(error.reason)) from error

    def _normalise_clock(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Adapter clock must include a timezone.")
        return value.astimezone(UTC)


def _decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    coordinates: list[tuple[float, float]] = []
    previous = [0, 0]
    index = 0
    while index < len(encoded):
        values = [0, 0]
        for coordinate_index in (0, 1):
            shift = 0
            result = 0
            while True:
                if index >= len(encoded):
                    raise ValueError("Encoded route shape ended unexpectedly.")
                byte = ord(encoded[index]) - 63
                index += 1
                if byte < 0:
                    raise ValueError("Encoded route shape contains an invalid byte.")
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
                if shift > 60:
                    raise ValueError("Encoded route shape is invalid.")
            delta = ~(result >> 1) if result & 1 else result >> 1
            previous[coordinate_index] += delta
            values[coordinate_index] = previous[coordinate_index]
        latitude, longitude = (value / 1_000_000 for value in values)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Decoded route shape is outside WGS84 bounds.")
        coordinates.append((longitude, latitude))
    return coordinates


def _haversine_metres(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
    radius = 6_371_008.8
    latitude_a_rad = math.radians(latitude_a)
    latitude_b_rad = math.radians(latitude_b)
    latitude_delta = latitude_b_rad - latitude_a_rad
    longitude_delta = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_rad)
        * math.cos(latitude_b_rad)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * radius * math.asin(min(1, math.sqrt(value)))


def _provider_warning_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("description") or value.get("text") or "").strip()
    return ""


def _duration_label(seconds: int) -> str:
    minutes = max(0, int(round(seconds / 60)))
    hours, remaining = divmod(minutes, 60)
    if hours and remaining:
        return f"{hours} h {remaining} min"
    if hours:
        return f"{hours} h"
    return f"{remaining} min"
