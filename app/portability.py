"""Versioned, checksummed local export, import, backup, and recovery bundles."""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from app.audit import record_audit_event
from app.db_schema import SCHEMA_MIGRATION_IDS, connect
from app.entities import ALL_DEFINITIONS_BY_TYPE
from app.entity_repository import validate_entity_values
from app.relationships import DATE_PRECISIONS, RELATIONSHIP_STATUSES
from app.structured_values import validate_structured_value

FORMAT_NAME = "project-e-portable-bundle"
FORMAT_VERSION = 1
DATABASE_MEMBER = "data/project-e.sqlite3"


@dataclass(frozen=True)
class BundlePreview:
    entities: int
    relationships: int
    documents: int
    deleted_entities: int
    deleted_relationships: int
    exported_at: str


def create_bundle(database_path: Path, document_storage_dir: Path) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "project-e.sqlite3"
        source = connect(database_path)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        members = {DATABASE_MEMBER: snapshot.read_bytes()}
        with connect(snapshot) as connection:
            for row in connection.execute(
                "SELECT file_path FROM documents WHERE file_path<>'' ORDER BY entity_id"
            ):
                relative = _safe_document_relative(row["file_path"])
                path = document_storage_dir.parent / relative
                if not path.is_file():
                    raise ValueError(f"Stored document is missing: {relative.as_posix()}")
                members[f"files/{relative.name}"] = path.read_bytes()
            counts = _counts(connection)
        manifest = {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "exported_at": _now(),
            "counts": counts,
            "members": {name: _sha256(value) for name, value in members.items()},
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
            for name, value in members.items():
                archive.writestr(name, value)
        return output.getvalue()


def inspect_bundle(bundle: bytes) -> BundlePreview:
    with tempfile.TemporaryDirectory() as directory:
        manifest, database_path, document_members = _extract_and_validate(
            bundle, Path(directory)
        )
        with connect(database_path) as connection:
            _validate_database(connection)
            counts = _counts(connection)
            if counts != manifest.get("counts"):
                raise ValueError("Bundle record counts do not match its manifest.")
            expected_files = {
                f"files/{_safe_document_relative(row['file_path']).name}"
                for row in connection.execute(
                    "SELECT file_path FROM documents WHERE file_path<>''"
                )
            }
            if expected_files != set(document_members):
                raise ValueError(
                    "Bundle document files do not match canonical Document records."
                )
        return BundlePreview(exported_at=manifest["exported_at"], **counts)


def apply_import_bundle(
    bundle: bytes,
    database_path: Path,
    document_storage_dir: Path,
    backup_dir: Path,
    *,
    require_empty: bool = True,
) -> BundlePreview:
    preview = inspect_bundle(bundle)
    if require_empty and not _target_is_empty(database_path, document_storage_dir):
        raise ValueError("Import requires an empty database and document store.")
    backup_dir.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        create_recovery_backup(
            database_path, document_storage_dir, backup_dir, "before-import"
        )
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=database_path.parent) as directory:
        staging = Path(directory)
        _manifest, staged_database, document_members = _extract_and_validate(
            bundle, staging
        )
        with connect(staged_database) as connection:
            _validate_database(connection)
        staged_documents = staging / "documents"
        staged_documents.mkdir()
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            for member in document_members:
                target = staged_documents / PurePosixPath(member).name
                target.write_bytes(archive.read(member))
        old_documents = staging / "previous-documents"
        document_storage_dir.parent.mkdir(parents=True, exist_ok=True)
        if document_storage_dir.exists():
            os.replace(document_storage_dir, old_documents)
        replacement_database = database_path.with_suffix(database_path.suffix + ".importing")
        try:
            os.replace(staged_documents, document_storage_dir)
            shutil.copy2(staged_database, replacement_database)
            os.replace(replacement_database, database_path)
        except Exception:
            if replacement_database.exists():
                replacement_database.unlink()
            if document_storage_dir.exists():
                shutil.rmtree(document_storage_dir)
            if old_documents.exists():
                os.replace(old_documents, document_storage_dir)
            raise
    with connect(database_path) as connection:
        record_audit_event(
            connection,
            "import",
            [("system", 0)],
            after={"entities": preview.entities, "relationships": preview.relationships},
            notes="Portable bundle imported after validation and backup",
            provenance="imported",
        )
        connection.commit()
    return preview


def create_recovery_backup(
    database_path: Path,
    document_storage_dir: Path,
    backup_dir: Path,
    reason: str,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"{stamp}-{reason}-{uuid.uuid4().hex[:8]}.zip"
    path.write_bytes(create_bundle(database_path, document_storage_dir))
    return path


def restore_recovery_bundle(
    backup_path: Path,
    database_path: Path,
    document_storage_dir: Path,
    backup_dir: Path,
) -> BundlePreview:
    return apply_import_bundle(
        backup_path.read_bytes(),
        database_path,
        document_storage_dir,
        backup_dir,
        require_empty=False,
    )


def stage_bundle(bundle: bytes, staging_dir: Path) -> str:
    inspect_bundle(bundle)
    staging_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    (staging_dir / f"{token}.zip").write_bytes(bundle)
    return token


def consume_staged_bundle(token: str, staging_dir: Path) -> bytes:
    if len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        raise ValueError("Import preview token is invalid.")
    path = staging_dir / f"{token}.zip"
    if not path.is_file():
        raise ValueError("Import preview has expired or does not exist.")
    content = path.read_bytes()
    path.unlink()
    return content


def _extract_and_validate(bundle: bytes, directory: Path):
    try:
        archive = zipfile.ZipFile(io.BytesIO(bundle))
    except zipfile.BadZipFile as error:
        raise ValueError("Import file is not a valid ZIP bundle.") from error
    with archive:
        names = archive.namelist()
        if any(_unsafe_member(name) for name in names):
            raise ValueError("Bundle contains an unsafe file path.")
        if "manifest.json" not in names or DATABASE_MEMBER not in names:
            raise ValueError("Bundle is missing its manifest or database.")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Bundle manifest is invalid.") from error
        if (
            manifest.get("format") != FORMAT_NAME
            or manifest.get("version") != FORMAT_VERSION
        ):
            raise ValueError("Bundle format or version is not supported.")
        members = manifest.get("members")
        if not isinstance(members, dict) or set(members) != set(names) - {
            "manifest.json"
        }:
            raise ValueError("Bundle member list does not match its manifest.")
        for name, expected in members.items():
            if _sha256(archive.read(name)) != expected:
                raise ValueError(f"Bundle checksum failed for {name}.")
        database_path = directory / "import.sqlite3"
        database_path.write_bytes(archive.read(DATABASE_MEMBER))
        document_members = [name for name in names if name.startswith("files/")]
    return manifest, database_path, document_members


def _validate_database(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Imported database failed SQLite integrity checks.")
    if connection.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Imported database contains broken references.")
    migrations = {
        row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations")
    }
    if not set(SCHEMA_MIGRATION_IDS) <= migrations:
        raise ValueError("Imported database is not at the current supported schema.")
    from app.calendar_service import validate_stored_calendar
    calendars = list(connection.execute("SELECT id FROM calendars"))
    if not calendars:
        raise ValueError("Imported database has no Calendar.")
    defaults = [row for row in connection.execute(
        "SELECT id FROM calendars WHERE is_default = 1 AND archived_at = ''"
    )]
    if len(defaults) != 1:
        raise ValueError("Imported database must have one active default Calendar.")
    for row in calendars:
        errors = validate_stored_calendar(connection, int(row["id"]))
        if errors:
            raise ValueError(f"Calendar {row['id']} is invalid: {'; '.join(errors)}")
    for row in connection.execute("SELECT id,type FROM entities"):
        definition = ALL_DEFINITIONS_BY_TYPE.get(row["type"])
        if definition is None:
            raise ValueError(f"Entity {row['id']} has an unknown type.")
        if not connection.execute(
            f"SELECT 1 FROM {definition.table} WHERE entity_id=?", (row["id"],)
        ).fetchone():
            raise ValueError(f"Entity {row['id']} is missing its typed record.")
        errors = validate_entity_values(
            definition, _entity_values_for_validation(connection, row["id"], definition), connection
        )
        if row["type"] == "event":
            from app.event_service import validate_stored_event
            errors.extend(validate_stored_event(connection, int(row["id"])))
        if errors:
            raise ValueError(f"Entity {row['id']} is invalid: {'; '.join(errors)}")
    entity_types = {
        int(row["id"]): row["type"]
        for row in connection.execute("SELECT id,type FROM entities")
    }
    for row in connection.execute("SELECT * FROM relationships"):
        source_type = entity_types.get(int(row["source_entity_id"]))
        target_type = entity_types.get(int(row["target_entity_id"]))
        if not source_type or not target_type or not _relationship_type_supports(connection, row["type"], source_type, target_type):
            raise ValueError(
                f"Relationship {row['id']} has invalid endpoints or type."
            )
        if row["source_entity_id"] == row["target_entity_id"]:
            raise ValueError(f"Relationship {row['id']} references one entity twice.")
        if row["status"] not in RELATIONSHIP_STATUSES:
            raise ValueError(f"Relationship {row['id']} has an invalid status.")
        if row["started_at_precision"] not in DATE_PRECISIONS or row["ended_at_precision"] not in DATE_PRECISIONS:
            raise ValueError(f"Relationship {row['id']} has invalid date precision.")
        for field_name, label in (("started_at", "Started"), ("ended_at", "Ended")):
            error = validate_structured_value(row[field_name], "date", label)
            if error:
                raise ValueError(f"Relationship {row['id']} is invalid: {error}")


def _relationship_type_supports(connection, type_key, source_type, target_type):
    row = connection.execute("""SELECT definition.source_entity_type, definition.target_entity_type, definition.directional
        FROM relationship_type_definitions definition
        JOIN taxonomy_entries entry ON entry.id=definition.taxonomy_entry_id
        JOIN taxonomies taxonomy ON taxonomy.id=entry.taxonomy_id
        WHERE taxonomy.key='relationship_type' AND entry.key=?""", (type_key,)).fetchone()
    if row is None:
        return False
    if (source_type, target_type) == (row["source_entity_type"], row["target_entity_type"]):
        return True
    return not row["directional"] and (target_type, source_type) == (row["source_entity_type"], row["target_entity_type"])


def _entity_values_for_validation(connection, entity_id, definition):
    entity = connection.execute("SELECT display_name,notes FROM entities WHERE id=?", (entity_id,)).fetchone()
    typed = connection.execute(f"SELECT * FROM {definition.table} WHERE entity_id=?", (entity_id,)).fetchone()
    values = {"display_name": entity["display_name"], "notes": entity["notes"]}
    for field in definition.fields:
        if field.storage_kind == "scalar":
            values[field.name] = typed[field.name]
        elif field.storage_kind == "alias":
            values[field.name] = "\n".join(
                row[0] for row in connection.execute("SELECT value FROM entity_aliases WHERE entity_id=? ORDER BY id", (entity_id,))
            )
        elif field.storage_kind == "reference":
            values[field.name] = ",".join(str(row[0]) for row in connection.execute("SELECT reference_item_id FROM entity_reference_values WHERE entity_id=? AND field_name=? ORDER BY position", (entity_id, field.name)))
        elif field.storage_kind == "measurement":
            measurement = connection.execute("SELECT canonical_value,display_unit_id FROM entity_measurements WHERE entity_id=? AND field_name=?", (entity_id, field.name)).fetchone()
            values[field.name] = measurement["canonical_value"] if measurement else ""
            values[f"{field.name}__unit"] = str(measurement["display_unit_id"]) if measurement else ""
        elif field.storage_kind == "taxonomy":
            values[field.name] = str(typed["taxonomy_entry_id"] or "")
    return values


def _target_is_empty(database_path: Path, document_storage_dir: Path) -> bool:
    if document_storage_dir.exists() and any(document_storage_dir.iterdir()):
        return False
    if not database_path.exists():
        return True
    with connect(database_path) as connection:
        user_tables = ("entities", "relationships", "journal_entries", "audit_events", "data_quality_finding_state", "entity_edit_history")
        return all(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0 for table in user_tables)


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "entities": connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        "relationships": connection.execute(
            "SELECT COUNT(*) FROM relationships"
        ).fetchone()[0],
        "documents": connection.execute(
            "SELECT COUNT(*) FROM documents WHERE file_path<>''"
        ).fetchone()[0],
        "deleted_entities": connection.execute(
            "SELECT COUNT(*) FROM entities WHERE deleted_at<>''"
        ).fetchone()[0],
        "deleted_relationships": connection.execute(
            "SELECT COUNT(*) FROM relationships WHERE deleted_at<>''"
        ).fetchone()[0],
    }


def _safe_document_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) != 2
        or path.parts[0] != "documents"
        or ".." in path.parts
    ):
        raise ValueError(f"Document path is unsafe: {value}")
    return path


def _unsafe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or ".." in path.parts or "\\" in name


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()
