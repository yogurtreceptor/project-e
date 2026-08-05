"""Canonical Location address, geometry, and provider-reference persistence."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from typing import Any, Sequence

from app.audit import record_audit_event, set_provenance
from app.db_support import utc_now


ADDRESS_PURPOSES = ("physical", "postal", "delivery")
GEOMETRY_TYPES = (
    "Point",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
)
GEOMETRY_ROLES = (
    "representative_point",
    "boundary",
    "entrance",
    "route_anchor",
    "path",
)
PLACE_CONFIDENCE_LEVELS = (
    "User confirmed",
    "Source reported",
    "Approximate",
    "Unknown",
)


@dataclass(frozen=True)
class LocationAddress:
    id: int
    location_entity_id: int
    purpose: str
    formatted_address: str
    address_line_1: str
    address_line_2: str
    suburb: str
    city: str
    state: str
    post_code: str
    country: str
    confidence: str
    source_name: str
    source_reference: str
    source_version: str
    is_current: bool
    is_preferred: bool
    created_at: str
    updated_at: str

    @property
    def display_text(self) -> str:
        return self.formatted_address or ", ".join(
            part
            for part in (
                self.address_line_1,
                self.address_line_2,
                self.suburb,
                self.city,
                self.state,
                self.post_code,
                self.country,
            )
            if part
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "purpose": self.purpose,
            "formatted_address": self.formatted_address,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "suburb": self.suburb,
            "city": self.city,
            "state": self.state,
            "post_code": self.post_code,
            "country": self.country,
            "confidence": self.confidence,
            "source_name": self.source_name,
            "source_reference": self.source_reference,
            "source_version": self.source_version,
            "is_current": self.is_current,
            "is_preferred": self.is_preferred,
        }


@dataclass(frozen=True)
class LocationGeometry:
    id: int
    location_entity_id: int
    geometry_type: str
    coordinates: object
    role: str
    confidence: str
    accuracy_radius_metres: float | None
    source_name: str
    source_reference: str
    source_version: str
    is_current: bool
    is_preferred: bool
    created_at: str
    updated_at: str

    @property
    def point(self) -> tuple[float, float] | None:
        if self.geometry_type != "Point" or not isinstance(self.coordinates, list):
            return None
        longitude, latitude = self.coordinates
        return float(latitude), float(longitude)

    def snapshot(self) -> dict[str, object]:
        return {
            "geometry_type": self.geometry_type,
            "coordinates": self.coordinates,
            "role": self.role,
            "confidence": self.confidence,
            "accuracy_radius_metres": self.accuracy_radius_metres,
            "source_name": self.source_name,
            "source_reference": self.source_reference,
            "source_version": self.source_version,
            "is_current": self.is_current,
            "is_preferred": self.is_preferred,
        }


@dataclass(frozen=True)
class LocationProviderReference:
    id: int
    location_entity_id: int
    provider_key: str
    feature_id: str
    feature_version: str
    observed_at: str
    accepted_at: str


@dataclass(frozen=True)
class LocationPlaceContext:
    addresses: tuple[LocationAddress, ...]
    geometries: tuple[LocationGeometry, ...]
    provider_references: tuple[LocationProviderReference, ...]
    preferred_address: LocationAddress | None
    representative_point: LocationGeometry | None
    display_address: LocationAddress | None
    inherited_address_location_id: int | None = None
    inherited_address_location_title: str = ""


def list_location_addresses(
    connection: sqlite3.Connection, location_entity_id: int
) -> list[LocationAddress]:
    rows = connection.execute(
        """SELECT * FROM location_addresses
           WHERE location_entity_id=?
           ORDER BY is_current DESC, is_preferred DESC, purpose, id DESC""",
        (location_entity_id,),
    )
    return [_address_from_row(row) for row in rows]


def preferred_location_address(
    connection: sqlite3.Connection,
    location_entity_id: int,
    purpose: str = "physical",
) -> LocationAddress | None:
    row = connection.execute(
        """SELECT * FROM location_addresses
           WHERE location_entity_id=? AND purpose=? AND is_current=1
           ORDER BY is_preferred DESC, id DESC LIMIT 1""",
        (location_entity_id, purpose),
    ).fetchone()
    return _address_from_row(row) if row else None


def create_location_address(
    connection: sqlite3.Connection,
    location_entity_id: int,
    *,
    purpose: str = "physical",
    formatted_address: str = "",
    address_line_1: str = "",
    address_line_2: str = "",
    suburb: str = "",
    city: str = "",
    state: str = "",
    post_code: str = "",
    country: str = "",
    confidence: str = "Unknown",
    source_name: str = "",
    source_reference: str = "",
    source_version: str = "",
    is_current: bool = True,
    is_preferred: bool = False,
    commit: bool = True,
    audit: bool = True,
) -> int:
    _ensure_location(connection, location_entity_id)
    if purpose not in ADDRESS_PURPOSES:
        raise ValueError("Address purpose is invalid.")
    if confidence not in PLACE_CONFIDENCE_LEVELS:
        raise ValueError("Address confidence is invalid.")
    if is_preferred and not is_current:
        raise ValueError("A preferred address must be current.")
    address_values = (
        formatted_address,
        address_line_1,
        address_line_2,
        suburb,
        city,
        state,
        post_code,
        country,
    )
    if not any(value.strip() for value in address_values):
        raise ValueError("An address assertion must contain an address value.")
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO location_addresses (
               location_entity_id, purpose, formatted_address,
               address_line_1, address_line_2, suburb, city, state,
               post_code, country, confidence, source_name,
               source_reference, source_version, is_current, is_preferred,
               created_at, updated_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            location_entity_id,
            purpose,
            formatted_address.strip(),
            address_line_1.strip(),
            address_line_2.strip(),
            suburb.strip(),
            city.strip(),
            state.strip(),
            post_code.strip(),
            country.strip(),
            confidence,
            source_name.strip(),
            source_reference.strip(),
            source_version.strip(),
            int(is_current),
            int(is_preferred),
            now,
            now,
        ),
    )
    address_id = int(cursor.lastrowid)
    set_provenance(
        connection,
        "location_address",
        address_id,
        "*",
        confidence_provenance(confidence),
    )
    if audit:
        address = get_location_address(connection, address_id)
        record_audit_event(
            connection,
            "create",
            [("location_address", address_id), ("entity", location_entity_id)],
            after=address.snapshot() if address else None,
            notes="Location address assertion created",
            provenance=confidence_provenance(confidence),
        )
    if commit:
        connection.commit()
    return address_id


def get_location_address(
    connection: sqlite3.Connection, address_id: int
) -> LocationAddress | None:
    row = connection.execute(
        "SELECT * FROM location_addresses WHERE id=?", (address_id,)
    ).fetchone()
    return _address_from_row(row) if row else None


def list_location_geometries(
    connection: sqlite3.Connection, location_entity_id: int
) -> list[LocationGeometry]:
    rows = connection.execute(
        """SELECT * FROM location_geometries
           WHERE location_entity_id=?
           ORDER BY is_current DESC, is_preferred DESC, role, id DESC""",
        (location_entity_id,),
    )
    return [_geometry_from_row(row) for row in rows]


def preferred_location_geometry(
    connection: sqlite3.Connection,
    location_entity_id: int,
    role: str = "representative_point",
) -> LocationGeometry | None:
    row = connection.execute(
        """SELECT * FROM location_geometries
           WHERE location_entity_id=? AND role=? AND is_current=1
           ORDER BY is_preferred DESC, id DESC LIMIT 1""",
        (location_entity_id, role),
    ).fetchone()
    return _geometry_from_row(row) if row else None


def create_location_geometry(
    connection: sqlite3.Connection,
    location_entity_id: int,
    geometry_type: str,
    coordinates: object,
    *,
    role: str,
    confidence: str = "Unknown",
    accuracy_radius_metres: float | None = None,
    source_name: str = "",
    source_reference: str = "",
    source_version: str = "",
    is_current: bool = True,
    is_preferred: bool = False,
    commit: bool = True,
    audit: bool = True,
) -> int:
    _ensure_location(connection, location_entity_id)
    if role not in GEOMETRY_ROLES:
        raise ValueError("Geometry role is invalid.")
    if role == "representative_point" and geometry_type != "Point":
        raise ValueError("A representative point must use Point geometry.")
    if confidence not in PLACE_CONFIDENCE_LEVELS:
        raise ValueError("Geometry confidence is invalid.")
    if is_preferred and not is_current:
        raise ValueError("A preferred geometry must be current.")
    if accuracy_radius_metres is not None:
        if not math.isfinite(accuracy_radius_metres) or accuracy_radius_metres <= 0:
            raise ValueError("Accuracy radius must be a positive number.")
    coordinates_json = serialise_geometry_coordinates(geometry_type, coordinates)
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO location_geometries (
               location_entity_id, geometry_type, coordinates_json, role,
               confidence, accuracy_radius_metres, source_name,
               source_reference, source_version, is_current, is_preferred,
               created_at, updated_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            location_entity_id,
            geometry_type,
            coordinates_json,
            role,
            confidence,
            accuracy_radius_metres,
            source_name.strip(),
            source_reference.strip(),
            source_version.strip(),
            int(is_current),
            int(is_preferred),
            now,
            now,
        ),
    )
    geometry_id = int(cursor.lastrowid)
    set_provenance(
        connection,
        "location_geometry",
        geometry_id,
        "*",
        confidence_provenance(confidence),
    )
    if audit:
        geometry = get_location_geometry(connection, geometry_id)
        record_audit_event(
            connection,
            "create",
            [("location_geometry", geometry_id), ("entity", location_entity_id)],
            after=geometry.snapshot() if geometry else None,
            notes="Location geometry assertion created",
            provenance=confidence_provenance(confidence),
        )
    if commit:
        connection.commit()
    return geometry_id


def get_location_geometry(
    connection: sqlite3.Connection, geometry_id: int
) -> LocationGeometry | None:
    row = connection.execute(
        "SELECT * FROM location_geometries WHERE id=?", (geometry_id,)
    ).fetchone()
    return _geometry_from_row(row) if row else None


def list_location_provider_references(
    connection: sqlite3.Connection, location_entity_id: int
) -> list[LocationProviderReference]:
    rows = connection.execute(
        """SELECT * FROM location_provider_references
           WHERE location_entity_id=?
           ORDER BY provider_key, feature_id, feature_version, id""",
        (location_entity_id,),
    )
    return [_provider_reference_from_row(row) for row in rows]


def create_location_provider_reference(
    connection: sqlite3.Connection,
    location_entity_id: int,
    provider_key: str,
    feature_id: str,
    *,
    feature_version: str = "",
    observed_at: str = "",
    commit: bool = True,
) -> int:
    _ensure_location(connection, location_entity_id)
    provider_key = provider_key.strip()
    feature_id = feature_id.strip()
    if not provider_key or not feature_id:
        raise ValueError("Provider and feature identifiers are required.")
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO location_provider_references (
               location_entity_id, provider_key, feature_id, feature_version,
               observed_at, accepted_at
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (
            location_entity_id,
            provider_key,
            feature_id,
            feature_version.strip(),
            observed_at.strip(),
            now,
        ),
    )
    reference_id = int(cursor.lastrowid)
    record_audit_event(
        connection,
        "create",
        [("location_provider_reference", reference_id), ("entity", location_entity_id)],
        after={
            "provider_key": provider_key,
            "feature_id": feature_id,
            "feature_version": feature_version.strip(),
        },
        notes="Provider reference accepted for canonical Location",
        provenance="source_reported",
    )
    if commit:
        connection.commit()
    return reference_id


def delete_location_provider_reference(
    connection: sqlite3.Connection, reference_id: int, *, commit: bool = True
) -> bool:
    row = connection.execute(
        "SELECT * FROM location_provider_references WHERE id=?", (reference_id,)
    ).fetchone()
    if row is None:
        return False
    connection.execute(
        "DELETE FROM location_provider_references WHERE id=?", (reference_id,)
    )
    record_audit_event(
        connection,
        "delete",
        [
            ("location_provider_reference", reference_id),
            ("entity", int(row["location_entity_id"])),
        ],
        before={
            "provider_key": row["provider_key"],
            "feature_id": row["feature_id"],
            "feature_version": row["feature_version"],
        },
        notes="Provider reference removed; canonical place assertions retained",
        provenance="source_reported",
    )
    if commit:
        connection.commit()
    return True


def location_place_context(
    connection: sqlite3.Connection, location_entity_id: int
) -> LocationPlaceContext:
    addresses = tuple(list_location_addresses(connection, location_entity_id))
    geometries = tuple(list_location_geometries(connection, location_entity_id))
    provider_references = tuple(
        list_location_provider_references(connection, location_entity_id)
    )
    preferred_address = next(
        (
            item
            for item in addresses
            if item.purpose == "physical" and item.is_current and item.is_preferred
        ),
        next(
            (
                item
                for item in addresses
                if item.purpose == "physical" and item.is_current
            ),
            None,
        ),
    )
    representative_point = next(
        (
            item
            for item in geometries
            if item.role == "representative_point"
            and item.is_current
            and item.is_preferred
        ),
        next(
            (
                item
                for item in geometries
                if item.role == "representative_point" and item.is_current
            ),
            None,
        ),
    )
    display_address = preferred_address
    inherited_id = None
    inherited_title = ""
    if display_address is None:
        display_address, inherited_id, inherited_title = _inherited_address(
            connection, location_entity_id
        )
    return LocationPlaceContext(
        addresses=addresses,
        geometries=geometries,
        provider_references=provider_references,
        preferred_address=preferred_address,
        representative_point=representative_point,
        display_address=display_address,
        inherited_address_location_id=inherited_id,
        inherited_address_location_title=inherited_title,
    )


def hydrate_location_metadata(connection: sqlite3.Connection, record) -> None:
    context = location_place_context(connection, record.id)
    address = context.preferred_address
    address_fields = (
        "formatted_address",
        "address_line_1",
        "address_line_2",
        "suburb",
        "city",
        "state",
        "post_code",
        "country",
        "address_confidence",
        "address_source_name",
        "address_source_reference",
        "address_source_version",
    )
    for field_name in address_fields:
        record.metadata[field_name] = ""
    if address:
        for field_name in address_fields[:8]:
            record.metadata[field_name] = getattr(address, field_name)
        record.metadata["address_confidence"] = address.confidence
        record.metadata["address_source_name"] = address.source_name
        record.metadata["address_source_reference"] = address.source_reference
        record.metadata["address_source_version"] = address.source_version

    geometry = context.representative_point
    for field_name in (
        "latitude",
        "longitude",
        "geometry_confidence",
        "accuracy_radius_metres",
        "geometry_source_name",
        "geometry_source_reference",
        "geometry_source_version",
    ):
        record.metadata[field_name] = ""
    if geometry and geometry.point:
        latitude, longitude = geometry.point
        record.metadata["latitude"] = _format_coordinate(latitude)
        record.metadata["longitude"] = _format_coordinate(longitude)
        record.metadata["geometry_confidence"] = geometry.confidence
        record.metadata["accuracy_radius_metres"] = (
            ""
            if geometry.accuracy_radius_metres is None
            else _format_coordinate(geometry.accuracy_radius_metres)
        )
        record.metadata["geometry_source_name"] = geometry.source_name
        record.metadata["geometry_source_reference"] = geometry.source_reference
        record.metadata["geometry_source_version"] = geometry.source_version


def serialise_geometry_coordinates(geometry_type: str, coordinates: object) -> str:
    errors = validate_geometry_coordinates(geometry_type, coordinates)
    if errors:
        raise ValueError("; ".join(errors))
    canonical = _canonical_coordinates(coordinates)
    return json.dumps(canonical, separators=(",", ":"), allow_nan=False)


def validate_geometry_coordinates(
    geometry_type: str, coordinates: object
) -> list[str]:
    if geometry_type not in GEOMETRY_TYPES:
        return ["Geometry type is invalid."]
    try:
        if geometry_type == "Point":
            _validate_position(coordinates)
        elif geometry_type == "LineString":
            _validate_line(coordinates)
        elif geometry_type == "MultiLineString":
            _require_sequence(coordinates, "MultiLineString")
            if not coordinates:
                raise ValueError("MultiLineString requires at least one line.")
            for line in coordinates:
                _validate_line(line)
        elif geometry_type == "Polygon":
            _validate_polygon(coordinates)
        elif geometry_type == "MultiPolygon":
            _require_sequence(coordinates, "MultiPolygon")
            if not coordinates:
                raise ValueError("MultiPolygon requires at least one polygon.")
            for polygon in coordinates:
                _validate_polygon(polygon)
    except ValueError as error:
        return [str(error)]
    return []


def validate_stored_place_foundation(connection: sqlite3.Connection) -> list[str]:
    """Validate portable place assertions independently of SQLite triggers."""
    errors: list[str] = []
    location_ids = {
        int(row["id"])
        for row in connection.execute("SELECT id FROM entities WHERE type='location'")
    }
    for table in (
        "location_addresses",
        "location_geometries",
        "location_provider_references",
    ):
        for row in connection.execute(
            f"SELECT id, location_entity_id FROM {table} ORDER BY id"
        ):
            if int(row["location_entity_id"]) not in location_ids:
                errors.append(
                    f"{table} row {row['id']} does not belong to a Location."
                )
    for row in connection.execute(
        """SELECT id, geometry_type, coordinates_json, role
           FROM location_geometries ORDER BY id"""
    ):
        if row["role"] == "representative_point" and row["geometry_type"] != "Point":
            errors.append(
                f"Location geometry {row['id']}: a representative point must use Point geometry."
            )
        try:
            coordinates = json.loads(row["coordinates_json"])
        except json.JSONDecodeError:
            errors.append(f"Location geometry {row['id']} has invalid JSON.")
            continue
        geometry_errors = validate_geometry_coordinates(
            row["geometry_type"], coordinates
        )
        errors.extend(
            f"Location geometry {row['id']}: {error}" for error in geometry_errors
        )

    active_containment = connection.execute(
        """SELECT id, source_entity_id, target_entity_id
           FROM relationships
           WHERE type='contains_location' AND status='active' AND deleted_at=''
           ORDER BY id"""
    ).fetchall()
    parents: dict[int, int] = {}
    children: dict[int, set[int]] = {}
    for row in active_containment:
        source = int(row["source_entity_id"])
        target = int(row["target_entity_id"])
        if source not in location_ids or target not in location_ids:
            errors.append(
                f"Location containment {row['id']} requires two Locations."
            )
        if target in parents:
            errors.append(f"Location {target} has more than one active parent.")
        parents[target] = source
        children.setdefault(source, set()).add(target)
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(location_id: int) -> bool:
        if location_id in visiting:
            return True
        if location_id in visited:
            return False
        visiting.add(location_id)
        cycle = any(visit(child) for child in children.get(location_id, ()))
        visiting.remove(location_id)
        visited.add(location_id)
        return cycle

    if any(visit(location_id) for location_id in location_ids if location_id not in visited):
        errors.append("Location containment contains a cycle.")
    return errors


def confidence_provenance(confidence: str) -> str:
    return {
        "User confirmed": "user_confirmed",
        "Source reported": "source_reported",
        "Approximate": "approximate",
        "Unknown": "unknown",
    }[confidence]


def _address_from_row(row: sqlite3.Row) -> LocationAddress:
    return LocationAddress(
        id=int(row["id"]),
        location_entity_id=int(row["location_entity_id"]),
        purpose=row["purpose"],
        formatted_address=row["formatted_address"],
        address_line_1=row["address_line_1"],
        address_line_2=row["address_line_2"],
        suburb=row["suburb"],
        city=row["city"],
        state=row["state"],
        post_code=row["post_code"],
        country=row["country"],
        confidence=row["confidence"],
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        source_version=row["source_version"],
        is_current=bool(row["is_current"]),
        is_preferred=bool(row["is_preferred"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _geometry_from_row(row: sqlite3.Row) -> LocationGeometry:
    return LocationGeometry(
        id=int(row["id"]),
        location_entity_id=int(row["location_entity_id"]),
        geometry_type=row["geometry_type"],
        coordinates=json.loads(row["coordinates_json"]),
        role=row["role"],
        confidence=row["confidence"],
        accuracy_radius_metres=(
            None
            if row["accuracy_radius_metres"] is None
            else float(row["accuracy_radius_metres"])
        ),
        source_name=row["source_name"],
        source_reference=row["source_reference"],
        source_version=row["source_version"],
        is_current=bool(row["is_current"]),
        is_preferred=bool(row["is_preferred"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _provider_reference_from_row(row: sqlite3.Row) -> LocationProviderReference:
    return LocationProviderReference(
        id=int(row["id"]),
        location_entity_id=int(row["location_entity_id"]),
        provider_key=row["provider_key"],
        feature_id=row["feature_id"],
        feature_version=row["feature_version"],
        observed_at=row["observed_at"],
        accepted_at=row["accepted_at"],
    )


def _ensure_location(connection: sqlite3.Connection, location_entity_id: int) -> None:
    row = connection.execute(
        "SELECT type FROM entities WHERE id=?", (location_entity_id,)
    ).fetchone()
    if row is None or row["type"] != "location":
        raise ValueError("Location does not exist.")


def _inherited_address(
    connection: sqlite3.Connection, location_entity_id: int
) -> tuple[LocationAddress | None, int | None, str]:
    seen = {location_entity_id}
    child_id = location_entity_id
    while True:
        row = connection.execute(
            """SELECT parent.id, parent.display_name
               FROM relationships relationship
               JOIN entities parent ON parent.id=relationship.source_entity_id
               WHERE relationship.type='contains_location'
                 AND relationship.status='active'
                 AND relationship.deleted_at=''
                 AND relationship.target_entity_id=?
                 AND parent.deleted_at=''
               ORDER BY relationship.id DESC LIMIT 1""",
            (child_id,),
        ).fetchone()
        if row is None:
            return None, None, ""
        parent_id = int(row["id"])
        if parent_id in seen:
            return None, None, ""
        seen.add(parent_id)
        address = preferred_location_address(connection, parent_id)
        if address:
            return address, parent_id, row["display_name"]
        child_id = parent_id


def _require_sequence(value: object, label: str) -> Sequence:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} coordinates must be an array.")
    return value


def _validate_position(value: object) -> None:
    position = _require_sequence(value, "Position")
    if len(position) != 2:
        raise ValueError("A position requires longitude and latitude.")
    longitude, latitude = position
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise ValueError("Coordinates must be finite numbers.")
    try:
        longitude = float(longitude)
        latitude = float(latitude)
    except (TypeError, ValueError) as error:
        raise ValueError("Coordinates must be finite numbers.") from error
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise ValueError("Coordinates must be finite numbers.")
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise ValueError("Coordinates must be valid WGS84 longitude/latitude values.")


def _validate_line(value: object) -> None:
    line = _require_sequence(value, "LineString")
    if len(line) < 2:
        raise ValueError("LineString requires at least two positions.")
    for position in line:
        _validate_position(position)


def _validate_polygon(value: object) -> None:
    polygon = _require_sequence(value, "Polygon")
    if not polygon:
        raise ValueError("Polygon requires at least one ring.")
    for ring in polygon:
        ring = _require_sequence(ring, "Polygon ring")
        if len(ring) < 4:
            raise ValueError("A polygon ring requires at least four positions.")
        for position in ring:
            _validate_position(position)
        if list(ring[0]) != list(ring[-1]):
            raise ValueError("A polygon ring must be closed.")


def _canonical_coordinates(value: Any) -> Any:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonical_coordinates(item) for item in value]
    return float(value)


def _format_coordinate(value: float) -> str:
    return format(value, ".15g")
