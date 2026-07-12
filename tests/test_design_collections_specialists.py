import unittest

from app import views
from app.entities import DEFINITIONS_BY_SLUG, EntityRecord
from app.graph_layout import GraphLayout, PositionedEdge, PositionedNode


def record(slug, metadata):
    definition = DEFINITIONS_BY_SLUG[slug]
    return EntityRecord(1, definition, "Example", "", "", "now", "now", "now", False, metadata)


class CollectionAndSpecialistDesignTests(unittest.TestCase):
    def test_domain_indexes_use_priority_columns_and_accessible_overflow(self):
        cases = {
            "people": ("DOB", "Email"), "organisations": ("Classification", "Email"),
            "locations": ("City", "State"), "projects": ("Status", "Target"),
            "documents": ("Purpose", "Expiry"), "assets": ("Type", "Status"),
        }
        for slug, headings in cases.items():
            html = views.entity_list_page(DEFINITIONS_BY_SLUG[slug], [record(slug, {})])
            self.assertIn('class="table-scroll" tabindex="0" role="region"', html)
            self.assertIn(f'aria-label="{DEFINITIONS_BY_SLUG[slug].plural} records"', html)
            for heading in headings: self.assertIn(f"<th>{heading}</th>", html)
            self.assertNotIn(">Delete</button>", html)
            self.assertNotIn("<th>Notes</th>", html)

    def test_filtered_and_unfiltered_empty_collections_are_distinct(self):
        definition = DEFINITIONS_BY_SLUG["people"]
        self.assertIn("No people yet", views.entity_list_page(definition, []))
        filtered = views.entity_list_page(definition, [], query="nobody")
        self.assertIn("No matches", filtered)
        self.assertIn("Clear filters", filtered)

    def test_map_has_keyboard_region_text_alternative_and_remote_failure(self):
        payload = {"defaultCenter": {"latitude": 0, "longitude": 0, "zoom": 2}, "layers": [], "markers": []}
        html = views.map_page(payload)
        self.assertIn('role="region" tabindex="0" aria-label="Entity map"', html)
        self.assertIn("Interactive map unavailable", html)
        self.assertIn("canonical coordinates remain available", html)
        self.assertIn("map-remote-status')?.setAttribute('hidden'", html)

    def test_family_tree_has_keyboard_region_and_text_relationships(self):
        tree = GraphLayout((PositionedNode(1, "Parent", "/people/1", 100, 80), PositionedNode(2, "Child", "/people/2", 100, 210)), (PositionedEdge(1, 2, "parent of"),), 300, 300)
        html = views.family_tree_page(tree)
        self.assertIn('tabindex="0" role="region" aria-label="Scrollable family relationship tree"', html)
        self.assertIn('href="/people/1">Parent</a>', html)
        self.assertIn("parent of", html)
        self.assertIn('href="/people/2">Child</a>', html)

if __name__ == "__main__": unittest.main()
