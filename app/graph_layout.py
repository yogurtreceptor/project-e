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
    connector_style: str = "hierarchy"
    cyclic: bool = False

@dataclass(frozen=True)
class GraphLayout:
    nodes: tuple[PositionedNode, ...]
    edges: tuple[PositionedEdge, ...]
    width: int
    height: int

def layered_layout(graph: RelationshipGraph, horizontal_gap: int = 190, vertical_gap: int = 130, padding: int = 90) -> GraphLayout:
    """Place rank-connected groups on a deterministic generational grid."""
    if not graph.nodes:
        return GraphLayout((), (), 0, 0)

    parent = {node.id: node.id for node in graph.nodes}

    def find(node_id: int) -> int:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(first: int, second: int) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[max(first_root, second_root)] = min(first_root, second_root)

    for edge in graph.edges:
        if edge.rank_delta == 0:
            union(edge.source_id, edge.target_id)

    group_edges: list[tuple[int, int, GraphEdge]] = []
    cyclic_keys: set[tuple[int, int, str, str]] = set()
    adjacency: dict[int, set[int]] = {}
    for edge in graph.edges:
        if edge.rank_delta <= 0:
            continue
        source_group, target_group = find(edge.source_id), find(edge.target_id)
        key = (edge.source_id, edge.target_id, edge.label, edge.connector_style)
        if source_group == target_group or _reachable(adjacency, target_group, source_group):
            cyclic_keys.add(key)
            continue
        adjacency.setdefault(source_group, set()).add(target_group)
        group_edges.append((source_group, target_group, edge))

    groups = {find(node.id) for node in graph.nodes}
    group_ranks = {group: 0 for group in groups}
    for _ in range(len(groups)):
        changed = False
        for source_group, target_group, edge in group_edges:
            wanted = group_ranks[source_group] + edge.rank_delta
            if wanted > group_ranks[target_group]:
                group_ranks[target_group] = wanted
                changed = True
        if not changed:
            break

    ranks = {node.id: group_ranks[find(node.id)] for node in graph.nodes}
    layers: dict[int, list[list]] = {}
    grouped_nodes: dict[int, list] = {}
    for node in graph.nodes:
        grouped_nodes.setdefault(find(node.id), []).append(node)
    for group_id, nodes in grouped_nodes.items():
        nodes.sort(key=lambda node: (node.label.casefold(), node.id))
        layers.setdefault(group_ranks[group_id], []).append(nodes)
    for groups_in_layer in layers.values():
        groups_in_layer.sort(key=lambda nodes: (nodes[0].label.casefold(), nodes[0].id))

    ordered_layers = {rank: [node for group in groups_in_layer for node in group] for rank, groups_in_layer in layers.items()}
    max_count = max(len(nodes) for nodes in ordered_layers.values())
    positions: list[PositionedNode] = []
    for rank, nodes in sorted(ordered_layers.items()):
        row_width = (len(nodes) - 1) * horizontal_gap
        offset = padding + ((max_count - 1) * horizontal_gap - row_width) // 2
        for index, node in enumerate(nodes):
            positions.append(PositionedNode(node.id, node.label, node.href, offset + index * horizontal_gap, padding + rank * vertical_gap))

    rendered_edges = tuple(
        PositionedEdge(
            edge.source_id,
            edge.target_id,
            edge.label,
            edge.connector_style,
            (edge.source_id, edge.target_id, edge.label, edge.connector_style) in cyclic_keys,
        )
        for edge in graph.edges
    )
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
