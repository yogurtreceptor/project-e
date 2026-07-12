import unittest
from pathlib import Path

from app import views
from app.audit import AuditFilters
from app.entities import DEFINITIONS_BY_SLUG, EntityRecord


def record(slug, metadata=None):
    definition = DEFINITIONS_BY_SLUG[slug]
    return EntityRecord(9, definition, "Example", "", "Notes", "now", "now", "now", False, metadata or {})


class RemainingRouteConversionTests(unittest.TestCase):
    def test_every_entity_family_uses_concise_overview_without_admin_or_duplicates(self):
        expected = {"people": "Contact", "organisations": "Organisation details", "locations": "Geography", "projects": "Milestones", "documents": "Document", "assets": "Asset details"}
        for slug, heading in expected.items():
            html = views.entity_detail_page(record(slug), [])
            self.assertIn(heading, html)
            self.assertIn("Relationships", html)
            self.assertNotIn("Related Entities", html)
            self.assertNotIn("<h2>Metadata</h2>", html)
            self.assertNotIn("<h2>Change History</h2>", html)

    def test_system_admin_tables_use_accessible_compact_regions(self):
        audit = views.system_audit_page([], AuditFilters())
        self.assertIn("No matching audit events", audit)
        quality = views.data_quality_page([])
        self.assertIn("No data quality findings", quality)
        recycled = views.recycle_bin_page([])
        self.assertIn("Recycle Bin is empty", recycled)
        for html in (audit, quality):
            self.assertNotIn("Review · Open record", html)

    def test_record_scoped_audit_preserves_context(self):
        filters = AuditFilters(record_kind="relationship", record_id=42)
        html = views.system_audit_page([], filters)
        self.assertIn('name="record_id" value="42"', html)
        self.assertIn('name="record_kind" value="relationship"', html)
        self.assertIn("Filtered to relationship 42", html)

    def test_taxonomy_archive_uses_shared_confirmation_contract(self):
        class Entry:
            id=3; active=True; path="Type / Example"; depth=1; label="Example"
        html = views.taxonomies_page({"organisation_classification": [Entry()], "relationship_type": []})
        self.assertIn('data-confirm-object="Type / Example"', html)
        self.assertIn("Existing records retain it", html)
        self.assertNotIn("confirm(", html)

    def test_stylesheet_has_no_component_colour_literals_or_tool_translation(self):
        css = Path("app/static/styles.css").read_text()
        import re
        self.assertEqual([], re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\(", css))
        self.assertNotIn("translateY", css)
        self.assertIn(".table-compact", css)


if __name__ == "__main__": unittest.main()
