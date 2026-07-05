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
        ):
            self.assertIn(f'href="{href}"', html)
            self.assertIn(f"<h2>{label}</h2>", html)

    def test_navigation_replaces_individual_tool_links_with_active_hub(self):
        html = views.layout("Tools", views.system_tools_page(), "system-tools")
        nav = html.split("<nav>", 1)[1].split("</nav>", 1)[0]
        self.assertIn('<a class="active" href="/system-tools">System Tools</a>', nav)
        self.assertNotIn('href="/taxonomies"', nav)
        self.assertNotIn('href="/data-quality"', nav)
        self.assertNotIn('href="/recycle-bin"', nav)
        self.assertNotIn('href="/search"', nav)
        self.assertIn('action="/search"', html)


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
