import sqlite3
from decimal import Decimal, InvalidOperation
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
from app.reference_data import list_entity_reference_values, replace_entity_reference_values
from app.units import clear_measurement, get_measurement, get_unit, set_measurement


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
    for record in records:
        hydrate_external_fields(connection, record)
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
    record = to_entity_record(definition, row)
    hydrate_external_fields(connection, record)
    return record


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
    sync_external_fields(connection, definition, entity_id, values)
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
    sync_external_fields(connection, definition, entity_id, values)
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
    definition: EntityDefinition, values: dict[str, str],
    connection: sqlite3.Connection | None = None,
) -> list[str]:
    errors = []
    if definition.type == "person" and not values.get("given_name", "").strip():
        errors.append("Given name is required.")
    elif definition.type != "person" and not values.get("display_name", "").strip():
        errors.append(f"{definition.singular} name is required.")
    for field in definition.fields:
        value = values.get(field.name, "").strip()
        if field.storage_kind == "alias":
            aliases = parse_aliases(value)
            if len(aliases) != len({alias.casefold() for alias in aliases}):
                errors.append(f"{field.label} must not contain duplicates.")
            continue
        if field.storage_kind == "measurement":
            if value:
                try:
                    number = Decimal(value)
                    if not number.is_finite() or number <= 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    errors.append(f"{field.label} must be a positive number.")
                if not values.get(f"{field.name}__unit", ""):
                    errors.append(f"{field.label} requires a unit.")
                elif connection is not None:
                    unit_id = values[f"{field.name}__unit"]
                    unit = get_unit(connection, int(unit_id)) if unit_id.isdecimal() else None
                    if unit is None or unit.category != field.measurement_category:
                        errors.append(f"{field.label} unit is invalid.")
            continue
        if field.storage_kind == "reference":
            if value and parse_reference_ids(value) is None:
                errors.append(f"{field.label} selection is invalid.")
            elif value and connection is not None:
                item_ids = parse_reference_ids(value) or []
                placeholders = ",".join("?" for _ in item_ids)
                count = connection.execute(
                    f"SELECT COUNT(*) FROM reference_data_items WHERE id IN ({placeholders}) AND type_key=? AND active=1",
                    (*item_ids, field.reference_type),
                ).fetchone()[0]
                if count != len(set(item_ids)):
                    errors.append(f"{field.label} selection is invalid.")
            continue
        if field.storage_kind == "taxonomy":
            if not value or not value.isdecimal():
                errors.append(f"{field.label} is required.")
            elif connection is not None:
                from app.taxonomy import get_entry
                entry = get_entry(connection, int(value))
                if entry is None or entry.taxonomy_key != "organisation_classification":
                    errors.append(f"{field.label} selection is invalid.")
            continue
        if field.options and not field.allow_custom and value and value not in field.options:
            errors.append(f"{field.label} is invalid.")
        structured_error = validate_structured_value(value, field.value_kind, field.label)
        if structured_error:
            errors.append(structured_error)
    optional_groups: dict[str, list] = {}
    for field in definition.fields:
        if field.optional_group:
            optional_groups.setdefault(field.optional_group, []).append(field)
    for fields in optional_groups.values():
        populated = [bool(values.get(field.name, "").strip()) for field in fields]
        if any(populated) and not all(populated):
            label = fields[0].optional_group_label or fields[0].optional_group.replace("_", " ").title()
            errors.append(f"{label} requires both {fields[0].label} and {fields[1].label}.")
    if definition.type == "project" and values.get("started_at") and values.get("ended_at"):
        if values["ended_at"] < values["started_at"]:
            errors.append("Ended / completed must not be before Started.")
    if definition.type == "document" and values.get("document_date") and values.get("expiry_date"):
        if values["expiry_date"] < values["document_date"]:
            errors.append("Expiry date must not be before Document date.")
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
        if field.storage_kind in {"reference", "alias"}:
            raw_value = str(raw_values.get(field.name, "")).strip()
        values[field.name] = normalise_structured_value(raw_value, field.value_kind)
        if field.storage_kind == "measurement":
            values[f"{field.name}__unit"] = str(raw_values.get(f"{field.name}__unit", "")).strip()
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
        f"{sql_identifier(field.name)} = ?" for field in definition.fields if field.typed_column
    )
    if not assignments:
        return
    connection.execute(
        "UPDATE {table} SET {assignments} WHERE entity_id = ?".format(
            table=sql_identifier(definition.table),
            assignments=assignments,
        ),
        [*[values.get(field.name, "") for field in definition.fields if field.typed_column], entity_id],
    )


def parse_aliases(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def hydrate_external_fields(connection: sqlite3.Connection, record: EntityRecord) -> None:
    if record.type == "organisation":
        from app.taxonomy import hydrate_organisation_taxonomy
        hydrate_organisation_taxonomy(connection, record)
    for field in record.definition.fields:
        if field.storage_kind == "reference":
            items = list_entity_reference_values(connection, record.id, field.name)
            record.metadata[field.name] = ", ".join(item.name for item in items)
            record.metadata[f"{field.name}__ids"] = ",".join(str(item.id) for item in items)
        elif field.storage_kind == "measurement":
            measurement = get_measurement(connection, record.id, field.name)
            if measurement:
                record.metadata[field.name] = measurement.display_text
                record.metadata[f"{field.name}__value"] = format(measurement.display_value.normalize(), "f")
                record.metadata[f"{field.name}__unit"] = str(measurement.display_unit.id)
        elif field.storage_kind == "alias":
            rows = connection.execute(
                "SELECT value FROM entity_aliases WHERE entity_id=? ORDER BY lower(value), id",
                (record.id,),
            )
            record.metadata[field.name] = "\n".join(row["value"] for row in rows)


def sync_external_fields(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
    for field in definition.fields:
        if field.storage_kind == "taxonomy":
            from app.taxonomy import assign_organisation_value
            assign_organisation_value(connection, entity_id, values.get(field.name, ""))
            continue
        if field.storage_kind == "reference":
            raw = values.get(field.name, "")
            item_ids = parse_reference_ids(raw)
            if item_ids is not None:
                replace_entity_reference_values(
                    connection, entity_id, field.name, item_ids, field.reference_type
                )
        elif field.storage_kind == "alias":
            connection.execute("DELETE FROM entity_aliases WHERE entity_id=?", (entity_id,))
            connection.executemany(
                "INSERT INTO entity_aliases(entity_id,value,created_at) VALUES(?,?,?)",
                ((entity_id, alias, utc_now()) for alias in parse_aliases(values.get(field.name, ""))),
            )
        elif field.storage_kind == "measurement":
            value = values.get(field.name, "").strip()
            unit_id = values.get(f"{field.name}__unit", "").strip()
            if not value and not unit_id:
                clear_measurement(connection, entity_id, field.name)
            elif value and unit_id.isdecimal():
                set_measurement(
                    connection, entity_id, field.name, field.measurement_category,
                    value, int(unit_id),
                )


def parse_reference_ids(value: str) -> list[int] | None:
    if not value.strip():
        return []
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not all(part.isascii() and part.isdecimal() for part in parts):
        return None
    return [int(part) for part in parts]


def entity_matches_query(record: EntityRecord, query: str) -> bool:
    haystack = " ".join(
        [record.display_name, record.summary, record.notes, record.definition.singular, record.definition.plural]
        + list(record.metadata.values())
    ).lower()
    return query.lower() in haystack
