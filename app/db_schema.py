import sqlite3
from pathlib import Path

from app.db_support import allowed_entity_type_sql, sql_identifier, sql_literal, utc_now
from app.entities import ENTITY_DEFINITIONS, EntityDefinition


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
    create_schema_migration_table(connection)
    apply_schema_migrations(connection)
    ensure_current_schema(connection)


def create_schema_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )


def apply_schema_migrations(connection: sqlite3.Connection) -> None:
    applied = {
        row["migration_id"]
        for row in connection.execute("SELECT migration_id FROM schema_migrations")
    }
    for migration_id, migration in SCHEMA_MIGRATIONS:
        if migration_id in applied:
            continue
        migration(connection)
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (migration_id, utc_now()),
        )


def ensure_current_schema(connection: sqlite3.Connection) -> None:
    create_entity_table(connection)
    ensure_entity_columns(connection)
    ensure_entity_type_constraint(connection)
    create_typed_entity_tables(connection)
    create_relationship_table(connection)
    create_entity_history_table(connection)


def create_entity_history_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS entity_edit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entity_edit_history_entity
            ON entity_edit_history (entity_id, created_at);
        """
    )

def create_entity_table(connection: sqlite3.Connection) -> None:
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


def create_typed_entity_tables(connection: sqlite3.Connection) -> None:
    for definition in ENTITY_DEFINITIONS:
        create_typed_table(connection, definition)
        ensure_typed_columns(connection, definition)


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


SCHEMA_MIGRATIONS = (
    ("20260628_01_core_entities", create_entity_table),
    ("20260628_02_typed_entities", create_typed_entity_tables),
    ("20260628_03_relationships", create_relationship_table),
    ("20260628_04_entity_edit_history", create_entity_history_table),
)

SCHEMA_MIGRATION_IDS = tuple(migration_id for migration_id, _ in SCHEMA_MIGRATIONS)
if len(SCHEMA_MIGRATION_IDS) != len(set(SCHEMA_MIGRATION_IDS)):
    raise ValueError("Schema migration identifiers must be unique.")
