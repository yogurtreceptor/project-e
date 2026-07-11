import sqlite3
from dataclasses import dataclass

from app.entities import EntityDefinition, EntityRecord
from app.entity_repository import list_entities


@dataclass(frozen=True)
class DuplicateMatch:
    record: EntityRecord
    matched_fields: tuple[str, ...]


def find_duplicate_entities(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    values: dict[str, str],
    exclude_entity_id: int | None = None,
    limit: int = 5,
) -> list[DuplicateMatch]:
    incoming_name = comparable_value(values.get("display_name", ""))
    incoming_aliases = {
        comparable_value(value)
        for value in values.get("aliases", "").splitlines()
        if comparable_value(value)
    }
    field_labels = {field.name: field.label for field in definition.fields}
    matches = []
    for record in list_entities(connection, definition):
        if record.id == exclude_entity_id:
            continue
        matched_fields = []
        existing_name = comparable_value(record.display_name)
        existing_aliases = {
            comparable_value(value)
            for value in record.metadata.get("aliases", "").splitlines()
            if comparable_value(value)
        }
        if incoming_name and (existing_name == incoming_name or incoming_name in existing_aliases):
            matched_fields.append("Name")
        if incoming_aliases and ({existing_name} | existing_aliases) & incoming_aliases:
            matched_fields.append("Other names")
        for field_name in definition.duplicate_fields:
            incoming = comparable_value(values.get(field_name, ""))
            existing = comparable_value(record.metadata.get(field_name, ""))
            if incoming and existing == incoming:
                matched_fields.append(field_labels.get(field_name, field_name.replace("_", " ").title()))
        if matched_fields:
            matches.append(DuplicateMatch(record, tuple(matched_fields)))
        if len(matches) >= limit:
            break
    return matches


def comparable_value(value: str) -> str:
    return " ".join(value.casefold().split())
