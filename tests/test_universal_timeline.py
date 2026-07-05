import tempfile
import unittest
from pathlib import Path

from app import views
from app.db import (
    connect,
    create_entity,
    create_relationship,
    initialise_database,
    list_all_entities,
    list_relationships,
)
from app.entities import DEFINITIONS_BY_TYPE
from app.timeline import TimelineFilters, registry


class UniversalTimelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "timeline.sqlite3"
        initialise_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_derives_one_chronological_stream_with_origin_links(self) -> None:
        with connect(self.database_path) as connection:
            person_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["person"],
                {"display_name": "Ada Lovelace", "given_name": "Ada", "family_name": "Lovelace", "birthday": "1815-12-10"},
            )
            project_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["project"],
                {"display_name": "Analytical Engine", "status": "Active", "started_at": "1840-01-01"},
            )
            relationship_id = create_relationship(
                connection,
                {
                    "source_entity_id": str(person_id),
                    "target_entity_id": str(project_id),
                    "type": "project_contributor",
                    "status": "active",
                    "started_at": "1842-01-01",
                },
            )
            records = list_all_entities(connection)
            relationships = list_relationships(connection)

        events = registry.derive_all(records, relationships)

        self.assertEqual([event.date for event in events], ["1842-01-01", "1840-01-01", "1815-12-10"])
        self.assertEqual(sum(event.category == "relationship" for event in events), 1)
        self.assertEqual(events[0].href, f"/relationships/{relationship_id}")
        self.assertEqual(events[1].href, f"/projects/{project_id}")

    def test_filters_by_type_range_and_directly_related_entities(self) -> None:
        with connect(self.database_path) as connection:
            person_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["person"],
                {"display_name": "Ada Lovelace", "given_name": "Ada", "family_name": "Lovelace", "birthday": "1815-12-10"},
            )
            document_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["document"],
                {"display_name": "Notes", "document_date": "1843-01-01"},
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(document_id),
                    "target_entity_id": str(person_id),
                    "type": "document_references_person",
                    "status": "active",
                },
            )
            records = list_all_entities(connection)
            relationships = list_relationships(connection)

        events = registry.derive_all(
            records,
            relationships,
            TimelineFilters(
                entity_type="document",
                date_from="1840-01-01",
                date_to="1850-01-01",
                related_person_id=person_id,
            ),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].href, f"/documents/{document_id}")

    def test_project_end_and_document_expiry_are_timeline_events(self) -> None:
        with connect(self.database_path) as connection:
            create_entity(
                connection,
                DEFINITIONS_BY_TYPE["project"],
                {"display_name": "Migration", "started_at": "2026-01-01", "ended_at": "2026-06-30"},
            )
            create_entity(
                connection,
                DEFINITIONS_BY_TYPE["document"],
                {"display_name": "Licence", "expiry_date": "2028-07-05"},
            )
            records = list_all_entities(connection)

        events = registry.derive_all(records, [])

        self.assertIn(("2026-06-30", "Project ended"), [(event.date, event.title) for event in events])
        self.assertIn(("2028-07-05", "Document expires"), [(event.date, event.title) for event in events])

    def test_page_renders_filters_links_and_clean_empty_state(self) -> None:
        filters = TimelineFilters(entity_type="person", date_from="1900-01-01")
        options = {"person": [], "organisation": [], "project": []}

        html = views.universal_timeline_page([], filters, options)

        self.assertIn("Universal Timeline", html)
        self.assertIn('name="person"', html)
        self.assertIn('name="organisation"', html)
        self.assertIn('name="project"', html)
        self.assertIn("No timeline entries match these filters.", html)


if __name__ == "__main__":
    unittest.main()
