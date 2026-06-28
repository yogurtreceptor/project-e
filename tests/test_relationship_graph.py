import unittest
from unittest.mock import patch
from app.entities import DEFINITIONS_BY_TYPE, EntityRecord
from app.graph_layout import layered_layout
from app.relationship_graph import GraphEdge, adjacent_family_edge, extract_family_graph
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
            relationship(2, "sibling_of", child, sibling),
            relationship(3, "spouse_of", parent, partner),
        ]))
        styles = {edge.label: edge.connector_style for edge in layout.edges}
        self.assertEqual(styles, {"parent": "hierarchy", "sibling": "peer", "spouse": "peer-strong"})

        html = family_tree_page(layout)
        self.assertIn('family-edge-peer-strong', html)
        self.assertIn('family-edge-peer', html)
        self.assertIn('family-edge-hierarchy', html)
        self.assertIn('aria-label="Family tree connector key"', html)
        self.assertIn('Partner / spouse', html)
        self.assertRegex(html, r'd="M \d+ \d+ H \d+"')
        self.assertRegex(html, r'd="M \d+ \d+ V \d+ H \d+ V \d+"')

    def test_cycles_terminate_and_are_marked_without_duplicate_nodes(self) -> None:
        first, second = person(1, "First"), person(2, "Second")
        layout = layered_layout(extract_family_graph([relationship(1, "parent_child", first, second), relationship(2, "parent_child", second, first)]))
        self.assertEqual(len(layout.nodes), 2)
        self.assertEqual(sum(edge.cyclic for edge in layout.edges), 1)

    def test_empty_input_is_safe(self) -> None:
        layout = layered_layout(extract_family_graph([]))
        self.assertEqual(layout.nodes, ())
        self.assertEqual((layout.width, layout.height), (0, 0))

if __name__ == "__main__":
    unittest.main()
