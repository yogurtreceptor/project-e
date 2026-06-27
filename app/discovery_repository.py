import sqlite3

from app.db_support import utc_now
from app.entities import EntityRecord
from app.entity_repository import entity_matches_query, get_entity_by_id, list_all_entities
from app.relationship_repository import list_relationships_for_entity
from app.relationships import RelationshipRecord


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
