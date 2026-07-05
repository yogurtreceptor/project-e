import tempfile
import unittest
from pathlib import Path

from app.db import connect, create_entity, get_entity, initialise_database, search_entities
from app.duplicate_detection import find_duplicate_entities
from app.entities import ASSET_TYPES, DEFINITIONS_BY_TYPE, DOCUMENT_TYPES
from app.timeline import registry as timeline_registry


class DomainModelCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "domain.postgres"
        initialise_database(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_organisation_aliases_are_repeatable_searchable_and_duplicate_inputs(self) -> None:
        definition = DEFINITIONS_BY_TYPE["organisation"]
        with connect(self.database_path) as connection:
            entity_id = create_entity(connection, definition, {
                "display_name": "Australian Taxation Office",
                "organisation_type": "",
                "aliases": "ATO\nTax Office",
            })
            record = get_entity(connection, definition, entity_id)
            results = search_entities(connection, "ATO")
            name_matches = find_duplicate_entities(connection, definition, {
                "display_name": "ATO", "aliases": "",
            })
            alias_matches = find_duplicate_entities(connection, definition, {
                "display_name": "Different", "aliases": "Tax Office",
            })

        self.assertEqual(record.metadata["aliases"], "ATO\nTax Office")
        self.assertEqual([item["entity"].id for item in results], [entity_id])
        self.assertEqual(name_matches[0].matched_fields, ("Name",))
        self.assertEqual(alias_matches[0].matched_fields, ("Other names",))

    def test_project_target_and_end_dates_feed_timeline(self) -> None:
        definition = DEFINITIONS_BY_TYPE["project"]
        with connect(self.database_path) as connection:
            entity_id = create_entity(connection, definition, {
                "display_name": "Archive migration",
                "target_date": "2026-08-01",
                "ended_at": "2026-08-03",
            })
            record = get_entity(connection, definition, entity_id)
        events = timeline_registry.derive(record, [])
        self.assertEqual(
            [(event.date, event.title) for event in events],
            [("2026-08-03", "Project ended"), ("2026-08-01", "Project target date")],
        )

    def test_document_purposes_and_asset_types_do_not_mix_formats_or_records(self) -> None:
        self.assertIn("Licence", DOCUMENT_TYPES)
        self.assertIn("Statement", DOCUMENT_TYPES)
        self.assertNotIn("PDF", DOCUMENT_TYPES)
        self.assertNotIn("Image", DOCUMENT_TYPES)
        self.assertNotIn("Document-like asset", ASSET_TYPES)
        document_fields = {field.name for field in DEFINITIONS_BY_TYPE["document"].fields}
        self.assertNotIn("issuer", document_fields)

    def test_postgresql_baseline_has_no_legacy_document_issuer(self) -> None:
        with connect(self.database_path) as connection:
            columns = {row["name"] for row in connection.execute(
                "SELECT column_name AS name FROM information_schema.columns WHERE table_name='documents'"
            )}
        self.assertNotIn("issuer", columns)


if __name__ == "__main__":
    unittest.main()
