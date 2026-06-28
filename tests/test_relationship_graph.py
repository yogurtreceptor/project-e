import re
import unittest
from unittest.mock import patch
from app.entities import DEFINITIONS_BY_TYPE, EntityRecord
from app.graph_layout import layered_layout
from app.relationship_graph import (
    GraphEdge, adjacent_family_edge, extract_family_graph, full_family_component, person_family_subgraph,
)
from app.relationships import RelationshipRecord
from app.view_pages.relationships import family_tree_page

def person(entity_id: int, name: str) -> EntityRecord:
    return EntityRecord(entity_id, DEFINITIONS_BY_TYPE["person"], name, "", "", "", "", "", False, {})

def relationship(relationship_id: int, type_key: str, source: EntityRecord, target: EntityRecord) -> RelationshipRecord:
    return RelationshipRecord(relationship_id, type_key, source, target, "active", "", "exact", "", "exact", "", "", "")

class RelationshipGraphTests(unittest.TestCase):
    def test_family_extraction_deduplicates_nodes_and_ignores_unrelated_types(self) -> None:
        parent, first, second = person(1, "Parent"), person(2, "First"), person(3, "Second")
        graph = extract_family_graph([relationship(1, "parent_child", parent, first), relationship(2, "parent_child", parent, second), relationship(3, "friend_of", first, second)])
        self.assertEqual({node.id for node in graph.nodes}, {1, 2, 3})
        self.assertEqual(len(graph.edges), 2)

    def test_layered_layout_places_parents_above_children_and_siblings_together(self) -> None:
        parent, first, second = person(1, "Parent"), person(2, "First"), person(3, "Second")
        layout = layered_layout(extract_family_graph([relationship(1, "parent_child", parent, first), relationship(2, "parent_child", parent, second)]))
        positions = {node.id: node for node in layout.nodes}
        self.assertLess(positions[1].y, positions[2].y)
        self.assertEqual(positions[2].y, positions[3].y)
        self.assertNotEqual(positions[2].x, positions[3].x)

    def test_family_extraction_uses_parent_chain_without_redundant_generation_spanning_edge(self) -> None:
        grandparent, parent, child = person(1, "Grandparent"), person(2, "Parent"), person(3, "Child")
        graph = extract_family_graph([
            relationship(1, "parent_child", grandparent, parent),
            relationship(2, "parent_child", parent, child),
            relationship(3, "grandparent_child", grandparent, child),
        ])
        self.assertEqual(
            {(edge.source_id, edge.target_id, edge.rank_delta) for edge in graph.edges},
            {(1, 2, 1), (2, 3, 1)},
        )

    def test_adjacent_generation_filter_is_based_on_rank_span_not_relationship_type(self) -> None:
        parent, child = person(1, "Parent"), person(2, "Child")
        record = relationship(1, "parent_child", parent, child)

        with patch("app.relationship_graph.family_edge", return_value=GraphEdge(1, 2, "future ancestor", 3)):
            self.assertIsNone(adjacent_family_edge(record))

    def test_equivalent_hierarchy_endpoints_align_when_only_one_branch_has_ancestors(self) -> None:
        grandparent, first_parent, second_parent, child = (
            person(1, "Grandparent"), person(2, "First parent"), person(3, "Second parent"), person(4, "Child")
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", grandparent, first_parent),
            relationship(2, "parent_child", first_parent, child),
            relationship(3, "parent_child", second_parent, child),
        ]))
        positions = {node.id: node for node in layout.nodes}
        self.assertEqual(positions[2].y, positions[3].y)
        self.assertLess(positions[1].y, positions[2].y)
        self.assertLess(positions[2].y, positions[4].y)
        self.assertNotEqual(positions[1].y, positions[3].y)

    def test_equivalent_targets_align_as_a_generic_layout_rule(self) -> None:
        source, first, second = person(1, "Source"), person(2, "First"), person(3, "Second")
        graph = extract_family_graph([
            relationship(1, "parent_child", source, first),
            relationship(2, "parent_child", source, second),
        ])
        layout = layered_layout(graph)
        positions = {node.id: node for node in layout.nodes}
        self.assertEqual(positions[2].y, positions[3].y)

    def test_mixed_parent_sets_are_ordered_near_only_their_connected_children(self) -> None:
        shared_parent, additional_parent, first_child, second_child = (
            person(1, "Zulu shared parent"),
            person(2, "Alpha additional parent"),
            person(3, "Alpha first child"),
            person(4, "Zulu second child"),
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", shared_parent, first_child),
            relationship(2, "parent_child", shared_parent, second_child),
            relationship(3, "parent_child", additional_parent, second_child),
        ]))
        positions = {node.id: node for node in layout.nodes}

        parent_order = positions[2].x - positions[1].x
        child_order = positions[4].x - positions[3].x
        self.assertGreater(parent_order * child_order, 0)
        self.assertLess(abs(positions[1].x - positions[3].x), abs(positions[2].x - positions[3].x))
        self.assertLess(abs(positions[2].x - positions[4].x), abs(positions[2].x - positions[3].x))
        self.assertGreater(abs(positions[1].x - positions[2].x), 190)
        self.assertGreater(abs(positions[3].x - positions[4].x), 190)

    def test_hierarchy_connectors_bundle_children_by_exact_parent_set(self) -> None:
        first_parent, second_parent, single_parent_child, first_shared_child, second_shared_child = (
            person(1, "First parent"),
            person(2, "Second parent"),
            person(3, "Single-parent child"),
            person(4, "First shared child"),
            person(5, "Second shared child"),
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", first_parent, single_parent_child),
            relationship(2, "parent_child", first_parent, first_shared_child),
            relationship(3, "parent_child", second_parent, first_shared_child),
            relationship(4, "parent_child", first_parent, second_shared_child),
            relationship(5, "parent_child", second_parent, second_shared_child),
        ]))

        html = family_tree_page(layout)
        self.assertEqual(html.count('family-edge-bundle'), 2)
        self.assertIn('data-source-set="1" data-target-set="3"', html)
        self.assertIn('data-source-set="1,2" data-target-set="4,5"', html)
        self.assertNotIn('data-source-set="1" data-target-set="3,4,5"', html)

    def test_blended_family_groups_use_independent_parent_ports_and_lanes(self) -> None:
        parent_a, parent_b, parent_c, child_a, child_ab_one, child_ab_two, child_ac = (
            person(1, "Parent A"), person(2, "Parent B"), person(3, "Parent C"),
            person(4, "Child A"), person(5, "Child AB one"), person(6, "Child AB two"), person(7, "Child AC"),
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", parent_a, child_a),
            relationship(2, "parent_child", parent_a, child_ab_one),
            relationship(3, "parent_child", parent_b, child_ab_one),
            relationship(4, "parent_child", parent_a, child_ab_two),
            relationship(5, "parent_child", parent_b, child_ab_two),
            relationship(6, "parent_child", parent_a, child_ac),
            relationship(7, "parent_child", parent_c, child_ac),
        ]))

        html = family_tree_page(layout)
        bundles = re.findall(
            r'data-source-set="([^"]+)" data-target-set="([^"]+)" '
            r'data-source-ports="([^"]+)" data-lane="([^"]+)"',
            html,
        )
        self.assertEqual({(sources, targets) for sources, targets, _, _ in bundles}, {
            ("1", "4"), ("1,2", "5,6"), ("1,3", "7"),
        })
        parent_a_ports = {
            int(match.group(1))
            for _, _, ports, _ in bundles
            if (match := re.search(r'(?:^|,)1:(\d+)(?:,|$)', ports))
        }
        self.assertEqual(len(parent_a_ports), 3)
        self.assertEqual(len({lane for _, _, _, lane in bundles}), 3)
        self.assertEqual(html.count('data-crossings="0"'), 3)
        self.assertNotIn('class="family-edge-casing"', html)

    def test_partner_units_are_adjacent_and_multiple_partners_do_not_interleave(self) -> None:
        central, first_partner, second_partner, sibling, child, parent = (
            person(1, "Central"), person(2, "First partner"), person(3, "Second partner"),
            person(4, "Sibling"), person(5, "Child"), person(6, "Parent"),
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "spouse_of", central, first_partner),
            relationship(2, "partner_of", central, second_partner),
            relationship(3, "parent_child", parent, central),
            relationship(4, "parent_child", parent, sibling),
            relationship(5, "parent_child", central, child),
        ]))
        central_y = next(node.y for node in layout.nodes if node.id == central.id)
        row = [node.id for node in sorted((node for node in layout.nodes if node.y == central_y), key=lambda node: node.x)]
        partner_indexes = sorted(row.index(node_id) for node_id in (1, 2, 3))
        self.assertEqual(partner_indexes, list(range(partner_indexes[0], partner_indexes[0] + 3)))
        self.assertNotIn(4, row[partner_indexes[0]:partner_indexes[-1] + 1])
        self.assertEqual(abs(row.index(1) - row.index(2)), 1)
        self.assertEqual(abs(row.index(1) - row.index(3)), 1)

    def test_exact_parent_set_child_blocks_are_contiguous_and_under_their_family_units(self) -> None:
        parent_a, parent_b, parent_c = person(1, "A"), person(2, "B"), person(3, "C")
        child_a, child_ab_one, child_ab_two, child_ac = (
            person(4, "A child"), person(5, "AB one"), person(6, "AB two"), person(7, "AC child")
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", parent_a, child_a),
            relationship(2, "parent_child", parent_a, child_ab_one),
            relationship(3, "parent_child", parent_b, child_ab_one),
            relationship(4, "parent_child", parent_a, child_ab_two),
            relationship(5, "parent_child", parent_b, child_ab_two),
            relationship(6, "parent_child", parent_a, child_ac),
            relationship(7, "parent_child", parent_c, child_ac),
        ]))
        positions = {node.id: node for node in layout.nodes}
        child_order = [node.id for node in sorted((positions[node_id] for node_id in (4, 5, 6, 7)), key=lambda node: node.x)]
        self.assertEqual(abs(child_order.index(5) - child_order.index(6)), 1)
        self.assertLess(abs(positions[4].x - positions[1].x), abs(positions[4].x - positions[2].x))
        parent_ab_centre = (positions[1].x + positions[2].x) / 2
        self.assertLess(abs((positions[5].x + positions[6].x) / 2 - parent_ab_centre), abs(positions[7].x - parent_ab_centre))

    def test_unrelated_branch_does_not_reshuffle_existing_family_order(self) -> None:
        parent_a, parent_b, child = person(1, "Parent A"), person(2, "Parent B"), person(3, "Child")
        base_relationships = [
            relationship(1, "partner_of", parent_a, parent_b),
            relationship(2, "parent_child", parent_a, child),
            relationship(3, "parent_child", parent_b, child),
        ]
        base = layered_layout(extract_family_graph(base_relationships))
        extra_parent, extra_child = person(10, "Unrelated parent"), person(11, "Unrelated child")
        expanded = layered_layout(extract_family_graph(base_relationships + [relationship(4, "parent_child", extra_parent, extra_child)]))
        base_order = [node.id for node in sorted(base.nodes, key=lambda node: (node.y, node.x)) if node.id in {1, 2, 3}]
        expanded_order = [node.id for node in sorted(expanded.nodes, key=lambda node: (node.y, node.x)) if node.id in {1, 2, 3}]
        self.assertEqual(expanded_order, base_order)

    def test_zero_rank_groups_share_a_row_and_stay_adjacent(self) -> None:
        grandparent, parent, partner, child = (
            person(1, "Grandparent"), person(2, "Parent"), person(3, "Partner"), person(4, "Child")
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", grandparent, parent),
            relationship(2, "partner_of", parent, partner),
            relationship(3, "parent_child", partner, child),
        ]))
        positions = {node.id: node for node in layout.nodes}
        self.assertEqual(positions[2].y, positions[3].y)
        self.assertEqual(abs(positions[2].x - positions[3].x), 190)
        self.assertLess(positions[1].y, positions[2].y)
        self.assertLess(positions[3].y, positions[4].y)

    def test_connector_styles_are_generic_edge_metadata_and_render_with_a_key(self) -> None:
        parent, child, sibling, partner = (
            person(1, "Parent"), person(2, "Child"), person(3, "Sibling"), person(4, "Partner")
        )
        layout = layered_layout(extract_family_graph([
            relationship(1, "parent_child", parent, child),
            relationship(2, "parent_child", parent, sibling),
            relationship(3, "sibling_of", child, sibling),
            relationship(4, "spouse_of", parent, partner),
        ]))
        styles = {edge.label: edge.connector_style for edge in layout.edges}
        self.assertEqual(styles, {"parent": "hierarchy", "spouse": "peer-strong"})

        html = family_tree_page(layout)
        self.assertIn('family-edge-peer-strong', html)
        self.assertNotIn('family-edge-peer"', html)
        self.assertNotIn('legend-sibling', html)
        self.assertIn('family-edge-hierarchy', html)
        self.assertIn('aria-label="Family tree connector key"', html)
        self.assertIn('Partner / spouse', html)
        self.assertRegex(html, r'd="M \d+ \d+ H \d+"')
        self.assertIn('family-edge-bundle', html)
        self.assertRegex(html, r'data-source-set="\d+" data-target-set="\d+(?:,\d+)*"')

    def test_cycles_terminate_and_are_marked_without_duplicate_nodes(self) -> None:
        first, second = person(1, "First"), person(2, "Second")
        layout = layered_layout(extract_family_graph([relationship(1, "parent_child", first, second), relationship(2, "parent_child", second, first)]))
        self.assertEqual(len(layout.nodes), 2)
        self.assertEqual(sum(edge.cyclic for edge in layout.edges), 1)

    def test_full_view_selects_largest_component_and_local_view_filters_by_distance(self) -> None:
        people = [person(index, f"Person {index}") for index in range(1, 7)]
        records = [
            relationship(1, "parent_child", people[0], people[1]),
            relationship(2, "parent_child", people[1], people[2]),
            relationship(3, "partner_of", people[1], people[3]),
            relationship(4, "parent_child", people[4], people[5]),
        ]
        full = full_family_component(records)
        self.assertEqual({node.id for node in full.nodes}, {1, 2, 3, 4})
        local = person_family_subgraph(full, 2, generations=1)
        self.assertEqual({node.id for node in local.nodes}, {1, 2, 3, 4})
        self.assertEqual({node.id for node in person_family_subgraph(full, 1, generations=1).nodes}, {1, 2})

    def test_highlighting_is_presentation_only_and_does_not_change_geometry(self) -> None:
        parent, child, partner = person(1, "Parent"), person(2, "Child"), person(3, "Partner")
        graph = extract_family_graph([
            relationship(1, "partner_of", parent, partner),
            relationship(2, "parent_child", parent, child),
            relationship(3, "parent_child", partner, child),
        ])
        plain = layered_layout(graph)
        highlighted = layered_layout(graph, selected_ids=frozenset({2}))
        self.assertEqual([(node.id, node.x, node.y) for node in plain.nodes], [(node.id, node.x, node.y) for node in highlighted.nodes])
        self.assertEqual([node.id for node in highlighted.nodes if node.selected], [2])
        self.assertIn('family-node-selected', family_tree_page(highlighted))

    def test_complex_blended_fixture_has_non_overlapping_cards_and_exact_groups(self) -> None:
        people = [person(index, f"Family {index}") for index in range(1, 13)]
        pairs = [(1,4),(2,4),(1,5),(2,5),(1,6),(3,6),(4,8),(7,8),(4,9),(7,9),(6,10),(6,11),(12,11)]
        records = [relationship(index, "parent_child", people[source-1], people[target-1]) for index, (source, target) in enumerate(pairs, 1)]
        records += [relationship(20, "spouse_of", people[0], people[1]), relationship(21, "partner_of", people[0], people[2]), relationship(22, "partner_of", people[3], people[6])]
        layout = layered_layout(extract_family_graph(records), selected_ids=frozenset({4}))
        boxes = [(node.id, node.x - 72, node.y - 26, node.x + 72, node.y + 26) for node in layout.nodes]
        for index, first in enumerate(boxes):
            for second in boxes[index + 1:]:
                self.assertFalse(first[1] < second[3] and second[1] < first[3] and first[2] < second[4] and second[2] < first[4])
        html = family_tree_page(layout)
        self.assertIn('data-source-set="1,2" data-target-set="4,5"', html)
        self.assertIn('data-source-set="1,3" data-target-set="6"', html)
        self.assertNotIn('legend-sibling', html)

    def test_empty_input_is_safe(self) -> None:
        layout = layered_layout(extract_family_graph([]))
        self.assertEqual(layout.nodes, ())
        self.assertEqual((layout.width, layout.height), (0, 0))

if __name__ == "__main__":
    unittest.main()
