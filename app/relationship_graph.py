"""Reusable extraction of entity relationships into a presentation-neutral graph."""
from dataclasses import dataclass
from typing import Callable, Iterable
from app.entities import EntityRecord
from app.relationships import RelationshipRecord

@dataclass(frozen=True)
class GraphNode:
    id: int
    label: str
    href: str
    entity_type: str

@dataclass(frozen=True)
class GraphEdge:
    source_id: int
    target_id: int
    label: str
    rank_delta: int = 1

@dataclass(frozen=True)
class RelationshipGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

EdgeMapper = Callable[[RelationshipRecord], GraphEdge | None]

def extract_relationship_graph(relationships: Iterable[RelationshipRecord], edge_mapper: EdgeMapper) -> RelationshipGraph:
    """Map canonical records into a deduplicated graph without layout assumptions."""
    nodes: dict[int, GraphNode] = {}
    edges: dict[tuple[int, int, str, int], GraphEdge] = {}
    for relationship in relationships:
        edge = edge_mapper(relationship)
        if edge is None or edge.source_id == edge.target_id:
            continue
        for entity in (relationship.source, relationship.target):
            nodes.setdefault(entity.id, node_from_entity(entity))
        key = (edge.source_id, edge.target_id, edge.label, edge.rank_delta)
        edges.setdefault(key, edge)
    return RelationshipGraph(tuple(sorted(nodes.values(), key=lambda node: (node.label.casefold(), node.id))), tuple(edges.values()))

def extract_family_graph(relationships: Iterable[RelationshipRecord]) -> RelationshipGraph:
    """Adapt family records, drawing only same or adjacent-generation edges."""
    return extract_relationship_graph(relationships, adjacent_family_edge)

def adjacent_family_edge(relationship: RelationshipRecord) -> GraphEdge | None:
    """Exclude visually redundant relationships that span multiple generations."""
    edge = family_edge(relationship)
    return edge if edge is None or edge.rank_delta <= 1 else None

def family_edge(relationship: RelationshipRecord) -> GraphEdge | None:
    if relationship.source.type != "person" or relationship.target.type != "person":
        return None
    if relationship.type_key == "parent_child":
        return GraphEdge(relationship.source.id, relationship.target.id, "parent", 1)
    if relationship.type_key == "grandparent_child":
        return GraphEdge(relationship.source.id, relationship.target.id, "grandparent", 2)
    if relationship.type_key in {"sibling_of", "spouse_of", "partner_of"}:
        return GraphEdge(relationship.source.id, relationship.target.id, relationship.type.subtype.lower(), 0)
    return None

def node_from_entity(entity: EntityRecord) -> GraphNode:
    label = entity.title or f"Unnamed {entity.definition.singular}"
    return GraphNode(entity.id, label, f"/{entity.slug}/{entity.id}", entity.type)
