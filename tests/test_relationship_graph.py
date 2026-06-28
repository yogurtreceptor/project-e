import unittest
from unittest.mock import patch
from app.entities import DEFINITIONS_BY_TYPE, EntityRecord
from app.graph_layout import layered_layout
from app.relationship_graph import GraphEdge, adjacent_family_edge, extract_family_graph
from app.relationships import RelationshipRecord

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
