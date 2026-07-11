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
        WHERE deleted_at = ''
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
        WHERE deleted_at = '' AND (source_entity_id = ? OR target_entity_id = ?)
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
    connection: sqlite3.Connection, relationship_id: int, include_deleted: bool = False
) -> RelationshipRecord | None:
    row = connection.execute(
        "SELECT * FROM relationships WHERE id = ? AND (? OR deleted_at = '')",
        (relationship_id, include_deleted)
    ).fetchone()
    if row is None:
        return None
    try:
        return to_relationship_record(connection, row)
    except ValueError:
        return None


def create_relationship(connection: sqlite3.Connection, values: dict[str, str]) -> int:
    normalise_relationship_direction(connection, values)
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO relationships (
            source_entity_id, target_entity_id, type, status,
            started_at, started_at_precision, ended_at, ended_at_precision, notes, created_at, updated_at, taxonomy_entry_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            (SELECT e.id FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id
             WHERE t.key='relationship_type' AND e.key=?))
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
            values["type"],
        ),
    )
    relationship_id = int(cursor.lastrowid)
    from app.audit import record_audit_event, set_provenance
    record_audit_event(connection, "create", [("relationship", relationship_id), ("entity", int(values["source_entity_id"])), ("entity", int(values["target_entity_id"]))], after=values, notes="Relationship created")
    set_provenance(connection, "relationship", relationship_id, "*", "manual")
    from app.relationship_inference import recompute_inferences
    recompute_inferences(connection, "relationship_created", relationship_id)
    return relationship_id


def update_relationship(
    connection: sqlite3.Connection, relationship_id: int, values: dict[str, str]
) -> None:
    normalise_relationship_direction(connection, values)
    before = get_relationship(connection, relationship_id)
    connection.execute(
        """
        UPDATE relationships
        SET source_entity_id = ?, target_entity_id = ?, type = ?, status = ?,
            started_at = ?, started_at_precision = ?, ended_at = ?, ended_at_precision = ?, notes = ?, updated_at = ?,
            taxonomy_entry_id=(SELECT e.id FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id
              WHERE t.key='relationship_type' AND e.key=?)
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
            values["type"],
            relationship_id,
        ),
    )
    from app.audit import record_audit_event
    record_audit_event(connection, "edit", [("relationship", relationship_id), ("entity", int(values["source_entity_id"])), ("entity", int(values["target_entity_id"]))], before=before.to_form_values() if before else None, after=values, notes="Relationship edited")
    from app.relationship_inference import recompute_inferences
    recompute_inferences(connection, "relationship_updated", relationship_id)


def delete_relationship(connection: sqlite3.Connection, relationship_id: int) -> bool:
    before = get_relationship(connection, relationship_id)
    if before is None:
        return False
    from app.audit import record_audit_event
    deleted_at = utc_now()
    record_audit_event(connection, "delete", [("relationship", relationship_id), ("entity", before.source.id), ("entity", before.target.id)], before=before.to_form_values(), after={"deleted_at": deleted_at}, notes="Relationship moved to Recycle Bin")
    connection.execute("UPDATE relationships SET deleted_at=?, updated_at=? WHERE id=? AND deleted_at=''", (deleted_at, deleted_at, relationship_id))
    from app.relationship_inference import recompute_inferences
    recompute_inferences(connection, "relationship_deleted", relationship_id)
    return True


def restore_relationship(connection: sqlite3.Connection, relationship_id: int) -> bool:
    before = get_relationship(connection, relationship_id, include_deleted=True)
    if before is None or not before.is_deleted:
        return False
    restored_at = utc_now()
    connection.execute("UPDATE relationships SET deleted_at='', updated_at=? WHERE id=?", (restored_at, relationship_id))
    from app.audit import record_audit_event
    record_audit_event(connection, "restore", [("relationship", relationship_id), ("entity", before.source.id), ("entity", before.target.id)], before={"deleted_at": before.deleted_at}, after={"deleted_at": ""}, notes="Relationship restored from Recycle Bin")
    from app.relationship_inference import recompute_inferences
    recompute_inferences(connection, "relationship_restored", relationship_id)
    return True


def list_deleted_relationships(connection: sqlite3.Connection) -> list[RelationshipRecord]:
    rows = connection.execute("SELECT * FROM relationships WHERE deleted_at<>'' ORDER BY deleted_at DESC, id DESC").fetchall()
    records = []
    for row in rows:
        try:
            records.append(to_relationship_record(connection, row, include_deleted_entities=True))
        except ValueError:
            continue
    return records


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
    connection: sqlite3.Connection, values: dict[str, str], relationship_id: int | None = None
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
        if source is not None and target is not None and not relationship_type_is_valid_for_pair(type_key, source.type, target.type):
            existing = connection.execute("SELECT type FROM relationships WHERE id=?", (relationship_id,)).fetchone() if relationship_id is not None else None
            relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(type_key)
            retaining_archived = bool(existing and existing["type"] == type_key and relationship_type and relationship_type.supports_pair(source.type, target.type))
            if not retaining_archived:
                errors.append("Relationship type is not valid for these entity types.")

    if values.get("status") not in RELATIONSHIP_STATUSES:
        errors.append("Relationship status is invalid.")

    if values.get("started_at_precision", "exact") not in DATE_PRECISIONS:
        errors.append("Start date certainty is invalid.")

    if values.get("ended_at_precision", "exact") not in DATE_PRECISIONS:
        errors.append("End date certainty is invalid.")

    if source_id is not None and target_id is not None and type_key in RELATIONSHIP_TYPES_BY_KEY:
        symmetric = not RELATIONSHIP_TYPES_BY_KEY[type_key].directional
        params = [type_key, source_id, target_id]
        reverse_sql = " OR (source_entity_id=? AND target_entity_id=?)" if symmetric else ""
        if symmetric:
            params.extend((target_id, source_id))
        exclude_sql = " AND id<>?" if relationship_id is not None else ""
        if relationship_id is not None:
            params.append(relationship_id)
        duplicate = connection.execute(f"SELECT 1 FROM relationships WHERE deleted_at='' AND type=? AND ((source_entity_id=? AND target_entity_id=?){reverse_sql}){exclude_sql}", params).fetchone()
        if duplicate:
            errors.append("This relationship already exists.")
        family_types = ("parent_child", "grandparent_child", "sibling_of", "aunt_uncle_niece_nephew", "cousin_of")
        if type_key in family_types:
            placeholders = ",".join("?" for _ in family_types)
            conflict_exclude = " AND id<>?" if relationship_id is not None else ""
            conflict_params = [source_id, target_id, target_id, source_id, *family_types, type_key]
            if relationship_id is not None:
                conflict_params.append(relationship_id)
            conflict = connection.execute(f"SELECT 1 FROM relationships WHERE deleted_at='' AND ((source_entity_id=? AND target_entity_id=?) OR (source_entity_id=? AND target_entity_id=?)) AND type IN ({placeholders}) AND type<>?{conflict_exclude}", conflict_params).fetchone()
            if conflict:
                errors.append("A conflicting bloodline relationship already connects these people.")
        if type_key == "parent_child" and _parent_path_exists(connection, target_id, source_id, relationship_id):
            errors.append("This parent relationship would create a family cycle.")

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
    connection: sqlite3.Connection, row: sqlite3.Row, include_deleted_entities: bool = False
) -> RelationshipRecord:
    source = get_entity_by_id(connection, int(row["source_entity_id"]), include_deleted=include_deleted_entities)
    target = get_entity_by_id(connection, int(row["target_entity_id"]), include_deleted=include_deleted_entities)
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
        record_origin=row["record_origin"],
        inference_suggestion_id=row["inference_suggestion_id"],
        provenance_json=row["provenance_json"],
        created_from_inference=bool(row["created_from_inference"]),
        inference_evidence_status=row["inference_evidence_status"],
        deleted_at=row["deleted_at"],
    )


def _parent_path_exists(connection: sqlite3.Connection, start_id: int, goal_id: int, exclude_id: int | None = None) -> bool:
    rows = connection.execute("SELECT id, source_entity_id, target_entity_id FROM relationships WHERE deleted_at='' AND type='parent_child' AND status='active'").fetchall()
    children = {}
    for row in rows:
        if exclude_id is not None and int(row["id"]) == exclude_id:
            continue
        children.setdefault(int(row["source_entity_id"]), set()).add(int(row["target_entity_id"]))
    stack, seen = [start_id], set()
    while stack:
        node = stack.pop()
        if node == goal_id:
            return True
        if node not in seen:
            seen.add(node); stack.extend(children.get(node, ()))
    return False
