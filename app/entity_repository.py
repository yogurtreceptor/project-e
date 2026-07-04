import sqlite3
from typing import Any

from app.db_support import sql_identifier, utc_now
from app.entities import (
    DEFINITIONS_BY_TYPE,
    ENTITY_DEFINITIONS,
    EntityDefinition,
    EntityRecord,
    to_entity_record,
)
from app.structured_values import normalise_structured_value, validate_structured_value


def list_entities(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    query: str = "",
    favourites_only: bool = False,
) -> list[EntityRecord]:
    rows = connection.execute(
        """
        SELECT entities.*, typed.*
        FROM entities
        JOIN {table} AS typed ON typed.entity_id = entities.id
        WHERE entities.type = ? AND entities.deleted_at = ''
        ORDER BY lower(entities.display_name), entities.id
        """.format(table=sql_identifier(definition.table)),
        (definition.type,),
    ).fetchall()
    records = [to_entity_record(definition, row) for row in rows]
    if favourites_only:
        records = [record for record in records if record.is_favourite]
    if query:
        records = [record for record in records if entity_matches_query(record, query)]
    return records


def list_all_entities(connection: sqlite3.Connection) -> list[EntityRecord]:
    records: list[EntityRecord] = []
    for definition in ENTITY_DEFINITIONS:
        records.extend(list_entities(connection, definition))
    return sorted(records, key=lambda record: (record.display_name.lower(), record.id))


def count_entities(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT type, COUNT(*) AS count FROM entities WHERE deleted_at = '' GROUP BY type"
    ).fetchall()
    return {row["type"]: row["count"] for row in rows}


def get_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, entity_id: int,
    include_deleted: bool = False,
) -> EntityRecord | None:
    deleted_clause = "" if include_deleted else "AND entities.deleted_at = ''"
    row = connection.execute(
        """
        SELECT entities.*, typed.*
        FROM entities
        JOIN {table} AS typed ON typed.entity_id = entities.id
        WHERE entities.id = ? AND entities.type = ? {deleted_clause}
        """.format(table=sql_identifier(definition.table), deleted_clause=deleted_clause),
        (entity_id, definition.type),
    ).fetchone()
    if row is None:
        return None
    return to_entity_record(definition, row)


def get_entity_by_id(connection: sqlite3.Connection, entity_id: int, include_deleted: bool = False) -> EntityRecord | None:
    clause = "" if include_deleted else "AND deleted_at = ''"
    row = connection.execute(f"SELECT id, type FROM entities WHERE id = ? {clause}", (entity_id,)).fetchone()
    if row is None:
        return None
    definition = DEFINITIONS_BY_TYPE.get(row["type"])
    if definition is None:
        return None
    return get_entity(connection, definition, entity_id, include_deleted=include_deleted)


def list_deleted_entities(connection: sqlite3.Connection) -> list[EntityRecord]:
    records = []
    rows = connection.execute("SELECT id FROM entities WHERE deleted_at <> '' ORDER BY deleted_at DESC, id DESC")
    for row in rows:
        record = get_entity_by_id(connection, int(row["id"]), include_deleted=True)
        if record is not None:
            records.append(record)
    return records


def create_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    values: dict[str, str],
    commit: bool = True,
) -> int:
    values = with_canonical_person_name(definition, values)
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO entities (type, display_name, summary, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            definition.type,
            values["display_name"],
            values.get("summary", ""),
            values.get("notes", ""),
            now,
            now,
        ),
    )
    entity_id = int(cursor.lastrowid)
    insert_typed_row(connection, definition, entity_id, values)
    from app.audit import record_audit_event, set_provenance
    record_audit_event(connection, "create", [("entity", entity_id)], after=values)
    for field, value in values.items():
        if value: set_provenance(connection, "entity", entity_id, field, "manual")
    if commit:
        connection.commit()
    return entity_id


def update_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
    values = with_canonical_person_name(definition, values)
    before = get_entity(connection, definition, entity_id)
    connection.execute(
        """
        UPDATE entities
        SET display_name = ?, summary = ?, notes = ?, updated_at = ?
        WHERE id = ? AND type = ?
        """,
        (
            values["display_name"],
            values.get("summary", ""),
            values.get("notes", ""),
            utc_now(),
            entity_id,
            definition.type,
        ),
    )
    update_typed_row(connection, definition, entity_id, values)
    if before is not None:
        from app.audit import record_audit_event
        record_audit_event(connection, "edit", [("entity", entity_id)], before=before.to_form_values(), after=values)
    if definition.type == "person" and before is not None and before.metadata.get("birthday", "") != values.get("birthday", ""):
        from app.relationship_inference import recompute_inferences
        recompute_inferences(connection, "person_date_updated", entity_id)
    else:
        connection.commit()


def delete_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, entity_id: int
) -> None:
    before = get_entity(connection, definition, entity_id)
    from app.audit import record_audit_event
    if before: record_audit_event(connection, "delete", [("entity", entity_id)], before=before.to_form_values())
    connection.execute("UPDATE entities SET deleted_at = ?, updated_at = ? WHERE id = ? AND type = ? AND deleted_at = ''", (utc_now(), utc_now(), entity_id, definition.type))
    if definition.type == "person":
        from app.relationship_inference import recompute_inferences
        recompute_inferences(connection, "person_deleted", entity_id)
    else:
        connection.commit()


def restore_entity(connection: sqlite3.Connection, entity_id: int) -> bool:
    before = get_entity_by_id(connection, entity_id, include_deleted=True)
    if before is None or not before.is_deleted:
        return False
    connection.execute("UPDATE entities SET deleted_at = '', updated_at = ? WHERE id = ?", (utc_now(), entity_id))
    from app.audit import record_audit_event
    record_audit_event(connection, "restore", [("entity", entity_id)], before={"deleted_at": before.deleted_at}, after={"deleted_at": ""}, notes="Entity restored from Recycle Bin")
    if before.type == "person":
        from app.relationship_inference import recompute_inferences
        recompute_inferences(connection, "person_restored", entity_id)
    else:
        connection.commit()
    return True


def permanent_delete_entity(connection: sqlite3.Connection, entity_id: int) -> tuple[str, str]:
    record = get_entity_by_id(connection, entity_id, include_deleted=True)
    if record is None or not record.is_deleted:
        raise ValueError("Only deleted records can be permanently deleted.")
    file_path = record.metadata.get("file_path", "") if record.type == "document" else ""
    from app.audit import record_audit_event
    record_audit_event(connection, "permanent_delete", [("entity", entity_id)], before=record.to_form_values(), notes="Entity permanently deleted from Recycle Bin")
    connection.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
    connection.commit()
    return record.type, file_path


def entity_dependency_counts(connection: sqlite3.Connection, entity_id: int) -> dict[str, int]:
    relationship_count = connection.execute("SELECT COUNT(*) FROM relationships WHERE source_entity_id=? OR target_entity_id=?", (entity_id, entity_id)).fetchone()[0]
    journal_count = connection.execute("SELECT COUNT(*) FROM journal_entries WHERE entity_id=?", (entity_id,)).fetchone()[0]
    return {"relationships": int(relationship_count), "journal_entries": int(journal_count)}


def with_canonical_person_name(
    definition: EntityDefinition, values: dict[str, str]
) -> dict[str, str]:
    if definition.type != "person":
        return values
    canonical_values = dict(values)
    canonical_values["display_name"] = " ".join(
        part.strip()
        for part in (values.get("given_name", ""), values.get("family_name", ""))
        if part.strip()
    )
    return canonical_values


def validate_entity_values(
    definition: EntityDefinition, values: dict[str, str]
) -> list[str]:
    errors = []
    if definition.type == "person" and not values.get("given_name", "").strip():
        errors.append("Given name is required.")
    elif definition.type != "person" and not values.get("display_name", "").strip():
        errors.append(f"{definition.singular} name is required.")
    for field in definition.fields:
        value = values.get(field.name, "").strip()
        if field.options and not field.allow_custom and value and value not in field.options:
            errors.append(f"{field.label} is invalid.")
        structured_error = validate_structured_value(value, field.value_kind, field.label)
        if structured_error:
            errors.append(structured_error)
    return errors


def normalise_form_values(
    definition: EntityDefinition, raw_values: dict[str, Any]
) -> dict[str, str]:
    values = {
        "display_name": str(raw_values.get("display_name", "")).strip(),
        "notes": str(raw_values.get("notes", "")).strip(),
    }
    for field in definition.fields:
        raw_value = str(raw_values.get(field.name, field.default)).strip() or field.default
        values[field.name] = normalise_structured_value(raw_value, field.value_kind)
    if definition.type == "person":
        values["display_name"] = " ".join(
            part
            for part in (values.get("given_name", ""), values.get("family_name", ""))
            if part
        )
    return values


def insert_typed_row(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
    field_names = list(definition.field_names)
    columns = ["entity_id", *field_names]
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(
        "INSERT INTO {table} ({columns}) VALUES ({placeholders})".format(
            table=sql_identifier(definition.table),
            columns=", ".join(sql_identifier(column) for column in columns),
            placeholders=placeholders,
        ),
        [entity_id, *[values.get(name, "") for name in field_names]],
    )


def update_typed_row(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
    assignments = ", ".join(
        f"{sql_identifier(field.name)} = ?" for field in definition.fields
    )
    if not assignments:
        return
    connection.execute(
        "UPDATE {table} SET {assignments} WHERE entity_id = ?".format(
            table=sql_identifier(definition.table),
            assignments=assignments,
        ),
        [*[values.get(field.name, "") for field in definition.fields], entity_id],
    )


def entity_matches_query(record: EntityRecord, query: str) -> bool:
    haystack = " ".join(
        [record.display_name, record.summary, record.notes, record.definition.singular, record.definition.plural]
        + list(record.metadata.values())
    ).lower()
    return query.lower() in haystack
