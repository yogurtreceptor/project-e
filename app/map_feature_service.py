"""Reviewed provider-feature promotion and portable Map-list membership."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app.audit import record_audit_event
from app.db_support import utc_now
from app.duplicate_detection import find_duplicate_entities
from app.entities import DEFINITIONS_BY_SLUG, EntityRecord
from app.entity_repository import get_entity, validate_entity_values
from app.entity_service import create_entity
from app.place_repository import create_location_provider_reference
from app.spatial_pack import read_active_search_feature, spatial_pack_status


MAX_LIST_NAME = 80
MAX_PROVIDER_KEY = 160
MAX_FEATURE_ID = 512
MAX_FEATURE_LABEL = 300
NEARBY_DUPLICATE_METRES = 100.0


@dataclass(frozen=True)
class ProviderFeatureSnapshot:
    provider_key: str
    feature_id: str
    feature_version: str
    title: str
    description: str
    feature_type: str
    source_name: str
    source_layer: str
    latitude: float
    longitude: float
    geometry_confidence: str = "Source reported"
    formatted_address: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    suburb: str = ""
    city: str = ""
    state: str = ""
    post_code: str = ""
    country: str = ""

    def form_values(self) -> dict[str, str]:
        return {
            "provider_key": self.provider_key,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "title": self.title,
            "description": self.description,
            "feature_type": self.feature_type,
            "source_name": self.source_name,
            "source_layer": self.source_layer,
            "latitude": _coordinate_text(self.latitude),
            "longitude": _coordinate_text(self.longitude),
            "geometry_confidence": self.geometry_confidence,
            "formatted_address": self.formatted_address,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "suburb": self.suburb,
            "city": self.city,
            "state": self.state,
            "post_code": self.post_code,
            "country": self.country,
        }


@dataclass(frozen=True)
class ProviderPromotionMatch:
    record: EntityRecord
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class MapFeatureList:
    id: int
    list_key: str
    name: str
    kind: str
    created_at: str
    updated_at: str
    member_count: int = 0


@dataclass(frozen=True)
class MapFeatureMembership:
    id: int
    list_id: int
    provider_key: str
    feature_id: str
    user_label: str
    added_at: str


def provider_feature_from_form(
    values: Mapping[str, str], spatial_pack_root: Path
) -> ProviderFeatureSnapshot:
    provider_key = _required_text(
        values.get("provider_key", ""), "Provider identity", MAX_PROVIDER_KEY
    )
    feature_id = _required_text(
        values.get("feature_id", ""), "Provider feature identity", MAX_FEATURE_ID
    )
    feature_version = _text(values.get("feature_version", ""), 200)
    title = _required_text(values.get("title", ""), "Provider feature name", MAX_FEATURE_LABEL)
    description = _text(values.get("description", ""), 500)
    feature_type = _text(values.get("feature_type", ""), 160) or "Place"
    source_name = _required_text(values.get("source_name", ""), "Provider source", 240)
    source_layer = _text(values.get("source_layer", ""), 160)
    latitude = _coordinate(values.get("latitude", ""), "Latitude", -90, 90)
    longitude = _coordinate(values.get("longitude", ""), "Longitude", -180, 180)
    geometry_confidence = "Source reported"

    if provider_key == "nominatim-osm":
        if feature_version:
            raise ValueError("The Nominatim result has an unsupported version identity.")
        source_name = "OpenStreetMap Nominatim"
        source_layer = "nominatim"
    elif provider_key.startswith("spatial-pack:"):
        pack_id = provider_key.removeprefix("spatial-pack:")
        status = spatial_pack_status(spatial_pack_root)
        if status.active is None:
            raise ValueError("The provider feature's spatial pack is no longer active.")
        manifest = status.active.manifest
        if pack_id != manifest.pack_id or feature_version != manifest.pack_version:
            raise ValueError(
                "The provider feature belongs to a spatial-pack version that is no longer active."
            )
        west, south, east, north = manifest.coverage_bbox
        if not (west <= longitude <= east and south <= latitude <= north):
            raise ValueError("The provider feature lies outside its declared pack coverage.")
        source_name = f"{manifest.title} {manifest.pack_version} · Local"
        current = read_active_search_feature(
            spatial_pack_root, provider_key, feature_id
        )
        if current is not None:
            title = str(current["title"])
            description = str(current["subtitle"])
            feature_type = str(current["feature_type"])
            source_layer = str(current["source_layer"])
            latitude = float(current["latitude"])
            longitude = float(current["longitude"])
        else:
            geometry_confidence = "Approximate"
    else:
        raise ValueError("The provider feature source is not supported for reviewed saving.")

    address_values = {
        key: _text(values.get(key, ""), 500)
        for key in (
            "formatted_address",
            "address_line_1",
            "address_line_2",
            "suburb",
            "city",
            "state",
            "post_code",
            "country",
        )
    }
    if provider_key.startswith("spatial-pack:"):
        address_values = {key: "" for key in address_values}
    return ProviderFeatureSnapshot(
        provider_key=provider_key,
        feature_id=feature_id,
        feature_version=feature_version,
        title=title,
        description=description,
        feature_type=feature_type,
        source_name=source_name,
        source_layer=source_layer,
        latitude=latitude,
        longitude=longitude,
        geometry_confidence=geometry_confidence,
        **address_values,
    )


def find_provider_promotion_matches(
    connection: sqlite3.Connection, feature: ProviderFeatureSnapshot
) -> list[ProviderPromotionMatch]:
    definition = DEFINITIONS_BY_SLUG["locations"]
    reasons_by_id: dict[int, list[str]] = {}
    records_by_id: dict[int, EntityRecord] = {}

    rows = connection.execute(
        """SELECT DISTINCT location_entity_id, feature_version
             FROM location_provider_references
            WHERE provider_key=? AND feature_id=?
            ORDER BY location_entity_id, feature_version""",
        (feature.provider_key, feature.feature_id),
    ).fetchall()
    for row in rows:
        record = get_entity(connection, definition, int(row["location_entity_id"]))
        if record is None:
            continue
        records_by_id[record.id] = record
        reason = "Accepted provider reference"
        if row["feature_version"]:
            reason += f" ({row['feature_version']})"
        reasons_by_id.setdefault(record.id, []).append(reason)

    values = {
        "display_name": feature.title,
        "formatted_address": feature.formatted_address,
    }
    for duplicate in find_duplicate_entities(connection, definition, values, limit=20):
        records_by_id[duplicate.record.id] = duplicate.record
        reasons_by_id.setdefault(duplicate.record.id, []).extend(
            f"Matching {field.lower()}" for field in duplicate.matched_fields
        )

    for row in connection.execute(
        """SELECT location_entity_id, coordinates_json
             FROM location_geometries
            WHERE geometry_type='Point' AND role='representative_point'
              AND is_current=1
              AND id=(
                  SELECT candidate.id FROM location_geometries candidate
                   WHERE candidate.location_entity_id=location_geometries.location_entity_id
                     AND candidate.geometry_type='Point'
                     AND candidate.role='representative_point'
                     AND candidate.is_current=1
                   ORDER BY candidate.is_preferred DESC, candidate.id DESC
                   LIMIT 1
              )
            ORDER BY location_entity_id"""
    ):
        try:
            longitude, latitude = json.loads(row["coordinates_json"])
            distance = _haversine_metres(
                feature.latitude, feature.longitude, float(latitude), float(longitude)
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if distance > NEARBY_DUPLICATE_METRES:
            continue
        entity_id = int(row["location_entity_id"])
        record = records_by_id.get(entity_id) or get_entity(
            connection, definition, entity_id
        )
        if record is None:
            continue
        records_by_id[entity_id] = record
        reasons_by_id.setdefault(entity_id, []).append(
            f"Representative point within {max(1, round(distance))} m"
        )

    return [
        ProviderPromotionMatch(
            records_by_id[entity_id], tuple(dict.fromkeys(reasons_by_id[entity_id]))
        )
        for entity_id in sorted(
            records_by_id,
            key=lambda item: (records_by_id[item].title.casefold(), item),
        )
    ]


def promote_provider_feature(
    connection: sqlite3.Connection,
    feature: ProviderFeatureSnapshot,
    *,
    choice: str,
    display_name: str,
) -> tuple[int, bool]:
    matches = find_provider_promotion_matches(connection, feature)
    if choice == "new":
        location_id = _create_location_from_provider(
            connection, feature, display_name.strip()
        )
        return location_id, True
    if not choice.isdecimal():
        raise ValueError("Choose whether to create a new Location or use a reviewed match.")
    location_id = int(choice)
    if location_id not in {match.record.id for match in matches}:
        raise ValueError("The selected canonical Location is not a current reviewed match.")
    if connection.execute(
        """SELECT 1 FROM location_provider_references
            WHERE location_entity_id=? AND provider_key=? AND feature_id=?
              AND feature_version=?""",
        (
            location_id,
            feature.provider_key,
            feature.feature_id,
            feature.feature_version,
        ),
    ).fetchone():
        return location_id, False
    create_location_provider_reference(
        connection,
        location_id,
        feature.provider_key,
        feature.feature_id,
        feature_version=feature.feature_version,
        observed_at=utc_now(),
        commit=False,
    )
    connection.commit()
    return location_id, False


def list_map_feature_lists(connection: sqlite3.Connection) -> list[MapFeatureList]:
    rows = connection.execute(
        """SELECT map_feature_lists.*, COUNT(membership.id) AS member_count
             FROM map_feature_lists
             LEFT JOIN map_feature_list_memberships membership
               ON membership.list_id=map_feature_lists.id
            GROUP BY map_feature_lists.id
            ORDER BY CASE map_feature_lists.kind WHEN 'favourites' THEN 0 ELSE 1 END,
                     lower(map_feature_lists.name), map_feature_lists.id"""
    )
    return [_list_from_row(row) for row in rows]


def get_map_feature_list(
    connection: sqlite3.Connection, list_id: int
) -> MapFeatureList | None:
    row = connection.execute(
        """SELECT map_feature_lists.*, COUNT(membership.id) AS member_count
             FROM map_feature_lists
             LEFT JOIN map_feature_list_memberships membership
               ON membership.list_id=map_feature_lists.id
            WHERE map_feature_lists.id=?
            GROUP BY map_feature_lists.id""",
        (list_id,),
    ).fetchone()
    return _list_from_row(row) if row else None


def create_map_feature_list(connection: sqlite3.Connection, name: str) -> int:
    name = _required_text(name, "List name", MAX_LIST_NAME)
    now = utc_now()
    try:
        cursor = connection.execute(
            """INSERT INTO map_feature_lists (
                   list_key, name, kind, created_at, updated_at
               ) VALUES (?, ?, 'named', ?, ?)""",
            (f"list:{uuid.uuid4().hex}", name, now, now),
        )
    except sqlite3.IntegrityError as error:
        raise ValueError("A Map list with that name already exists.") from error
    list_id = int(cursor.lastrowid)
    record_audit_event(
        connection,
        "create",
        [("map_feature_list", list_id)],
        after={"name": name, "kind": "named"},
        notes="Portable Map feature list created",
    )
    connection.commit()
    return list_id


def list_map_feature_memberships(
    connection: sqlite3.Connection, list_id: int
) -> list[MapFeatureMembership]:
    return [
        _membership_from_row(row)
        for row in connection.execute(
            """SELECT * FROM map_feature_list_memberships
                WHERE list_id=? ORDER BY lower(user_label), provider_key, feature_id, id""",
            (list_id,),
        )
    ]


def add_map_feature_membership(
    connection: sqlite3.Connection,
    list_id: int,
    feature: ProviderFeatureSnapshot,
) -> tuple[int, bool]:
    feature_list = get_map_feature_list(connection, list_id)
    if feature_list is None:
        raise ValueError("The selected Map list no longer exists.")
    existing = connection.execute(
        """SELECT id FROM map_feature_list_memberships
            WHERE list_id=? AND provider_key=? AND feature_id=?""",
        (list_id, feature.provider_key, feature.feature_id),
    ).fetchone()
    if existing:
        return int(existing["id"]), False
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO map_feature_list_memberships (
               list_id, provider_key, feature_id, user_label, added_at
           ) VALUES (?, ?, ?, ?, ?)""",
        (
            list_id,
            feature.provider_key,
            feature.feature_id,
            feature.title,
            now,
        ),
    )
    membership_id = int(cursor.lastrowid)
    connection.execute(
        "UPDATE map_feature_lists SET updated_at=? WHERE id=?", (now, list_id)
    )
    record_audit_event(
        connection,
        "create",
        [("map_feature_list_membership", membership_id), ("map_feature_list", list_id)],
        after={
            "provider_key": feature.provider_key,
            "feature_id": feature.feature_id,
            "user_label": feature.title,
        },
        notes="External provider feature added to portable Map list",
        provenance="user_confirmed",
    )
    connection.commit()
    return membership_id, True


def remove_map_feature_membership(
    connection: sqlite3.Connection, list_id: int, membership_id: int
) -> bool:
    row = connection.execute(
        """SELECT * FROM map_feature_list_memberships
            WHERE id=? AND list_id=?""",
        (membership_id, list_id),
    ).fetchone()
    if row is None:
        return False
    connection.execute(
        "DELETE FROM map_feature_list_memberships WHERE id=?", (membership_id,)
    )
    connection.execute(
        "UPDATE map_feature_lists SET updated_at=? WHERE id=?", (utc_now(), list_id)
    )
    record_audit_event(
        connection,
        "delete",
        [("map_feature_list_membership", membership_id), ("map_feature_list", list_id)],
        before={
            "provider_key": row["provider_key"],
            "feature_id": row["feature_id"],
            "user_label": row["user_label"],
        },
        notes="External provider feature removed from Map list",
        provenance="user_confirmed",
    )
    connection.commit()
    return True


def clear_map_feature_list(connection: sqlite3.Connection, list_id: int) -> int:
    feature_list = get_map_feature_list(connection, list_id)
    if feature_list is None:
        raise ValueError("The Map list no longer exists.")
    memberships = list_map_feature_memberships(connection, list_id)
    count = len(memberships)
    connection.execute(
        "DELETE FROM map_feature_list_memberships WHERE list_id=?", (list_id,)
    )
    connection.execute(
        "UPDATE map_feature_lists SET updated_at=? WHERE id=?", (utc_now(), list_id)
    )
    if count:
        record_audit_event(
            connection,
            "edit",
            [("map_feature_list", list_id)],
            before={
                "memberships": [
                    {
                        "provider_key": item.provider_key,
                        "feature_id": item.feature_id,
                        "user_label": item.user_label,
                    }
                    for item in memberships
                ]
            },
            after={"member_count": 0},
            notes="Portable Map feature list cleared",
            provenance="user_confirmed",
        )
    connection.commit()
    return count


def map_feature_membership_export(
    feature_list: MapFeatureList, memberships: list[MapFeatureMembership]
) -> dict[str, object]:
    return {
        "format": "project-e-map-feature-list",
        "version": 1,
        "list": {
            "list_key": feature_list.list_key,
            "name": feature_list.name,
            "kind": feature_list.kind,
        },
        "memberships": [
            {
                "provider_key": item.provider_key,
                "feature_id": item.feature_id,
                "user_label": item.user_label,
                "added_at": item.added_at,
            }
            for item in memberships
        ],
    }


def validate_stored_map_feature_lists(connection: sqlite3.Connection) -> list[str]:
    errors = []
    favourites = connection.execute(
        """SELECT id, list_key, name FROM map_feature_lists
            WHERE kind='favourites' ORDER BY id"""
    ).fetchall()
    if len(favourites) != 1:
        errors.append("Map lists require exactly one Favourites list.")
    elif favourites[0]["list_key"] != "favourites" or favourites[0]["name"] != "Favourites":
        errors.append("The Favourites Map list identity is invalid.")
    for row in connection.execute(
        "SELECT id, list_key, name, kind FROM map_feature_lists ORDER BY id"
    ):
        if not row["list_key"].strip() or len(row["list_key"]) > 160:
            errors.append(f"Map list {row['id']} has an invalid identity.")
        if not row["name"].strip() or len(row["name"]) > MAX_LIST_NAME:
            errors.append(f"Map list {row['id']} has an invalid name.")
    for row in connection.execute(
        """SELECT id, provider_key, feature_id, user_label
             FROM map_feature_list_memberships ORDER BY id"""
    ):
        if not row["provider_key"].strip() or len(row["provider_key"]) > MAX_PROVIDER_KEY:
            errors.append(f"Map-list membership {row['id']} has an invalid provider.")
        if not row["feature_id"].strip() or len(row["feature_id"]) > MAX_FEATURE_ID:
            errors.append(f"Map-list membership {row['id']} has an invalid feature identity.")
        if not row["user_label"].strip() or len(row["user_label"]) > MAX_FEATURE_LABEL:
            errors.append(f"Map-list membership {row['id']} has an invalid user label.")
    return errors


def _create_location_from_provider(
    connection: sqlite3.Connection,
    feature: ProviderFeatureSnapshot,
    display_name: str,
) -> int:
    values = {
        "display_name": display_name,
        "formatted_address": feature.formatted_address,
        "address_line_1": feature.address_line_1,
        "address_line_2": feature.address_line_2,
        "suburb": feature.suburb,
        "city": feature.city,
        "state": feature.state,
        "post_code": feature.post_code,
        "country": feature.country,
        "address_confidence": "Source reported",
        "address_source_name": feature.source_name,
        "address_source_reference": feature.feature_id,
        "address_source_version": feature.feature_version,
        "latitude": _coordinate_text(feature.latitude),
        "longitude": _coordinate_text(feature.longitude),
        "geometry_confidence": feature.geometry_confidence,
        "geometry_source_name": feature.source_name,
        "geometry_source_reference": feature.feature_id,
        "geometry_source_version": feature.feature_version,
    }
    definition = DEFINITIONS_BY_SLUG["locations"]
    errors = validate_entity_values(definition, values, connection)
    if errors:
        raise ValueError(" ".join(errors))
    try:
        location_id = create_entity(connection, definition, values, commit=False)
        create_location_provider_reference(
            connection,
            location_id,
            feature.provider_key,
            feature.feature_id,
            feature_version=feature.feature_version,
            observed_at=utc_now(),
            commit=False,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return location_id


def _list_from_row(row: sqlite3.Row) -> MapFeatureList:
    return MapFeatureList(
        id=int(row["id"]),
        list_key=row["list_key"],
        name=row["name"],
        kind=row["kind"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        member_count=int(row["member_count"]),
    )


def _membership_from_row(row: sqlite3.Row) -> MapFeatureMembership:
    return MapFeatureMembership(
        id=int(row["id"]),
        list_id=int(row["list_id"]),
        provider_key=row["provider_key"],
        feature_id=row["feature_id"],
        user_label=row["user_label"],
        added_at=row["added_at"],
    )


def _text(value: str, maximum: int) -> str:
    value = " ".join(str(value).strip().split())
    if len(value) > maximum:
        raise ValueError("Provider feature text exceeds the supported length.")
    return value


def _required_text(value: str, label: str, maximum: int) -> str:
    value = _text(value, maximum)
    if not value:
        raise ValueError(f"{label} is required.")
    return value


def _coordinate(value: str, label: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is invalid.") from error
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{label} is invalid.")
    return number


def _coordinate_text(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _haversine_metres(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    radius = 6_371_000.0
    first_latitude_radians = math.radians(first_latitude)
    second_latitude_radians = math.radians(second_latitude)
    latitude_delta = math.radians(second_latitude - first_latitude)
    longitude_delta = math.radians(second_longitude - first_longitude)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_latitude_radians)
        * math.cos(second_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
