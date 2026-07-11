import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from app.relationships import RELATIONSHIP_TYPES_BY_KEY, relationship_type_is_valid_for_pair


@dataclass(frozen=True)
class IntegrityWarning:
    code: str
    severity: str
    message: str
    relationship_ids: tuple[int, ...] = ()
    entity_ids: tuple[int, ...] = ()


def audit_relationships(connection: sqlite3.Connection) -> list[IntegrityWarning]:
    entities = {row["id"]: row["type"] for row in connection.execute("SELECT id, type FROM entities")}
    rows = connection.execute("SELECT * FROM relationships WHERE deleted_at='' ORDER BY id").fetchall()
    warnings: list[IntegrityWarning] = []
    valid_rows = []
    for row in rows:
        rid, source, target = int(row["id"]), int(row["source_entity_id"]), int(row["target_entity_id"])
        missing = tuple(entity_id for entity_id in (source, target) if entity_id not in entities)
        if missing:
            warnings.append(IntegrityWarning("orphan_relationship", "error", f"Relationship {rid} references missing entity {', '.join(map(str, missing))}.", (rid,), missing))
            continue
        if source == target:
            warnings.append(IntegrityWarning("self_reference", "error", f"Relationship {rid} links an entity to itself.", (rid,), (source,)))
            continue
        if row["type"] not in RELATIONSHIP_TYPES_BY_KEY:
            warnings.append(IntegrityWarning("broken_type", "error", f"Relationship {rid} uses unknown type “{row['type']}”.", (rid,), (source, target)))
        elif not relationship_type_is_valid_for_pair(row["type"], entities[source], entities[target]):
            warnings.append(IntegrityWarning("invalid_pair", "error", f"Relationship {rid} has a type that is invalid for its entity types.", (rid,), (source, target)))
        valid_rows.append(row)

    groups: dict[tuple[object, ...], list[int]] = defaultdict(list)
    for row in valid_rows:
        relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(row["type"])
        endpoints = (int(row["source_entity_id"]), int(row["target_entity_id"]))
        if relationship_type and not relationship_type.directional:
            endpoints = tuple(sorted(endpoints))
        groups[(row["type"], *endpoints)].append(int(row["id"]))
    for ids in groups.values():
        if len(ids) > 1:
            warnings.append(IntegrityWarning("duplicate_relationship", "warning", f"Relationships {', '.join(map(str, ids))} duplicate the same connection.", tuple(ids)))

    person_links: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for row in valid_rows:
        if entities.get(row["source_entity_id"]) != "person" or entities.get(row["target_entity_id"]) != "person":
            continue
        source, target, kind = int(row["source_entity_id"]), int(row["target_entity_id"]), row["type"]
        person_links[source][kind].add(target)
        person_links[target][kind].add(source)
    for entity_id, by_type in person_links.items():
        for other_id in by_type.get("parent_child", set()) & by_type.get("spouse_of", set()):
            if entity_id < other_id:
                warnings.append(IntegrityWarning("suspicious_family_roles", "warning", "The same two people are recorded as both parent/child and spouses.", entity_ids=(entity_id, other_id)))
        parent_count = len(by_type.get("parent_child", set()))
        if parent_count > 4:
            warnings.append(IntegrityWarning("excessive_parent_links", "warning", f"Person {entity_id} has {parent_count} parent/child relationships; review their direction and meaning.", entity_ids=(entity_id,)))
    return warnings


def warnings_for_entity(warnings: list[IntegrityWarning], entity_id: int) -> list[IntegrityWarning]:
    return [warning for warning in warnings if entity_id in warning.entity_ids]
