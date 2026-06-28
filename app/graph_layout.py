"""Family-tree layout with generation, partner-unit and child-group rules."""
from dataclasses import dataclass
from itertools import permutations
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
    rank_delta: int = 1
    cyclic: bool = False

@dataclass(frozen=True)
class GraphLayout:
    nodes: tuple[PositionedNode, ...]
    edges: tuple[PositionedEdge, ...]
    width: int
    height: int

def layered_layout(graph: RelationshipGraph, horizontal_gap: int = 190, vertical_gap: int = 130, padding: int = 90) -> GraphLayout:
    """Lay out family generations, partner units and exact-parent-set child groups."""
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

    equivalent_endpoints: dict[tuple[str, int, int], list[int]] = {}
    for edge in graph.edges:
        if edge.rank_delta <= 0:
            continue
        equivalent_endpoints.setdefault(("source", edge.target_id, edge.rank_delta), []).append(edge.source_id)
        equivalent_endpoints.setdefault(("target", edge.source_id, edge.rank_delta), []).append(edge.target_id)
    for node_ids in equivalent_endpoints.values():
        for node_id in node_ids[1:]:
            union(node_ids[0], node_id)

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
    hierarchy_neighbours: dict[int, set[int]] = {node.id: set() for node in graph.nodes}
    for edge in graph.edges:
        if edge.rank_delta > 0:
            hierarchy_neighbours[edge.source_id].add(edge.target_id)
            hierarchy_neighbours[edge.target_id].add(edge.source_id)
    _order_layers_by_neighbours(ordered_layers, ranks, hierarchy_neighbours)
    _order_sources_to_separate_family_units(ordered_layers, graph, ranks)
    _keep_partner_units_contiguous(ordered_layers, graph)
    _keep_exact_source_targets_contiguous(ordered_layers, graph, ranks)

    peer_pairs = {
        frozenset((edge.source_id, edge.target_id))
        for edge in graph.edges
        if edge.rank_delta == 0
    }
    branch_gap = horizontal_gap // 2
    row_coordinates: dict[int, list[int]] = {}
    row_widths: dict[int, int] = {}
    for rank, nodes in ordered_layers.items():
        coordinates = [0]
        for previous, current in zip(nodes, nodes[1:]):
            distinct_branches = hierarchy_neighbours[previous.id] != hierarchy_neighbours[current.id]
            explicit_peers = frozenset((previous.id, current.id)) in peer_pairs
            extra_gap = branch_gap if distinct_branches and not explicit_peers else 0
            coordinates.append(coordinates[-1] + horizontal_gap + extra_gap)
        row_coordinates[rank] = coordinates
        row_widths[rank] = coordinates[-1]

    hierarchy_sources: dict[int, set[int]] = {}
    for edge in graph.edges:
        if edge.rank_delta > 0:
            hierarchy_sources.setdefault(edge.target_id, set()).add(edge.source_id)
    bundle_counts: dict[int, set[tuple[int, ...]]] = {}
    for target_id, source_ids in hierarchy_sources.items():
        bundle_counts.setdefault(ranks[target_id], set()).add(tuple(sorted(source_ids)))
    max_bundles = max((len(source_sets) for source_sets in bundle_counts.values()), default=1)
    effective_vertical_gap = max(vertical_gap, 90 + max_bundles * 24)

    max_width = max(row_widths.values())
    positions: list[PositionedNode] = []
    for rank, nodes in sorted(ordered_layers.items()):
        offset = padding + (max_width - row_widths[rank]) // 2
        for node, coordinate in zip(nodes, row_coordinates[rank]):
            positions.append(PositionedNode(node.id, node.label, node.href, offset + coordinate, padding + rank * effective_vertical_gap))

    rendered_edges = tuple(
        PositionedEdge(
            source_id=edge.source_id,
            target_id=edge.target_id,
            label=edge.label,
            connector_style=edge.connector_style,
            rank_delta=edge.rank_delta,
            cyclic=(edge.source_id, edge.target_id, edge.label, edge.connector_style) in cyclic_keys,
        )
        for edge in graph.edges
    )
    return GraphLayout(tuple(positions), rendered_edges, max_width + padding * 2, max(ranks.values()) * effective_vertical_gap + padding * 2)

def _order_sources_to_separate_family_units(ordered_layers: dict[int, list], graph: RelationshipGraph, ranks: dict[int, int]) -> None:
    """Place shared parents between co-parents so family-unit spans do not interleave."""
    incoming_sources: dict[int, set[int]] = {}
    for edge in graph.edges:
        if edge.rank_delta > 0:
            incoming_sources.setdefault(edge.target_id, set()).add(edge.source_id)
    source_sets_by_rank: dict[int, set[tuple[int, ...]]] = {}
    for source_ids in incoming_sources.values():
        if len(source_ids) > 1:
            source_rank = ranks[next(iter(source_ids))]
            source_sets_by_rank.setdefault(source_rank, set()).add(tuple(sorted(source_ids)))

    for rank, source_sets in source_sets_by_rank.items():
        nodes = ordered_layers.get(rank, [])
        if len(nodes) > 7 or len(source_sets) < 2:
            continue
        original = {node.id: index for index, node in enumerate(nodes)}

        def score(order: tuple) -> tuple:
            positions = {node.id: index for index, node in enumerate(order)}
            intervals = [
                (min(positions[node_id] for node_id in source_set), max(positions[node_id] for node_id in source_set))
                for source_set in source_sets if all(node_id in positions for node_id in source_set)
            ]
            overlap = sum(
                max(0, min(first[1], second[1]) - max(first[0], second[0]))
                for index, first in enumerate(intervals) for second in intervals[index + 1:]
            )
            span = sum(end - start for start, end in intervals)
            movement = sum(abs(index - original[node.id]) for index, node in enumerate(order))
            return overlap, span, movement, tuple(node.id for node in order)

        ordered_layers[rank] = list(min(permutations(nodes), key=score))


def _keep_partner_units_contiguous(ordered_layers: dict[int, list], graph: RelationshipGraph) -> None:
    """Treat spouse/partner components as deterministic, indivisible row units."""
    partner_edges = [edge for edge in graph.edges if edge.rank_delta == 0 and edge.connector_style == "peer-strong"]
    adjacency: dict[int, set[int]] = {}
    for edge in partner_edges:
        adjacency.setdefault(edge.source_id, set()).add(edge.target_id)
        adjacency.setdefault(edge.target_id, set()).add(edge.source_id)
    for rank, nodes in ordered_layers.items():
        current = {node.id: index for index, node in enumerate(nodes)}
        node_by_id = {node.id: node for node in nodes}
        seen: set[int] = set()
        units: list[list] = []
        for node in nodes:
            if node.id in seen:
                continue
            pending = [node.id]
            component: list[int] = []
            while pending:
                node_id = pending.pop()
                if node_id in seen or node_id not in node_by_id:
                    continue
                seen.add(node_id)
                component.append(node_id)
                pending.extend(adjacency.get(node_id, ()))
            unit = [node_by_id[node_id] for node_id in component]
            if 1 < len(unit) <= 7:
                unit = list(min(permutations(unit), key=lambda order: (
                    sum(abs(index - next_index) for index, first in enumerate(order) for next_index, second in enumerate(order) if second.id in adjacency.get(first.id, ()) and index < next_index),
                    sum(abs(index - current[item.id]) for index, item in enumerate(order)),
                    tuple(item.id for item in order),
                )))
            else:
                unit.sort(key=lambda item: current[item.id])
            units.append(unit)
        units.sort(key=lambda unit: sum(current[item.id] for item in unit) / len(unit))
        ordered_layers[rank] = [node for unit in units for node in unit]


def _keep_exact_source_targets_contiguous(ordered_layers: dict[int, list], graph: RelationshipGraph, ranks: dict[int, int]) -> None:
    """Keep targets with the same complete incoming-source set in one row block."""
    incoming_sources: dict[int, set[int]] = {}
    for edge in graph.edges:
        if edge.rank_delta > 0:
            incoming_sources.setdefault(edge.target_id, set()).add(edge.source_id)
    for rank, nodes in ordered_layers.items():
        original_positions = {node.id: index for index, node in enumerate(nodes)}
        blocks: dict[tuple, list] = {}
        for node in nodes:
            source_set = tuple(sorted(incoming_sources.get(node.id, ())))
            key = ("sources", source_set) if source_set else ("node", node.id)
            blocks.setdefault(key, []).append(node)
        source_positions = {
            node.id: index
            for source_rank, source_nodes in ordered_layers.items()
            if source_rank < rank
            for index, node in enumerate(source_nodes)
        }

        def block_position(block: list) -> tuple[float, float, int]:
            source_set = tuple(sorted(incoming_sources.get(block[0].id, ())))
            parent_centre = (
                sum(source_positions[source_id] for source_id in source_set) / len(source_set)
                if source_set and all(source_id in source_positions for source_id in source_set)
                else float("inf")
            )
            prior_centre = sum(original_positions[node.id] for node in block) / len(block)
            return parent_centre, prior_centre, min(node.id for node in block)

        ordered_blocks = sorted(blocks.values(), key=block_position)
        ordered_layers[rank] = [node for block in ordered_blocks for node in sorted(block, key=lambda item: original_positions[item.id])]


def _order_layers_by_neighbours(ordered_layers: dict[int, list], ranks: dict[int, int], neighbours: dict[int, set[int]]) -> None:
    """Order each row near its actual adjacent-row connections."""
    sorted_ranks = sorted(ordered_layers)
    for _ in range(4):
        for rank_order, neighbour_direction in ((sorted_ranks[1:], -1), (list(reversed(sorted_ranks[:-1])), 1)):
            for rank in rank_order:
                nodes = ordered_layers[rank]
                prior_positions = {node.id: index for index, node in enumerate(nodes)}
                positions = {
                    node.id: index
                    for layer_nodes in ordered_layers.values()
                    for index, node in enumerate(layer_nodes)
                }

                def order_key(node) -> tuple[float, int, str, int]:
                    adjacent = [
                        positions[other_id]
                        for other_id in neighbours[node.id]
                        if ranks[other_id] == rank + neighbour_direction
                    ]
                    barycentre = sum(adjacent) / len(adjacent) if adjacent else float(prior_positions[node.id])
                    return (barycentre, prior_positions[node.id], node.label.casefold(), node.id)

                nodes.sort(key=order_key)

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
