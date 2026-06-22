import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.entities import (
    DEFINITIONS_BY_TYPE,
    ENTITY_DEFINITIONS,
    EntityDefinition,
    EntityRecord,
    to_entity_record,
)
from app.relationships import (
    DATE_PRECISIONS,
    RELATIONSHIP_STATUSES,
    RELATIONSHIP_TYPES_BY_KEY,
    RelationshipRecord,
    relationship_type_is_valid_for_pair,
    split_relationship_choice,
)


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
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ({allowed_entity_type_sql()})),
            display_name TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_viewed_at TEXT NOT NULL DEFAULT '',
            is_favourite INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type_name
            ON entities (type, display_name);
        """
    )
    ensure_entity_columns(connection)
    ensure_entity_type_constraint(connection)
    for definition in ENTITY_DEFINITIONS:
        create_typed_table(connection, definition)
        ensure_typed_columns(connection, definition)
    create_relationship_table(connection)


def ensure_entity_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
    if "last_viewed_at" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN last_viewed_at TEXT NOT NULL DEFAULT ''")
    if "is_favourite" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN is_favourite INTEGER NOT NULL DEFAULT 0")


def ensure_entity_type_constraint(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'entities'"
    ).fetchone()
    create_sql = row["sql"] if row else ""
    if all(sql_literal(definition.type) in create_sql for definition in ENTITY_DEFINITIONS):
        return

    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.executescript(
            f"""
            CREATE TABLE entities_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ({allowed_entity_type_sql()})),
                display_name TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_viewed_at TEXT NOT NULL DEFAULT '',
                is_favourite INTEGER NOT NULL DEFAULT 0
            );

            INSERT INTO entities_new (
                id, type, display_name, summary, notes,
                created_at, updated_at, last_viewed_at, is_favourite
            )
            SELECT
                id, type, display_name, summary, notes,
                created_at, updated_at, last_viewed_at, is_favourite
            FROM entities;

            DROP TABLE entities;
            ALTER TABLE entities_new RENAME TO entities;

            CREATE INDEX IF NOT EXISTS idx_entities_type_name
                ON entities (type, display_name);
            """
        )
        connection.commit()
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


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


def ensure_typed_columns(connection: sqlite3.Connection, definition: EntityDefinition) -> None:
    table = sql_identifier(definition.table)
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    for field in definition.fields:
        if field.name not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {sql_identifier(field.name)} TEXT NOT NULL DEFAULT ''"
            )
            columns.add(field.name)
        migrate_previous_field_values(connection, definition, field, columns)
        migrate_field_value_aliases(connection, definition, field, columns)


def migrate_previous_field_values(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    field,
    columns: set[str],
) -> None:
    table = sql_identifier(definition.table)
    target = sql_identifier(field.name)
    for previous_name in field.previous_names:
        if previous_name not in columns:
            continue
        previous = sql_identifier(previous_name)
        connection.execute(
            f"""
            UPDATE {table}
            SET {target} = {previous}
            WHERE {target} = '' AND {previous} <> ''
            """
        )


def migrate_field_value_aliases(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    field,
    columns: set[str],
) -> None:
    if field.name not in columns:
        return
    table = sql_identifier(definition.table)
    column = sql_identifier(field.name)
    for old_value, new_value in field.value_aliases:
        connection.execute(
            f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
            (new_value, old_value),
        )


def create_relationship_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            started_at TEXT NOT NULL DEFAULT '',
            started_at_precision TEXT NOT NULL DEFAULT 'exact',
            ended_at TEXT NOT NULL DEFAULT '',
            ended_at_precision TEXT NOT NULL DEFAULT 'exact',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (source_entity_id <> target_entity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_relationships_source
            ON relationships (source_entity_id);

        CREATE INDEX IF NOT EXISTS idx_relationships_target
            ON relationships (target_entity_id);

        CREATE INDEX IF NOT EXISTS idx_relationships_type
            ON relationships (type);
        """
    )
    ensure_relationship_columns(connection)


def ensure_relationship_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(relationships)")}
    if "started_at_precision" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN started_at_precision TEXT NOT NULL DEFAULT 'exact'")
    if "ended_at_precision" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN ended_at_precision TEXT NOT NULL DEFAULT 'exact'")


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
    for field in definition.fields:
        value = values.get(field.name, "").strip()
        if field.options and not field.allow_custom and value and value not in field.options:
            errors.append(f"{field.label} is invalid.")
    if definition.type == "asset":
        value = values.get("value", "").strip()
        if value and not value.isdecimal():
            errors.append("Value must be a whole number without a dollar sign.")
    return errors


def normalise_form_values(
    definition: EntityDefinition, raw_values: dict[str, Any]
) -> dict[str, str]:
    values = {
        "display_name": str(raw_values.get("display_name", "")).strip(),
        "notes": str(raw_values.get("notes", "")).strip(),
        "workflow_mode": str(raw_values.get("workflow_mode", "existing")).strip() or "existing",
    }
    for field in definition.fields:
        values[field.name] = str(raw_values.get(field.name, field.default)).strip() or field.default
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


def list_relationships(connection: sqlite3.Connection) -> list[RelationshipRecord]:
    rows = connection.execute(
        """
        SELECT *
        FROM relationships
        ORDER BY updated_at DESC, id DESC
        """
    ).fetchall()
    return [to_relationship_record(connection, row) for row in rows]


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
    return [to_relationship_record(connection, row) for row in rows]


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
        "started_at": str(raw_values.get("started_at", "")).strip(),
        "started_at_precision": str(raw_values.get("started_at_precision", "exact")).strip() or "exact",
        "ended_at": str(raw_values.get("ended_at", "")).strip(),
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



def list_recent_entities(connection: sqlite3.Connection, limit: int = 8) -> list[EntityRecord]:
    rows = connection.execute(
        """
        SELECT id
        FROM entities
        WHERE last_viewed_at <> ''
        ORDER BY last_viewed_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [entity for row in rows if (entity := get_entity_by_id(connection, int(row["id"]))) is not None]


def mark_entity_viewed(connection: sqlite3.Connection, entity_id: int) -> None:
    connection.execute(
        "UPDATE entities SET last_viewed_at = ? WHERE id = ?",
        (utc_now(), entity_id),
    )
    connection.commit()


def list_favourite_entities(connection: sqlite3.Connection, limit: int = 8) -> list[EntityRecord]:
    rows = connection.execute(
        """
        SELECT id
        FROM entities
        WHERE is_favourite = 1
        ORDER BY lower(display_name), id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [entity for row in rows if (entity := get_entity_by_id(connection, int(row["id"]))) is not None]


def set_entity_favourite(connection: sqlite3.Connection, entity_id: int, is_favourite: bool) -> None:
    connection.execute(
        "UPDATE entities SET is_favourite = ?, updated_at = ? WHERE id = ?",
        (1 if is_favourite else 0, utc_now(), entity_id),
    )
    connection.commit()


def search_entities(
    connection: sqlite3.Connection,
    query: str = "",
    entity_type: str = "",
    favourites_only: bool = False,
) -> list[dict[str, object]]:
    query = query.strip()
    records = list_all_entities(connection)
    if entity_type:
        records = [record for record in records if record.type == entity_type]
    if favourites_only:
        records = [record for record in records if record.is_favourite]

    results = []
    for record in records:
        direct_match = not query or entity_matches_query(record, query)
        relationship_matches = matching_relationships_for_entity(connection, record.id, query) if query else []
        if direct_match or relationship_matches:
            results.append(
                {
                    "entity": record,
                    "matched_relationships": relationship_matches,
                    "relationship_count": len(list_relationships_for_entity(connection, record.id)),
                }
            )
    return sorted(results, key=lambda result: (result["entity"].display_name.lower(), result["entity"].id))


def entity_matches_query(record: EntityRecord, query: str) -> bool:
    haystack = " ".join(
        [record.display_name, record.summary, record.notes, record.definition.singular, record.definition.plural]
        + list(record.metadata.values())
    ).lower()
    return query.lower() in haystack


def matching_relationships_for_entity(
    connection: sqlite3.Connection, entity_id: int, query: str
) -> list[RelationshipRecord]:
    matches = []
    lowered = query.lower()
    for relationship in list_relationships_for_entity(connection, entity_id):
        other = relationship.other_entity(entity_id)
        haystack = " ".join(
            [
                relationship.label_from(entity_id),
                relationship.type.inverse_label,
                relationship.status,
                relationship.notes,
                other.display_name,
                other.summary,
                other.definition.singular,
                other.definition.plural,
            ]
            + list(other.metadata.values())
        ).lower()
        if lowered in haystack:
            matches.append(relationship)
    return matches

def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def allowed_entity_type_sql() -> str:
    return ", ".join(sql_literal(definition.type) for definition in ENTITY_DEFINITIONS)
