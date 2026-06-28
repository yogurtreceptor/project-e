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
    birth_date: str = ""

@dataclass(frozen=True)
class GraphEdge:
    source_id: int
    target_id: int
    label: str
    rank_delta: int = 1
    connector_style: str = "hierarchy"

@dataclass(frozen=True)
class RelationshipGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

EdgeMapper = Callable[[RelationshipRecord], GraphEdge | None]

def extract_relationship_graph(relationships: Iterable[RelationshipRecord], edge_mapper: EdgeMapper) -> RelationshipGraph:
    """Map canonical records into a deduplicated graph without layout assumptions."""
    nodes: dict[int, GraphNode] = {}
    edges: dict[tuple[int, int, str, int, str], GraphEdge] = {}
    for relationship in relationships:
        edge = edge_mapper(relationship)
        if edge is None or edge.source_id == edge.target_id:
            continue
        for entity in (relationship.source, relationship.target):
            nodes.setdefault(entity.id, node_from_entity(entity))
        key = (edge.source_id, edge.target_id, edge.label, edge.rank_delta, edge.connector_style)
        edges.setdefault(key, edge)
    return RelationshipGraph(tuple(sorted(nodes.values(), key=_node_order)), tuple(edges.values()))

def extract_family_graph(relationships: Iterable[RelationshipRecord]) -> RelationshipGraph:
    """Adapt family records, drawing only same or adjacent-generation edges."""
    return extract_relationship_graph(relationships, adjacent_family_edge)

def connected_family_components(graph: RelationshipGraph) -> tuple[RelationshipGraph, ...]:
    """Return deterministic connected components without making layout decisions."""
    neighbours = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        neighbours[edge.source_id].add(edge.target_id)
        neighbours[edge.target_id].add(edge.source_id)
    nodes_by_id = {node.id: node for node in graph.nodes}
    components, unseen = [], set(nodes_by_id)
    while unseen:
        seed = min(unseen, key=lambda node_id: _node_order(nodes_by_id[node_id]))
        pending, member_ids = [seed], set()
        while pending:
            node_id = pending.pop()
            if node_id in member_ids:
                continue
            member_ids.add(node_id)
            unseen.discard(node_id)
            pending.extend(sorted(neighbours[node_id] - member_ids, reverse=True))
        components.append(_induced_graph(graph, member_ids))
    return tuple(sorted(components, key=lambda item: (-len(item.nodes), -len(item.edges), tuple(node.id for node in item.nodes))))


def full_family_component(relationships: Iterable[RelationshipRecord]) -> RelationshipGraph:
    """Select the largest connected family component for the relationships view."""
    components = connected_family_components(extract_family_graph(relationships))
    return components[0] if components else RelationshipGraph((), ())


def person_family_subgraph(graph: RelationshipGraph, person_id: int, generations: int = 1) -> RelationshipGraph:
    """Select a bounded person-centred subgraph for a future record-local view."""
    neighbours = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        neighbours[edge.source_id].add(edge.target_id)
        neighbours[edge.target_id].add(edge.source_id)
    included, frontier = {person_id}, {person_id}
    for _ in range(max(0, generations)):
        frontier = {other for node_id in frontier for other in neighbours.get(node_id, ())} - included
        included.update(frontier)
    return _induced_graph(graph, included)


def _induced_graph(graph: RelationshipGraph, member_ids: set[int]) -> RelationshipGraph:
    return RelationshipGraph(
        tuple(node for node in graph.nodes if node.id in member_ids),
        tuple(edge for edge in graph.edges if edge.source_id in member_ids and edge.target_id in member_ids),
    )


def _node_order(node: GraphNode) -> tuple[str, str, int]:
    return (node.birth_date or "9999-12-31", node.label.casefold(), node.id)


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
    if relationship.type_key in {"spouse_of", "partner_of"}:
        return GraphEdge(relationship.source.id, relationship.target.id, relationship.type.subtype.lower(), 0, "peer-strong")
    return None

def node_from_entity(entity: EntityRecord) -> GraphNode:
    label = entity.title or f"Unnamed {entity.definition.singular}"
    return GraphNode(entity.id, label, f"/{entity.slug}/{entity.id}", entity.type, entity.metadata.get("birthday", ""))
