import tempfile
import unittest
from pathlib import Path

from app import views
from app.audit import AuditFilters, list_audit_events
from app.db import connect, create_entity, create_relationship, initialise_database
from app.entities import DEFINITIONS_BY_TYPE


class SystemToolsViewTests(unittest.TestCase):
    def test_hub_links_all_maintenance_tools(self):
        html = views.system_tools_page()
        for href, label in (
            ("/search", "Search"),
            ("/data-quality", "Data Quality"),
            ("/taxonomies", "Taxonomies"),
            ("/recycle-bin", "Recycle Bin"),
            ("/system-tools/audit", "Audit"),
            ("/system-tools/portability", "Import and Export"),
        ):
            self.assertIn(f'href="{href}"', html)
            self.assertIn(f"<h2>{label}</h2>", html)

    def test_portability_pages_require_preview_and_explicit_confirmation(self):
        page = views.portability_page()
        self.assertIn("Download export", page)
        self.assertIn("Validate and preview", page)
        preview = type("Preview", (), {"exported_at": "2026-07-05", "entities": 2, "deleted_entities": 1, "relationships": 1, "deleted_relationships": 1, "documents": 1})()
        confirmation = views.import_preview_page(preview, "abc")
        self.assertIn("passed manifest, checksum, SQLite integrity", confirmation)
        self.assertIn("Confirm import", confirmation)

    def test_navigation_exposes_tool_hierarchy_and_active_parent(self):
        html = views.layout("Taxonomies", views.taxonomies_page({}), "system-tools")
        nav = html.split('<nav class="browse-nav"', 1)[1].split("</nav>", 1)[0]
        self.assertIn('href="/system-tools" aria-expanded="true"', nav)
        self.assertIn('class="active" aria-current="page" href="/taxonomies"', nav)
        for href in ("/search", "/data-quality", "/recycle-bin", "/system-tools/audit", "/system-tools/portability"):
            self.assertIn(f'href="{href}"', nav)
        self.assertNotIn('action="/search"', html)

    def test_shell_has_accessible_collapsible_browse_and_distinct_search(self):
        html = views.layout("People", "<h1>People</h1>", "people")
        self.assertIn('class="skip-link" href="#main-content"', html)
        self.assertIn('aria-label="Browse"', html)
        self.assertIn('aria-current="page" href="/people"', html)
        self.assertIn('data-sidebar-toggle', html)
        self.assertIn('src="/static/shell.js"', html)
        self.assertIn('class="global-search-link" href="/search"', html)
        self.assertIn('aria-label="Go with Super Key"', html)


class SystemAuditTests(unittest.TestCase):
    def test_filters_events_by_action_and_record_kind(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite3"
            initialise_database(path)
            with connect(path) as connection:
                person = DEFINITIONS_BY_TYPE["person"]
                first = create_entity(connection, person, {"display_name": "First", "given_name": "First"})
                second = create_entity(connection, person, {"display_name": "Second", "given_name": "Second"})
                create_relationship(connection, {"source_entity_id": str(first), "target_entity_id": str(second), "type": "knows"})
                connection.execute("UPDATE audit_events SET event_type='relationship_change' WHERE notes='Relationship created'")
                events = list_audit_events(connection, filters=AuditFilters(event_type="create", record_kind="relationship"))
        self.assertEqual(1, len(events))
        self.assertEqual("relationship", events[0].subject_kind)
        html = views.system_audit_page(events, AuditFilters(event_type="create", record_kind="relationship"))
        self.assertIn("Relationship", html)
        self.assertIn('value="create" selected', html)
        self.assertIn('action="/system-tools/audit"', html)


if __name__ == "__main__":
    unittest.main()
