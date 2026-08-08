"""Walking-journey form, endpoint and reviewed profile behaviour."""

from __future__ import annotations

import json
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from app.defaults import PLATFORM_TIMEZONE
from app.journey_contract import (
    EndpointReference,
    JourneyBuffer,
    JourneyMode,
    JourneyRequest,
    JourneyTime,
    JourneyTimeKind,
    MobilityProfile,
    PolicyKind,
    RoutingPolicy,
)
from app.journey_repository import (
    create_mobility_profile,
    create_routing_policy,
    get_mobility_profile,
    get_routing_policy,
    update_mobility_profile,
    update_routing_policy,
)


WALK_PRESETS = {
    "regular-walk": ("Regular walk", "regular"),
    "fast-walk": ("Fast walk / jog", "fast"),
    "run": ("Run", "run"),
}
WALK_PRESET_ORDER = tuple(WALK_PRESETS)
AVOID_STEPS_POLICY_KEY = "avoid-steps"
AVOID_STEPS_POLICY_DEFINITION = {
    "modes": ["walk"],
    "attribute": "steps",
    "strength": "strong",
}


@dataclass(frozen=True)
class JourneyEndpointOption:
    value: str
    location_id: int
    geometry_id: int
    label: str
    longitude: float
    latitude: float


@dataclass(frozen=True)
class WalkProfileReview:
    profile_key: str
    display_name: str
    definition: dict[str, object]
    speed_metres_per_second: float
    pace_seconds_per_kilometre: int
    form_values: dict[str, str]


def list_journey_endpoint_options(
    connection: sqlite3.Connection,
) -> list[JourneyEndpointOption]:
    rows = connection.execute(
        """SELECT entities.id AS location_id, entities.display_name,
                  geometry.id AS geometry_id, geometry.role,
                  geometry.coordinates_json, geometry.is_preferred
           FROM entities
           JOIN location_geometries AS geometry
             ON geometry.location_entity_id = entities.id
           WHERE entities.type='location' AND entities.deleted_at=''
             AND geometry.geometry_type='Point' AND geometry.is_current=1
             AND geometry.role IN ('route_anchor', 'entrance', 'representative_point')
           ORDER BY lower(entities.display_name), entities.id,
                    CASE geometry.role
                      WHEN 'route_anchor' THEN 0
                      WHEN 'entrance' THEN 1
                      ELSE 2
                    END,
                    geometry.is_preferred DESC, geometry.id"""
    ).fetchall()
    counts: dict[tuple[int, str], int] = {}
    for row in rows:
        key = (int(row["location_id"]), row["role"])
        counts[key] = counts.get(key, 0) + 1
    result = []
    for row in rows:
        longitude, latitude = json.loads(row["coordinates_json"])
        role = str(row["role"]).replace("_", " ")
        suffix = (
            f" · {role} #{row['geometry_id']}"
            if counts[(int(row["location_id"]), row["role"])] > 1
            else f" · {role}"
        )
        result.append(
            JourneyEndpointOption(
                value=f"{row['location_id']}:{row['geometry_id']}",
                location_id=int(row["location_id"]),
                geometry_id=int(row["geometry_id"]),
                label=f"{row['display_name']}{suffix}",
                longitude=float(longitude),
                latitude=float(latitude),
            )
        )
    return result


def walking_request_from_form(values: dict[str, str]) -> JourneyRequest:
    origin = _endpoint_reference(values.get("origin", ""), "Origin")
    destination = _endpoint_reference(values.get("destination", ""), "Destination")
    if origin == destination:
        raise ValueError("Choose different origin and destination access points.")
    try:
        time_kind = JourneyTimeKind(values.get("time_kind", "depart_at"))
    except ValueError as error:
        raise ValueError("Choose whether to depart at or arrive by the entered time.") from error
    raw_time = values.get("journey_time", "").strip()
    try:
        local_time = datetime.fromisoformat(raw_time)
    except ValueError as error:
        raise ValueError("Enter a valid local journey date and time.") from error
    if local_time.tzinfo is None:
        local_time = local_time.replace(tzinfo=ZoneInfo(PLATFORM_TIMEZONE))
    profile_key = values.get("profile_key", "").strip()
    if profile_key not in WALK_PRESETS:
        raise ValueError("Choose one reviewed Regular, Fast or Run profile.")
    policy_keys = tuple(
        key.strip()
        for key in values.get("policy_keys", "").split(",")
        if key.strip()
    )
    if len(policy_keys) != len(set(policy_keys)):
        raise ValueError("A walking policy was selected more than once.")
    preparation = _bounded_minutes(
        values.get("preparation_minutes", "0"), "Preparation buffer"
    )
    arrival = _bounded_minutes(
        values.get("arrival_minutes", "0"), "Arrival buffer"
    )
    try:
        alternatives = int(values.get("alternatives", "1"))
    except ValueError as error:
        raise ValueError("Walking alternatives must be 1, 2 or 3.") from error
    if alternatives not in {1, 2, 3}:
        raise ValueError("Walking alternatives must be 1, 2 or 3.")
    return JourneyRequest(
        origin=origin,
        destination=destination,
        mode=JourneyMode.WALK,
        access_modes=(),
        time=JourneyTime(time_kind, local_time.isoformat()),
        profile_keys=(profile_key,),
        policy_keys=policy_keys,
        buffers=(
            JourneyBuffer("preparation", "Preparation", preparation * 60),
            JourneyBuffer("arrival", "Arrival", arrival * 60),
        ),
        requested_alternatives=alternatives,
        require_geometry=True,
        require_complete_coverage=False,
        required_features=(),
    )


def default_walking_form_values(now: datetime | None = None) -> dict[str, str]:
    zone = ZoneInfo(PLATFORM_TIMEZONE)
    current = (now or datetime.now(zone)).astimezone(zone)
    rounded = (current + timedelta(minutes=15)).replace(
        minute=((current.minute + 15) // 15 * 15) % 60,
        second=0,
        microsecond=0,
    )
    if rounded <= current:
        rounded += timedelta(minutes=15)
    return {
        "origin": "",
        "destination": "",
        "time_kind": "depart_at",
        "journey_time": rounded.strftime("%Y-%m-%dT%H:%M"),
        "profile_key": "regular-walk",
        "policy_keys": "",
        "preparation_minutes": "0",
        "arrival_minutes": "0",
        "alternatives": "1",
    }


def review_walk_profile_measurements(values: dict[str, str]) -> WalkProfileReview:
    profile_key = values.get("profile_key", "").strip()
    if profile_key not in WALK_PRESETS:
        raise ValueError("Choose a recognised walking preset.")
    display_name, preset_kind = WALK_PRESETS[profile_key]
    distance = _bounded_decimal(
        values.get("distance_metres", ""),
        "Measured distance",
        Decimal("10"),
        Decimal("100000"),
    )
    trial_seconds = tuple(
        _measurement_duration(values.get(f"trial_{index}", ""), f"Trial {index}")
        for index in range(1, 4)
    )
    measured_on = values.get("measured_on", "").strip()
    try:
        effective_date = date.fromisoformat(measured_on)
    except ValueError as error:
        raise ValueError("Measurement date must be a valid date.") from error
    if effective_date > datetime.now(ZoneInfo(PLATFORM_TIMEZONE)).date():
        raise ValueError("Measurement date cannot be in the future.")
    course_note = values.get("course_note", "").strip()
    if len(course_note) > 200:
        raise ValueError("Measurement note must be 200 characters or fewer.")
    speeds = [float(distance) / seconds for seconds in trial_seconds]
    speed = round(statistics.median(speeds), 6)
    if not 0.5 / 3.6 <= speed <= 25 / 3.6:
        raise ValueError(
            "Measured speed falls outside the reviewed Valhalla walking range of 0.5–25 km/h."
        )
    maximum_distance = _optional_positive_decimal(
        values.get("maximum_distance_metres", ""), "Maximum contiguous distance"
    )
    maximum_duration = _optional_positive_decimal(
        values.get("maximum_duration_minutes", ""), "Maximum contiguous duration"
    )
    definition: dict[str, object] = {
        "preset_kind": preset_kind,
        "speed_metres_per_second": speed,
        "speed_unit": "metres_per_second",
        "source": "repeated_user_measurement",
        "measurement_effective_date": effective_date.isoformat(),
        "measurement_trials": [
            {
                "distance_metres": float(distance),
                "duration_seconds": seconds,
            }
            for seconds in trial_seconds
        ],
    }
    if course_note:
        definition["measurement_note"] = course_note
    if maximum_distance is not None:
        definition["maximum_contiguous_distance_metres"] = float(maximum_distance)
    if maximum_duration is not None:
        definition["maximum_contiguous_duration_seconds"] = int(
            maximum_duration * 60
        )
    normalised_values = dict(values)
    normalised_values.update(
        {
            "profile_key": profile_key,
            "distance_metres": _decimal_text(distance),
            "measured_on": effective_date.isoformat(),
            "trial_1": str(trial_seconds[0]),
            "trial_2": str(trial_seconds[1]),
            "trial_3": str(trial_seconds[2]),
            "maximum_distance_metres": (
                _decimal_text(maximum_distance) if maximum_distance is not None else ""
            ),
            "maximum_duration_minutes": (
                _decimal_text(maximum_duration) if maximum_duration is not None else ""
            ),
            "course_note": course_note,
        }
    )
    return WalkProfileReview(
        profile_key=profile_key,
        display_name=display_name,
        definition=definition,
        speed_metres_per_second=speed,
        pace_seconds_per_kilometre=int(round(1000 / speed)),
        form_values=normalised_values,
    )


def save_reviewed_walk_profile(
    connection: sqlite3.Connection,
    review: WalkProfileReview,
) -> MobilityProfile:
    _validate_profile_order(connection, review)
    existing = get_mobility_profile(connection, review.profile_key)
    if existing is None:
        return create_mobility_profile(
            connection,
            review.profile_key,
            review.display_name,
            JourneyMode.WALK,
            review.definition,
        )
    return update_mobility_profile(
        connection,
        review.profile_key,
        display_name=review.display_name,
        primary_mode=JourneyMode.WALK,
        definition=review.definition,
    )


def configure_avoid_steps_policy(
    connection: sqlite3.Connection,
    *,
    enabled: bool,
) -> RoutingPolicy:
    existing = get_routing_policy(connection, AVOID_STEPS_POLICY_KEY)
    if existing is None:
        return create_routing_policy(
            connection,
            AVOID_STEPS_POLICY_KEY,
            "Prefer routes without steps",
            PolicyKind.SOFT_AVOIDANCE,
            AVOID_STEPS_POLICY_DEFINITION,
            is_enabled=enabled,
        )
    if (
        existing.kind != PolicyKind.SOFT_AVOIDANCE
        or dict(existing.definition) != AVOID_STEPS_POLICY_DEFINITION
    ):
        raise ValueError(
            "The existing avoid-steps policy has a custom definition and was not overwritten."
        )
    return update_routing_policy(
        connection,
        existing.policy_key,
        display_name=existing.display_name,
        kind=existing.kind,
        definition=existing.definition,
        is_enabled=enabled,
    )


def _validate_profile_order(
    connection: sqlite3.Connection,
    review: WalkProfileReview,
) -> None:
    proposed: dict[str, float] = {review.profile_key: review.speed_metres_per_second}
    for profile_key in WALK_PRESET_ORDER:
        if profile_key == review.profile_key:
            continue
        existing = get_mobility_profile(connection, profile_key)
        if existing is None:
            continue
        speed = existing.definition.get("speed_metres_per_second")
        if isinstance(speed, (int, float)) and not isinstance(speed, bool):
            proposed[profile_key] = float(speed)
    previous = None
    for profile_key in WALK_PRESET_ORDER:
        speed = proposed.get(profile_key)
        if speed is None:
            continue
        if previous is not None and speed <= previous:
            raise ValueError(
                "Measured preset speeds must increase from Regular walk to Fast walk / jog to Run."
            )
        previous = speed


def _endpoint_reference(value: str, label: str) -> EndpointReference:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError(f"{label} must be a deliberate canonical Location access point.")
    location_id, geometry_id = (int(part) for part in parts)
    if location_id <= 0 or geometry_id <= 0:
        raise ValueError(f"{label} must be a deliberate canonical Location access point.")
    return EndpointReference(location_id, geometry_id)


def _bounded_minutes(value: str, label: str) -> int:
    try:
        minutes = int(value)
    except ValueError as error:
        raise ValueError(f"{label} must be whole minutes from 0 to 240.") from error
    if not 0 <= minutes <= 240:
        raise ValueError(f"{label} must be whole minutes from 0 to 240.")
    return minutes


def _measurement_duration(value: str, label: str) -> int:
    text = value.strip()
    try:
        if ":" in text:
            minutes_text, seconds_text = text.split(":", 1)
            minutes = int(minutes_text)
            seconds = int(seconds_text)
            if minutes < 0 or not 0 <= seconds < 60:
                raise ValueError
            total = minutes * 60 + seconds
        else:
            total = int(text)
    except ValueError as error:
        raise ValueError(f"{label} must use seconds or minutes:seconds.") from error
    if not 1 <= total <= 86_400:
        raise ValueError(f"{label} must be between 1 second and 24 hours.")
    return total


def _bounded_decimal(
    value: str,
    label: str,
    minimum: Decimal,
    maximum: Decimal,
) -> Decimal:
    try:
        number = Decimal(value.strip())
    except InvalidOperation as error:
        raise ValueError(f"{label} must be a number.") from error
    if not number.is_finite() or not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number


def _optional_positive_decimal(value: str, label: str) -> Decimal | None:
    text = value.strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"{label} must be a positive number when supplied.") from error
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{label} must be a positive number when supplied.")
    return number


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")
