"""Validated workflows over canonical Location place assertions."""

from __future__ import annotations

import math
import sqlite3

from app.audit import record_audit_event
from app.db_support import utc_now
from app.place_repository import (
    PLACE_CONFIDENCE_LEVELS,
    LocationAddress,
    LocationGeometry,
    create_location_address,
    create_location_geometry,
    preferred_location_address,
    preferred_location_geometry,
)


ADDRESS_VALUE_FIELDS = (
    "formatted_address",
    "address_line_1",
    "address_line_2",
    "suburb",
    "city",
    "state",
    "post_code",
    "country",
)


def validate_location_form_values(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    latitude = values.get("latitude", "").strip()
    longitude = values.get("longitude", "").strip()
    confidence = values.get("geometry_confidence", "User confirmed")
    if confidence not in PLACE_CONFIDENCE_LEVELS:
        errors.append("Geometry confidence is invalid.")
    address_confidence = values.get("address_confidence", "User confirmed")
    if address_confidence not in PLACE_CONFIDENCE_LEVELS:
        errors.append("Address confidence is invalid.")
    radius = values.get("accuracy_radius_metres", "").strip()
    if radius:
        try:
            number = float(radius)
            if not math.isfinite(number) or number <= 0:
                raise ValueError
        except ValueError:
            errors.append("Accuracy radius must be a positive number.")
        if not latitude or not longitude:
            errors.append("Accuracy radius requires Coordinates.")
    return errors


def sync_location_form_values(
    connection: sqlite3.Connection,
    location_entity_id: int,
    values: dict[str, str],
    *,
    audit: bool = True,
) -> None:
    _sync_physical_address(connection, location_entity_id, values, audit=audit)
    _sync_representative_point(connection, location_entity_id, values, audit=audit)


def merge_location_place_data(
    connection: sqlite3.Connection, survivor_id: int, duplicate_id: int
) -> None:
    for table, grouping_column in (
        ("location_addresses", "purpose"),
        ("location_geometries", "role"),
    ):
        survivor_preferred = {
            row[grouping_column]
            for row in connection.execute(
                f"SELECT {grouping_column} FROM {table} "
                "WHERE location_entity_id=? AND is_preferred=1",
                (survivor_id,),
            )
        }
        for group in survivor_preferred:
            connection.execute(
                f"UPDATE {table} SET is_preferred=0, updated_at=? "
                f"WHERE location_entity_id=? AND {grouping_column}=?",
                (utc_now(), duplicate_id, group),
            )
        connection.execute(
            f"UPDATE {table} SET location_entity_id=?, updated_at=? "
            "WHERE location_entity_id=?",
            (survivor_id, utc_now(), duplicate_id),
        )
    connection.execute(
        """DELETE FROM location_provider_references
           WHERE location_entity_id=? AND EXISTS (
               SELECT 1 FROM location_provider_references survivor
               WHERE survivor.location_entity_id=?
                 AND survivor.provider_key=location_provider_references.provider_key
                 AND survivor.feature_id=location_provider_references.feature_id
                 AND survivor.feature_version=location_provider_references.feature_version
           )""",
        (duplicate_id, survivor_id),
    )
    connection.execute(
        """UPDATE location_provider_references
           SET location_entity_id=? WHERE location_entity_id=?""",
        (survivor_id, duplicate_id),
    )


def _sync_physical_address(
    connection: sqlite3.Connection,
    location_entity_id: int,
    values: dict[str, str],
    *,
    audit: bool,
) -> None:
    existing = preferred_location_address(connection, location_entity_id)
    content = {field: values.get(field, "").strip() for field in ADDRESS_VALUE_FIELDS}
    has_address = any(content.values())
    if not has_address:
        if existing:
            _retire_address(connection, existing, audit=audit)
        return
    source_name = values.get("address_source_name", values.get("source", "")).strip()
    payload = {
        **content,
        "confidence": values.get("address_confidence", "User confirmed")
        or "User confirmed",
        "source_name": source_name,
        "source_reference": values.get("address_source_reference", "").strip(),
        "source_version": values.get("address_source_version", "").strip(),
    }
    if existing and _address_matches(existing, payload):
        return
    if existing:
        _retire_address(connection, existing, audit=audit)
    create_location_address(
        connection,
        location_entity_id,
        purpose="physical",
        is_current=True,
        is_preferred=True,
        commit=False,
        audit=audit,
        **payload,
    )


def _sync_representative_point(
    connection: sqlite3.Connection,
    location_entity_id: int,
    values: dict[str, str],
    *,
    audit: bool,
) -> None:
    existing = preferred_location_geometry(
        connection, location_entity_id, "representative_point"
    )
    latitude = values.get("latitude", "").strip()
    longitude = values.get("longitude", "").strip()
    if not latitude and not longitude:
        if existing:
            _retire_geometry(connection, existing, audit=audit)
        return
    radius_text = values.get("accuracy_radius_metres", "").strip()
    radius = float(radius_text) if radius_text else None
    source_name = values.get("geometry_source_name", values.get("source", "")).strip()
    payload = {
        "coordinates": [float(longitude), float(latitude)],
        "confidence": values.get("geometry_confidence", "User confirmed")
        or "User confirmed",
        "accuracy_radius_metres": radius,
        "source_name": source_name,
        "source_reference": values.get("geometry_source_reference", "").strip(),
        "source_version": values.get("geometry_source_version", "").strip(),
    }
    if existing and _geometry_matches(existing, payload):
        return
    if existing:
        _retire_geometry(connection, existing, audit=audit)
    create_location_geometry(
        connection,
        location_entity_id,
        "Point",
        role="representative_point",
        is_current=True,
        is_preferred=True,
        commit=False,
        audit=audit,
        **payload,
    )


def _retire_address(
    connection: sqlite3.Connection, address: LocationAddress, *, audit: bool
) -> None:
    after = {**address.snapshot(), "is_current": False, "is_preferred": False}
    connection.execute(
        """UPDATE location_addresses
           SET is_current=0, is_preferred=0, updated_at=? WHERE id=?""",
        (utc_now(), address.id),
    )
    if audit:
        record_audit_event(
            connection,
            "edit",
            [
                ("location_address", address.id),
                ("entity", address.location_entity_id),
            ],
            before=address.snapshot(),
            after=after,
            notes="Previous preferred physical address retained as historical",
        )


def _retire_geometry(
    connection: sqlite3.Connection, geometry: LocationGeometry, *, audit: bool
) -> None:
    after = {**geometry.snapshot(), "is_current": False, "is_preferred": False}
    connection.execute(
        """UPDATE location_geometries
           SET is_current=0, is_preferred=0, updated_at=? WHERE id=?""",
        (utc_now(), geometry.id),
    )
    if audit:
        record_audit_event(
            connection,
            "edit",
            [
                ("location_geometry", geometry.id),
                ("entity", geometry.location_entity_id),
            ],
            before=geometry.snapshot(),
            after=after,
            notes="Previous representative point retained as historical",
        )


def _address_matches(address: LocationAddress, payload: dict[str, object]) -> bool:
    return all(getattr(address, field) == payload[field] for field in ADDRESS_VALUE_FIELDS) and all(
        getattr(address, field) == payload[field]
        for field in (
            "confidence",
            "source_name",
            "source_reference",
            "source_version",
        )
    )


def _geometry_matches(geometry: LocationGeometry, payload: dict[str, object]) -> bool:
    return (
        geometry.geometry_type == "Point"
        and geometry.coordinates == payload["coordinates"]
        and geometry.confidence == payload["confidence"]
        and geometry.accuracy_radius_metres == payload["accuracy_radius_metres"]
        and geometry.source_name == payload["source_name"]
        and geometry.source_reference == payload["source_reference"]
        and geometry.source_version == payload["source_version"]
    )
