"""Canonical entity lifecycle orchestration over focused repositories."""

import sqlite3

from app.birthday_calendar import sync_person_birthday
from app.entities import EntityDefinition
from app.entity_repository import (
    create_entity as create_entity_record,
    delete_entity as delete_entity_record,
    get_entity,
    get_entity_by_id,
    permanent_delete_entity,
    restore_entity as restore_entity_record,
    update_entity as update_entity_record,
    with_canonical_person_name,
)
from app.inbox_repository import resolve_source_items
from app.relationship_inference import recompute_inferences


def create_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    values: dict[str, str],
    commit: bool = True,
) -> int:
    canonical_values = with_canonical_person_name(definition, values)
    entity_id = create_entity_record(
        connection, definition, canonical_values, commit=False
    )
    if definition.type == "person":
        sync_person_birthday(
            connection,
            entity_id,
            canonical_values["display_name"],
            canonical_values.get("birthday", ""),
        )
    if commit:
        connection.commit()
    return entity_id


def update_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
    values: dict[str, str],
) -> None:
    canonical_values = with_canonical_person_name(definition, values)
    before = get_entity(connection, definition, entity_id)
    update_entity_record(
        connection, definition, entity_id, canonical_values, commit=False
    )
    if (
        definition.type == "person"
        and before is not None
        and (
            before.metadata.get("birthday", "")
            != canonical_values.get("birthday", "")
            or before.display_name != canonical_values["display_name"]
        )
    ):
        sync_person_birthday(
            connection,
            entity_id,
            canonical_values["display_name"],
            canonical_values.get("birthday", ""),
        )
        resolve_source_items(connection, "birthday", entity_id)
        recompute_inferences(connection, "person_date_updated", entity_id)
    elif (
        definition.type == "document"
        and before is not None
        and before.metadata.get("expiry_date", "")
        != canonical_values.get("expiry_date", "")
    ):
        resolve_source_items(connection, "document_expiry", entity_id)
    connection.commit()


def delete_entity(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    entity_id: int,
) -> None:
    before = get_entity(connection, definition, entity_id)
    delete_entity_record(connection, definition, entity_id, commit=False)
    reminder_sources = {
        "person": "birthday",
        "document": "document_expiry",
        "event": "event",
    }
    if definition.type in reminder_sources:
        resolve_source_items(connection, reminder_sources[definition.type], entity_id)
    if definition.type == "person":
        sync_person_birthday(
            connection, entity_id, before.display_name if before else "", ""
        )
        recompute_inferences(connection, "person_deleted", entity_id)
    connection.commit()


def restore_entity(connection: sqlite3.Connection, entity_id: int) -> bool:
    before = get_entity_by_id(connection, entity_id, include_deleted=True)
    if before is None or not before.is_deleted:
        return False
    restored = restore_entity_record(connection, entity_id, commit=False)
    if not restored:
        return False
    if before.type == "person":
        sync_person_birthday(
            connection,
            entity_id,
            before.display_name,
            before.metadata.get("birthday", ""),
        )
        recompute_inferences(connection, "person_restored", entity_id)
    connection.commit()
    return True
