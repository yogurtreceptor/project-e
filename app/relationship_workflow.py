import sqlite3

from app.db import create_entity, normalise_form_values, validate_entity_values
from app.entities import DEFINITIONS_BY_TYPE, EntityDefinition


INLINE_RELATIONSHIP_ENTITY_TYPES = ("person", "organisation", "location")


def create_inline_relationship_target(
    connection: sqlite3.Connection,
    values: dict[str, str],
    raw_form: dict[str, str],
    query: dict[str, str],
) -> list[str]:
    if values.get("target_entity_id"):
        return []
    if raw_form.get("workflow_mode") != "create_new" and raw_form.get("target_mode") != "create_new":
        return []

    entity_type = raw_form.get("new_entity_type", "").strip()
    forced_target_type = query.get("target_type", "").strip()
    if forced_target_type:
        entity_type = forced_target_type
    if entity_type not in INLINE_RELATIONSHIP_ENTITY_TYPES:
        return ["Choose Person, Organisation or Location for inline creation."]

    definition = DEFINITIONS_BY_TYPE.get(entity_type)
    if definition is None:
        return ["Connected entity type is invalid."]

    entity_values = inline_entity_values(definition, raw_form)
    errors = validate_entity_values(definition, entity_values)
    if errors:
        return [f"New {definition.singular.lower()}: {error}" for error in errors]

    target_id = create_entity(connection, definition, entity_values, commit=False)
    values["target_entity_id"] = str(target_id)
    return []


def inline_entity_values(
    definition: EntityDefinition,
    raw_form: dict[str, str],
) -> dict[str, str]:
    raw_values = {
        "display_name": raw_form.get("new_display_name", ""),
        "notes": raw_form.get("new_notes", ""),
    }
    for field in definition.fields:
        raw_values[field.name] = raw_form.get(f"new_{field.name}", "")
    return normalise_form_values(definition, raw_values)
