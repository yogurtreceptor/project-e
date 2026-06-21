import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord, to_entity_record


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(database_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database(database_path: Path | str) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        create_schema(connection)


def create_schema(connection: sqlite3.Connection) -> None:
    allowed_types = ", ".join(sql_literal(definition.type) for definition in ENTITY_DEFINITIONS)
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ({allowed_types})),
            display_name TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type_name
            ON entities (type, display_name);
        """
    )
    for definition in ENTITY_DEFINITIONS:
        create_typed_table(connection, definition)


def create_typed_table(connection: sqlite3.Connection, definition: EntityDefinition) -> None:
    table = sql_identifier(definition.table)
    field_columns = ",\n            ".join(
        f"{sql_identifier(field.name)} TEXT NOT NULL DEFAULT ''"
        for field in definition.fields
    )
    columns_sql = ",\n            " + field_columns if field_columns else ""
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE{columns_sql}
        );
        """
    )


def list_entities(connection: sqlite3.Connection, definition: EntityDefinition) -> list[EntityRecord]:
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
    return [to_entity_record(definition, row) for row in rows]


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


def create_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, values: dict[str, str]
) -> int:
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
    connection.commit()
    return entity_id


def update_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
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
    connection.commit()


def delete_entity(
    connection: sqlite3.Connection, definition: EntityDefinition, entity_id: int
) -> None:
    connection.execute(
        "DELETE FROM entities WHERE id = ? AND type = ?", (entity_id, definition.type)
    )
    connection.commit()


def validate_entity_values(
    definition: EntityDefinition, values: dict[str, str]
) -> list[str]:
    errors = []
    if not values.get("display_name", "").strip():
        errors.append(f"{definition.singular} name is required.")
    return errors


def normalise_form_values(
    definition: EntityDefinition, raw_values: dict[str, Any]
) -> dict[str, str]:
    values = {
        "display_name": str(raw_values.get("display_name", "")).strip(),
        "summary": str(raw_values.get("summary", "")).strip(),
        "notes": str(raw_values.get("notes", "")).strip(),
    }
    for field in definition.fields:
        values[field.name] = str(raw_values.get(field.name, "")).strip()
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


def sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
