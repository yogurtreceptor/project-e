import sqlite3
from typing import Any

from app.db_support import parse_int, utc_now
from app.entities import EntityRecord
from app.entity_repository import get_entity_by_id
from app.relationships import (
    DATE_PRECISIONS,
    RELATIONSHIP_STATUSES,
    RELATIONSHIP_TYPES_BY_KEY,
    RelationshipRecord,
    relationship_type_is_valid_for_pair,
    split_relationship_choice,
)
from app.structured_values import normalise_structured_value, validate_structured_value


def list_relationships(connection: sqlite3.Connection) -> list[RelationshipRecord]:
    rows = connection.execute(
        """
        SELECT *
        FROM relationships
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    records = []
    for row in rows:
        try:
            records.append(to_relationship_record(connection, row))
        except ValueError:
            continue
    return records


def list_relationships_for_entity(
    connection: sqlite3.Connection, entity_id: int
) -> list[RelationshipRecord]:
    rows = connection.execute(
        """
        SELECT *
        FROM relationships
        WHERE source_entity_id = ? OR target_entity_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (entity_id, entity_id),
    ).fetchall()
    records = []
    for row in rows:
        try:
            records.append(to_relationship_record(connection, row))
        except ValueError:
            continue
    return records


def get_relationship(
    connection: sqlite3.Connection, relationship_id: int
) -> RelationshipRecord | None:
    row = connection.execute(
        "SELECT * FROM relationships WHERE id = ?", (relationship_id,)
    ).fetchone()
    if row is None:
        return None
    return to_relationship_record(connection, row)


def create_relationship(connection: sqlite3.Connection, values: dict[str, str]) -> int:
    normalise_relationship_direction(connection, values)
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO relationships (
            source_entity_id, target_entity_id, type, status,
            started_at, started_at_precision, ended_at, ended_at_precision, notes, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(values["source_entity_id"]),
            int(values["target_entity_id"]),
            values["type"],
            values.get("status", "active"),
            values.get("started_at", ""),
            values.get("started_at_precision", "exact"),
            values.get("ended_at", ""),
            values.get("ended_at_precision", "exact"),
            values.get("notes", ""),
            now,
            now,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def update_relationship(
    connection: sqlite3.Connection, relationship_id: int, values: dict[str, str]
) -> None:
    normalise_relationship_direction(connection, values)
    connection.execute(
        """
        UPDATE relationships
        SET source_entity_id = ?, target_entity_id = ?, type = ?, status = ?,
            started_at = ?, started_at_precision = ?, ended_at = ?, ended_at_precision = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            int(values["source_entity_id"]),
            int(values["target_entity_id"]),
            values["type"],
            values.get("status", "active"),
            values.get("started_at", ""),
            values.get("started_at_precision", "exact"),
            values.get("ended_at", ""),
            values.get("ended_at_precision", "exact"),
            values.get("notes", ""),
            utc_now(),
            relationship_id,
        ),
    )
    connection.commit()


def delete_relationship(connection: sqlite3.Connection, relationship_id: int) -> None:
    connection.execute("DELETE FROM relationships WHERE id = ?", (relationship_id,))
    connection.commit()


def normalise_relationship_values(raw_values: dict[str, Any]) -> dict[str, str]:
    return {
        "source_entity_id": str(raw_values.get("source_entity_id", "")).strip(),
        "target_entity_id": str(raw_values.get("target_entity_id", "")).strip(),
        "type": str(raw_values.get("type", "")).strip(),
        "status": str(raw_values.get("status", "active")).strip() or "active",
        "started_at": normalise_structured_value(str(raw_values.get("started_at", "")), "date"),
        "started_at_precision": str(raw_values.get("started_at_precision", "exact")).strip() or "exact",
        "ended_at": normalise_structured_value(str(raw_values.get("ended_at", "")), "date"),
        "ended_at_precision": str(raw_values.get("ended_at_precision", "exact")).strip() or "exact",
        "notes": str(raw_values.get("notes", "")).strip(),
        "workflow_mode": str(raw_values.get("workflow_mode", "existing")).strip() or "existing",
    }


def validate_relationship_values(
    connection: sqlite3.Connection, values: dict[str, str]
) -> list[str]:
    errors = []
    source_id = parse_int(values.get("source_entity_id", ""))
    target_id = parse_int(values.get("target_entity_id", ""))

    if source_id is None:
        errors.append("Source entity is required.")
    elif get_entity_by_id(connection, source_id) is None:
        errors.append("Source entity does not exist.")

    if target_id is None:
        errors.append("Target entity is required.")
    elif get_entity_by_id(connection, target_id) is None:
        errors.append("Target entity does not exist.")

    if source_id is not None and target_id is not None and source_id == target_id:
        errors.append("A relationship must connect two different entities.")

    type_key, _connected_role = split_relationship_choice(values.get("type", ""))
    if type_key not in RELATIONSHIP_TYPES_BY_KEY:
        errors.append("Relationship type is required.")
    elif source_id is not None and target_id is not None and source_id != target_id:
        source = get_entity_by_id(connection, source_id)
        target = get_entity_by_id(connection, target_id)
        if source is not None and target is not None and not relationship_type_is_valid_for_pair(
            type_key, source.type, target.type
        ):
            errors.append("Relationship type is not valid for these entity types.")

    if values.get("status") not in RELATIONSHIP_STATUSES:
        errors.append("Relationship status is invalid.")

    if values.get("started_at_precision", "exact") not in DATE_PRECISIONS:
        errors.append("Start date certainty is invalid.")

    if values.get("ended_at_precision", "exact") not in DATE_PRECISIONS:
        errors.append("End date certainty is invalid.")

    for field_name, label in (("started_at", "Started"), ("ended_at", "Ended")):
        date_error = validate_structured_value(values.get(field_name, ""), "date", label)
        if date_error:
            errors.append(date_error)

    return errors


def normalise_relationship_direction(connection: sqlite3.Connection, values: dict[str, str]) -> None:
    type_key, connected_role = split_relationship_choice(values.get("type", ""))
    values["type"] = type_key
    relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(type_key)
    if relationship_type is None or not relationship_type.pairs:
        return
    source_id = parse_int(values.get("source_entity_id", ""))
    target_id = parse_int(values.get("target_entity_id", ""))
    if source_id is None or target_id is None:
        return
    source = get_entity_by_id(connection, source_id)
    target = get_entity_by_id(connection, target_id)
    if source is None or target is None:
        return

    if connected_role == "source":
        values["source_entity_id"], values["target_entity_id"] = str(target_id), str(source_id)
        return
    if connected_role == "target":
        values["source_entity_id"], values["target_entity_id"] = str(source_id), str(target_id)
        return

    for source_type, target_type in relationship_type.pairs:
        if source.type == source_type and target.type == target_type:
            return
        if source.type == target_type and target.type == source_type:
            values["source_entity_id"], values["target_entity_id"] = values["target_entity_id"], values["source_entity_id"]
            return


def to_relationship_record(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> RelationshipRecord:
    source = get_entity_by_id(connection, int(row["source_entity_id"]))
    target = get_entity_by_id(connection, int(row["target_entity_id"]))
    if source is None or target is None:
        raise ValueError(f"Relationship {row['id']} references a missing entity")
    return RelationshipRecord(
        id=int(row["id"]),
        type_key=row["type"],
        source=source,
        target=target,
        status=row["status"],
        started_at=row["started_at"],
        started_at_precision=row["started_at_precision"],
        ended_at=row["ended_at"],
        ended_at_precision=row["ended_at_precision"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
