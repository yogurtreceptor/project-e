"""Small generic layered graph layout with deterministic cycle handling."""
from dataclasses import dataclass
from app.relationship_graph import GraphEdge, RelationshipGraph

@dataclass(frozen=True)
class PositionedNode:
    id: int
    label: str
    href: str
    x: int
    y: int

@dataclass(frozen=True)
class PositionedEdge:
    source_id: int
    target_id: int
    label: str
    cyclic: bool = False

@dataclass(frozen=True)
class GraphLayout:
    nodes: tuple[PositionedNode, ...]
    edges: tuple[PositionedEdge, ...]
    width: int
    height: int

def layered_layout(graph: RelationshipGraph, horizontal_gap: int = 190, vertical_gap: int = 130, padding: int = 90) -> GraphLayout:
    """Place positive-rank edges downward and zero-rank edges on the same layer."""
    if not graph.nodes:
        return GraphLayout((), (), 0, 0)
    ranks = {node.id: 0 for node in graph.nodes}
    accepted: list[GraphEdge] = []
    cyclic_keys: set[tuple[int, int, str]] = set()
    adjacency: dict[int, set[int]] = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        if edge.rank_delta <= 0:
            accepted.append(edge)
            continue
        if _reachable(adjacency, edge.target_id, edge.source_id):
            cyclic_keys.add((edge.source_id, edge.target_id, edge.label))
            continue
        adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        accepted.append(edge)
    for _ in range(len(ranks)):
        changed = False
        for edge in accepted:
            if edge.rank_delta > 0:
                wanted = ranks[edge.source_id] + edge.rank_delta
                if wanted > ranks[edge.target_id]:
                    ranks[edge.target_id] = wanted
                    changed = True
        if not changed:
            break
    layers: dict[int, list] = {}
    for node in graph.nodes:
        layers.setdefault(ranks[node.id], []).append(node)
    max_count = max(len(nodes) for nodes in layers.values())
    positions: list[PositionedNode] = []
    for rank, nodes in sorted(layers.items()):
        row_width = (len(nodes) - 1) * horizontal_gap
        offset = padding + ((max_count - 1) * horizontal_gap - row_width) // 2
        for index, node in enumerate(nodes):
            positions.append(PositionedNode(node.id, node.label, node.href, offset + index * horizontal_gap, padding + rank * vertical_gap))
    rendered_edges = tuple(PositionedEdge(edge.source_id, edge.target_id, edge.label, (edge.source_id, edge.target_id, edge.label) in cyclic_keys) for edge in graph.edges)
    return GraphLayout(tuple(positions), rendered_edges, (max_count - 1) * horizontal_gap + padding * 2, max(ranks.values()) * vertical_gap + padding * 2)

def _reachable(adjacency: dict[int, set[int]], start: int, target: int) -> bool:
    pending = [start]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency.get(current, ()))
    return False
