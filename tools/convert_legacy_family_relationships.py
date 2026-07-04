#!/usr/bin/env python3
"""Convert legacy gendered family relationships to canonical taxonomy types.

Dry-run is the default. Pass --apply to make changes; an SQLite backup is made
before the transaction begins.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Mapping:
    canonical_key: str
    reverse: bool = False


LEGACY_FAMILY_MAPPINGS = {
    "mother_of": Mapping("parent_child"), "father_of": Mapping("parent_child"),
    "parent_of": Mapping("parent_child"), "child_of": Mapping("parent_child", True),
    "son_of": Mapping("parent_child", True), "daughter_of": Mapping("parent_child", True),
    "grandmother_of": Mapping("grandparent_child"), "grandfather_of": Mapping("grandparent_child"),
    "grandparent_of": Mapping("grandparent_child"), "grandchild_of": Mapping("grandparent_child", True),
    "grandson_of": Mapping("grandparent_child", True), "granddaughter_of": Mapping("grandparent_child", True),
    "brother_of": Mapping("sibling_of"), "sister_of": Mapping("sibling_of"),
    "aunt_of": Mapping("aunt_uncle_niece_nephew"), "uncle_of": Mapping("aunt_uncle_niece_nephew"),
    "niece_of": Mapping("aunt_uncle_niece_nephew", True), "nephew_of": Mapping("aunt_uncle_niece_nephew", True),
}

CANONICAL_FAMILY_KEYS = {"parent_child", "sibling_of", "grandparent_child", "aunt_uncle_niece_nephew", "cousin_of"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("database", type=Path, help="Path to the Project E SQLite database")
    result.add_argument("--apply", action="store_true", help="Apply the reported conversions")
    result.add_argument("--backup", type=Path, help="Backup path (only valid with --apply)")
    return result


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def validate_schema(connection: sqlite3.Connection) -> dict[str, int]:
    required = {"id", "source_entity_id", "target_entity_id", "type", "taxonomy_entry_id"}
    missing_columns = required - table_columns(connection, "relationships")
    if missing_columns:
        raise RuntimeError("Database is not on the taxonomy schema; missing relationships columns: " + ", ".join(sorted(missing_columns)))
    entries = {row[0]: int(row[1]) for row in connection.execute(
        """SELECT e.key,e.id FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id
           WHERE t.key='relationship_type'""")}
    missing_entries = CANONICAL_FAMILY_KEYS - entries.keys()
    if missing_entries:
        raise RuntimeError("Canonical relationship taxonomy entries are missing: " + ", ".join(sorted(missing_entries)))
    return entries


def planned_changes(connection: sqlite3.Connection, entries: dict[str, int]) -> tuple[list[dict], list[dict]]:
    placeholders = ",".join("?" for _ in LEGACY_FAMILY_MAPPINGS)
    rows = connection.execute(
        f"""SELECT r.id,r.source_entity_id,r.target_entity_id,r.type,
                   s.display_name,t.display_name FROM relationships r
            JOIN entities s ON s.id=r.source_entity_id JOIN entities t ON t.id=r.target_entity_id
            WHERE r.type IN ({placeholders}) ORDER BY r.id""", tuple(LEGACY_FAMILY_MAPPINGS)).fetchall()
    changes, conflicts = [], []
    for row in rows:
        mapping = LEGACY_FAMILY_MAPPINGS[row[3]]
        source_id, target_id, source_name, target_name = int(row[1]), int(row[2]), row[4], row[5]
        if mapping.reverse:
            source_id, target_id, source_name, target_name = target_id, source_id, target_name, source_name
        duplicate = connection.execute(
            "SELECT id FROM relationships WHERE id<>? AND source_entity_id=? AND target_entity_id=? AND type=?",
            (row[0], source_id, target_id, mapping.canonical_key)).fetchone()
        item = {"id": int(row[0]), "old_key": row[3], "new_key": mapping.canonical_key,
                "source_id": source_id, "target_id": target_id, "source_name": source_name,
                "target_name": target_name, "taxonomy_entry_id": entries[mapping.canonical_key]}
        if duplicate:
            item["duplicate_id"] = int(duplicate[0]); conflicts.append(item)
        else:
            changes.append(item)
    return changes, conflicts


def backup_database(connection: sqlite3.Connection, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Backup already exists: {destination}")
    with sqlite3.connect(destination) as backup:
        connection.backup(backup)


def apply_changes(connection: sqlite3.Connection, changes: list[dict]) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        for item in changes:
            connection.execute(
                "UPDATE relationships SET source_entity_id=?,target_entity_id=?,type=?,taxonomy_entry_id=? WHERE id=?",
                (item["source_id"], item["target_id"], item["new_key"], item["taxonomy_entry_id"], item["id"]))
        connection.commit()
    except Exception:
        connection.rollback(); raise


def default_backup_path(database: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return database.with_name(f"{database.name}.pre-family-conversion-{stamp}.backup")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.backup and not args.apply:
        print("error: --backup requires --apply", file=sys.stderr); return 2
    database = args.database.expanduser().resolve()
    if not database.is_file():
        print(f"error: database does not exist: {database}", file=sys.stderr); return 2
    try:
        mode = "rw" if args.apply else "ro"
        with sqlite3.connect(f"file:{database}?mode={mode}", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            entries = validate_schema(connection)
            changes, conflicts = planned_changes(connection, entries)
            print(f"{'APPLY' if args.apply else 'DRY RUN'}: {database}")
            for item in changes:
                print(f"  #{item['id']}: {item['old_key']} -> {item['new_key']} | {item['source_name']} (#{item['source_id']}) -> {item['target_name']} (#{item['target_id']})")
            for item in conflicts:
                print(f"  CONFLICT #{item['id']}: canonical duplicate #{item['duplicate_id']} exists; left unchanged")
            if not args.apply:
                print(f"Would convert {len(changes)} relationship(s); {len(conflicts)} conflict(s).")
                print("Run again with --apply to convert. Canonical and unknown types are untouched.")
                return 1 if conflicts else 0
            backup = (args.backup or default_backup_path(database)).expanduser().resolve()
            backup_database(connection, backup)
            apply_changes(connection, changes)
            print(f"Backup: {backup}")
            print(f"Converted {len(changes)} relationship(s); {len(conflicts)} conflict(s) left unchanged.")
            return 1 if conflicts else 0
    except (sqlite3.Error, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
