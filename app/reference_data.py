"""Generic, local reference-data catalogue and entity value links."""

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class ReferenceItem:
    id: int
    type_key: str
    key: str
    name: str
    code: str
    parent_id: int | None


REFERENCE_DATA_SEED = {
    "country": (
        ("au", "Australia", "AU", None),
        ("gb", "United Kingdom", "GB", None),
    ),
    "region": (
        ("au-qld", "Queensland", "QLD", ("country", "au")),
    ),
    "language": (
        ("en", "English", "en", None),
        ("fr", "French", "fr", None),
    ),
    "currency": (
        ("aud", "Australian dollar", "AUD", None),
    ),
}


def create_reference_data_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS reference_data_types (
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS reference_data_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_key TEXT NOT NULL REFERENCES reference_data_types(key),
            key TEXT NOT NULL,
            name TEXT NOT NULL,
            code TEXT NOT NULL DEFAULT '',
            parent_id INTEGER REFERENCES reference_data_items(id),
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            UNIQUE (type_key, key)
        );
        CREATE INDEX IF NOT EXISTS idx_reference_items_type_name
            ON reference_data_items(type_key, active, name);
        CREATE TABLE IF NOT EXISTS entity_reference_values (
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            field_name TEXT NOT NULL,
            reference_item_id INTEGER NOT NULL REFERENCES reference_data_items(id),
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (entity_id, field_name, reference_item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_entity_reference_values_item
            ON entity_reference_values(reference_item_id);
        """
    )
    seed_reference_data(connection)


def seed_reference_data(connection: sqlite3.Connection) -> None:
    labels = {
        "country": "Countries",
        "region": "States / regions",
        "language": "Languages",
        "currency": "Currencies",
    }
    for type_key, name in labels.items():
        connection.execute(
            "INSERT OR IGNORE INTO reference_data_types(key, name) VALUES (?, ?)",
            (type_key, name),
        )
    for type_key, rows in REFERENCE_DATA_SEED.items():
        for key, name, code, parent in rows:
            parent_id = None
            if parent:
                parent_row = connection.execute(
                    "SELECT id FROM reference_data_items WHERE type_key=? AND key=?",
                    parent,
                ).fetchone()
                parent_id = int(parent_row["id"]) if parent_row else None
            connection.execute(
                """INSERT OR IGNORE INTO reference_data_items
                   (type_key, key, name, code, parent_id) VALUES (?, ?, ?, ?, ?)""",
                (type_key, key, name, code, parent_id),
            )


def list_reference_items(
    connection: sqlite3.Connection, type_key: str, *, include_inactive: bool = False
) -> list[ReferenceItem]:
    active_clause = "" if include_inactive else "AND active = 1"
    rows = connection.execute(
        f"""SELECT id, type_key, key, name, code, parent_id
            FROM reference_data_items
            WHERE type_key = ? {active_clause}
            ORDER BY lower(name), id""",
        (type_key,),
    ).fetchall()
    return [_to_reference_item(row) for row in rows]


def get_reference_item(
    connection: sqlite3.Connection, item_id: int
) -> ReferenceItem | None:
    row = connection.execute(
        """SELECT id, type_key, key, name, code, parent_id
           FROM reference_data_items WHERE id = ?""",
        (item_id,),
    ).fetchone()
    return _to_reference_item(row) if row else None


def create_reference_item(
    connection: sqlite3.Connection,
    type_key: str,
    key: str,
    name: str,
    *,
    code: str = "",
    parent_id: int | None = None,
) -> int:
    if not connection.execute(
        "SELECT 1 FROM reference_data_types WHERE key = ?", (type_key,)
    ).fetchone():
        raise ValueError(f"Unknown reference data type: {type_key}")
    cursor = connection.execute(
        """INSERT INTO reference_data_items(type_key, key, name, code, parent_id)
           VALUES (?, ?, ?, ?, ?)""",
        (type_key, key.strip(), name.strip(), code.strip(), parent_id),
    )
    return int(cursor.lastrowid)


def replace_entity_reference_values(
    connection: sqlite3.Connection,
    entity_id: int,
    field_name: str,
    item_ids: list[int],
    expected_type: str,
) -> None:
    unique_ids = list(dict.fromkeys(item_ids))
    if unique_ids:
        placeholders = ", ".join("?" for _ in unique_ids)
        count = connection.execute(
            f"""SELECT COUNT(*) FROM reference_data_items
                WHERE id IN ({placeholders}) AND type_key = ? AND active = 1""",
            (*unique_ids, expected_type),
        ).fetchone()[0]
        if count != len(unique_ids):
            raise ValueError(f"Invalid {expected_type} reference value.")
    connection.execute(
        "DELETE FROM entity_reference_values WHERE entity_id=? AND field_name=?",
        (entity_id, field_name),
    )
    connection.executemany(
        """INSERT INTO entity_reference_values
           (entity_id, field_name, reference_item_id, position) VALUES (?, ?, ?, ?)""",
        [(entity_id, field_name, item_id, position) for position, item_id in enumerate(unique_ids)],
    )


def list_entity_reference_values(
    connection: sqlite3.Connection, entity_id: int, field_name: str
) -> list[ReferenceItem]:
    rows = connection.execute(
        """SELECT item.id, item.type_key, item.key, item.name, item.code, item.parent_id
           FROM entity_reference_values value
           JOIN reference_data_items item ON item.id = value.reference_item_id
           WHERE value.entity_id=? AND value.field_name=?
           ORDER BY value.position, item.id""",
        (entity_id, field_name),
    ).fetchall()
    return [_to_reference_item(row) for row in rows]


def _to_reference_item(row: sqlite3.Row) -> ReferenceItem:
    return ReferenceItem(
        id=int(row["id"]),
        type_key=row["type_key"],
        key=row["key"],
        name=row["name"],
        code=row["code"],
        parent_id=int(row["parent_id"]) if row["parent_id"] is not None else None,
    )
