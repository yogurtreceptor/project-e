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
        WHERE entities.type = ?
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
        "SELECT type, COUNT(*) AS count FROM entities GROUP BY type"
    ).fetchall()
    return {row["type"]: row["count"] for row in rows}


def get_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, entity_id: int
) -> EntityRecord | None:
    row = connection.execute(
        """
        SELECT entities.*, typed.*
        FROM entities
        JOIN {table} AS typed ON typed.entity_id = entities.id
        WHERE entities.id = ? AND entities.type = ?
        """.format(table=sql_identifier(definition.table)),
        (entity_id, definition.type),
    ).fetchone()
    if row is None:
        return None
    return to_entity_record(definition, row)


def get_entity_by_id(connection: sqlite3.Connection, entity_id: int) -> EntityRecord | None:
    row = connection.execute("SELECT id, type FROM entities WHERE id = ?", (entity_id,)).fetchone()
    if row is None:
        return None
    definition = DEFINITIONS_BY_TYPE.get(row["type"])
    if definition is None:
        return None
    return get_entity(connection, definition, entity_id)


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
        from app.entity_merge import record_entity_edit
        record_entity_edit(connection, entity_id, before.to_form_values(), values)
    connection.commit()


def delete_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, entity_id: int
) -> None:
    connection.execute(
        "DELETE FROM entities WHERE id = ? AND type = ?", (entity_id, definition.type)
    )
    connection.commit()


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
