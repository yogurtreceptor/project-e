"""Walking-journey form, endpoint and provisional profile behaviour."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
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
    update_routing_policy,
)


WALK_PRESETS = {
    "regular-walk": ("Regular walk", "regular"),
    "fast-walk": ("Fast walk / jog", "fast"),
    "run": ("Run", "run"),
}
REGULAR_WALK_PROFILE_KEY = "regular-walk"
GENERIC_WALK_SPEED_KILOMETRES_PER_HOUR = 5.0
GENERIC_WALK_SPEED_METRES_PER_SECOND = round(
    GENERIC_WALK_SPEED_KILOMETRES_PER_HOUR / 3.6, 6
)
GENERIC_WALK_PROFILE_DEFINITION = {
    "preset_kind": "regular",
    "speed_metres_per_second": GENERIC_WALK_SPEED_METRES_PER_SECOND,
    "speed_unit": "metres_per_second",
    "source": "provisional_generic_reference",
    "source_label": "Google Maps Community Product Expert estimate",
    "source_url": (
        "https://support.google.com/maps/thread/246904678/"
        "qual-crit%C3%A9rio-o-google-maps-usa-para-trajetos-%C3%A0-p%C3%A9"
    ),
    "source_checked_on": "2026-08-08",
    "source_speed_kilometres_per_hour": GENERIC_WALK_SPEED_KILOMETRES_PER_HOUR,
    "provisional": True,
}
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
    if profile_key != REGULAR_WALK_PROFILE_KEY:
        raise ValueError(
            "Only Regular walk is available for now; Jog and Run are not enabled."
        )
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


def ensure_default_walk_profile(
    connection: sqlite3.Connection,
) -> MobilityProfile:
    """Create the provisional generic Regular walk profile once, without overwrite."""
    existing = get_mobility_profile(connection, REGULAR_WALK_PROFILE_KEY)
    if existing is not None:
        return existing
    return create_mobility_profile(
        connection,
        REGULAR_WALK_PROFILE_KEY,
        WALK_PRESETS[REGULAR_WALK_PROFILE_KEY][0],
        JourneyMode.WALK,
        GENERIC_WALK_PROFILE_DEFINITION,
        audit_actor="system",
        audit_provenance="source_reported",
        audit_notes="Provisional generic Regular walk profile initialised",
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
