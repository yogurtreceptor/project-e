import json
import sqlite3
from dataclasses import dataclass

from app.db_support import utc_now
from app.entities import EntityRecord
from app.entity_repository import get_entity_by_id, update_typed_row
from app.relationships import RELATIONSHIP_TYPES_BY_KEY


@dataclass(frozen=True)
class MergeField:
    name: str
    label: str
    survivor_value: str
    duplicate_value: str
    result_value: str
    conflict: bool


@dataclass(frozen=True)
class MergePreview:
    survivor: EntityRecord
    duplicate: EntityRecord
    fields: tuple[MergeField, ...]
    relationships_to_repoint: int
    duplicate_relationships_to_remove: int


def preview_entity_merge(connection: sqlite3.Connection, survivor_id: int, duplicate_id: int) -> MergePreview:
    survivor = get_entity_by_id(connection, survivor_id)
    duplicate = get_entity_by_id(connection, duplicate_id)
    if survivor is None or duplicate is None:
        raise ValueError("Both merge records must exist.")
    if survivor.id == duplicate.id:
        raise ValueError("Choose two different records.")
    if survivor.type != duplicate.type:
        raise ValueError("Only records of the same entity type can be merged.")

    values = [("display_name", "Name", survivor.display_name, duplicate.display_name)]
    values.extend((field.name, field.label, survivor.metadata.get(field.name, ""), duplicate.metadata.get(field.name, "")) for field in survivor.definition.fields)
    values.append(("notes", "Notes", survivor.notes, duplicate.notes))
    fields = []
    for name, label, left, right in values:
        if name == "notes" and left and right and left != right:
            result = left + "\n\n" + right
        else:
            result = left or right
        fields.append(MergeField(name, label, left, right, result, bool(left and right and left != right and name != "notes")))

    rows = connection.execute("SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?", (duplicate_id, duplicate_id)).fetchall()
    existing = {_relationship_key(row, survivor_id, duplicate_id) for row in connection.execute("SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?", (survivor_id, survivor_id))}
    duplicate_count = sum(1 for row in rows if _relationship_key(row, survivor_id, duplicate_id) in existing or _would_self_reference(row, survivor_id, duplicate_id))
    return MergePreview(survivor, duplicate, tuple(fields), len(rows), duplicate_count)


def merge_entities(connection: sqlite3.Connection, survivor_id: int, duplicate_id: int) -> MergePreview:
    preview = preview_entity_merge(connection, survivor_id, duplicate_id)
    survivor, duplicate = preview.survivor, preview.duplicate
    details = {
        "survivor_before": survivor.to_form_values(),
        "duplicate_before": duplicate.to_form_values(),
        "field_conflicts": {field.name: {"kept": field.result_value, "duplicate": field.duplicate_value} for field in preview.fields if field.conflict},
        "duplicate_relationships_before": [dict(row) for row in connection.execute("SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?", (duplicate_id, duplicate_id))],
    }
    values = {field.name: field.result_value for field in preview.fields}
    now = utc_now()
    connection.execute("BEGIN")
    try:
        connection.execute("UPDATE entities SET display_name = ?, notes = ?, updated_at = ? WHERE id = ?", (values["display_name"], values["notes"], now, survivor_id))
        update_typed_row(connection, survivor.definition, survivor_id, values)
        existing = {_relationship_key(row, survivor_id, duplicate_id) for row in connection.execute("SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?", (survivor_id, survivor_id))}
        for row in connection.execute("SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?", (duplicate_id, duplicate_id)).fetchall():
            key = _relationship_key(row, survivor_id, duplicate_id)
            if key in existing or _would_self_reference(row, survivor_id, duplicate_id):
                connection.execute("DELETE FROM relationships WHERE id = ?", (row["id"],))
                continue
            connection.execute(
                "UPDATE relationships SET source_entity_id = CASE WHEN source_entity_id = ? THEN ? ELSE source_entity_id END, target_entity_id = CASE WHEN target_entity_id = ? THEN ? ELSE target_entity_id END, updated_at = ? WHERE id = ?",
                (duplicate_id, survivor_id, duplicate_id, survivor_id, now, row["id"]),
            )
            existing.add(key)
        old_history = connection.execute("SELECT event_type, details, created_at FROM entity_edit_history WHERE entity_id = ?", (duplicate_id,)).fetchall()
        for row in old_history:
            connection.execute("INSERT INTO entity_edit_history (entity_id, event_type, details, created_at) VALUES (?, ?, ?, ?)", (survivor_id, "merged_history:" + row["event_type"], row["details"], row["created_at"]))
        connection.execute("INSERT INTO entity_edit_history (entity_id, event_type, details, created_at) VALUES (?, 'merge', ?, ?)", (survivor_id, json.dumps(details, sort_keys=True), now))
        connection.execute("DELETE FROM entities WHERE id = ?", (duplicate_id,))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return preview


def list_entity_history(connection: sqlite3.Connection, entity_id: int) -> list[sqlite3.Row]:
    return connection.execute("SELECT * FROM entity_edit_history WHERE entity_id = ? ORDER BY created_at DESC, id DESC", (entity_id,)).fetchall()


def record_entity_edit(connection: sqlite3.Connection, entity_id: int, before: dict[str, str], after: dict[str, str]) -> None:
    if before == after:
        return
    connection.execute("INSERT INTO entity_edit_history (entity_id, event_type, details, created_at) VALUES (?, 'edit', ?, ?)", (entity_id, json.dumps({"before": before, "after": after}, sort_keys=True), utc_now()))


def _would_self_reference(row: sqlite3.Row, survivor_id: int, duplicate_id: int) -> bool:
    source = survivor_id if row["source_entity_id"] == duplicate_id else row["source_entity_id"]
    target = survivor_id if row["target_entity_id"] == duplicate_id else row["target_entity_id"]
    return source == target


def _relationship_key(row: sqlite3.Row, survivor_id: int, duplicate_id: int) -> tuple[object, ...]:
    source = survivor_id if row["source_entity_id"] == duplicate_id else int(row["source_entity_id"])
    target = survivor_id if row["target_entity_id"] == duplicate_id else int(row["target_entity_id"])
    relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(row["type"])
    if relationship_type and not relationship_type.directional:
        source, target = sorted((source, target))
    return (source, target, row["type"])
