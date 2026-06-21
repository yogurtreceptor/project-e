import tempfile
import unittest
from pathlib import Path
import sqlite3

from app import views
from app.db import (
    connect,
    create_entity,
    delete_entity,
    get_entity,
    initialise_database,
    list_entities,
    list_favourite_entities,
    list_recent_entities,
    mark_entity_viewed,
    normalise_form_values,
    update_entity,
    create_relationship,
    delete_relationship,
    get_relationship,
    list_relationships,
    list_relationships_for_entity,
    normalise_relationship_values,
    search_entities,
    set_entity_favourite,
    update_relationship,
    validate_entity_values,
    validate_relationship_values,
)
from app.entities import DEFINITIONS_BY_SLUG, ENTITY_DEFINITIONS
from app.geo import build_map_payload


class EntityDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"
        initialise_database(self.database_path)
        self.definition = DEFINITIONS_BY_SLUG["people"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_update_list_and_delete_person(self) -> None:
        with connect(self.database_path) as connection:
            entity_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "Mathematician",
                    "notes": "Known for early computing work.",
                    "title": "",
                    "given_name": "Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "Ada",
                    "email": "",
                    "phone": "",
                },
            )

            created = get_entity(connection, self.definition, entity_id)
            self.assertIsNotNone(created)
            self.assertEqual(created.display_name, "Ada Lovelace")
            self.assertEqual(created.metadata["given_name"], "Ada")

            update_entity(
                connection,
                self.definition,
                entity_id,
                {
                    "display_name": "Augusta Ada Lovelace",
                    "summary": "Computing pioneer",
                    "notes": "",
                    "title": "Countess",
                    "given_name": "Augusta Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "Ada",
                    "email": "ada@example.test",
                    "phone": "",
                },
            )

            updated = get_entity(connection, self.definition, entity_id)
            self.assertEqual(updated.display_name, "Augusta Ada Lovelace")
            self.assertEqual(updated.metadata["email"], "ada@example.test")

            listed = list_entities(connection, self.definition)
            self.assertEqual(len(listed), 1)

            delete_entity(connection, self.definition, entity_id)
            self.assertIsNone(get_entity(connection, self.definition, entity_id))

    def test_all_entity_definitions_use_shared_crud_flow(self) -> None:
        with connect(self.database_path) as connection:
            for definition in ENTITY_DEFINITIONS:
                values = {
                    "display_name": f"Example {definition.singular}",
                    "summary": "Shared flow",
                    "notes": "",
                }
                values.update({field.name: f"{field.label} value" for field in definition.fields})

                entity_id = create_entity(connection, definition, values)
                record = get_entity(connection, definition, entity_id)

                self.assertIsNotNone(record)
                self.assertEqual(record.definition, definition)
                self.assertEqual(record.display_name, f"Example {definition.singular}")
                self.assertNotIn("summary", record.to_form_values())
                self.assertEqual(len(list_entities(connection, definition)), 1)

                delete_entity(connection, definition, entity_id)
                self.assertIsNone(get_entity(connection, definition, entity_id))

    def test_entity_profile_page_has_reusable_sections(self) -> None:
        with connect(self.database_path) as connection:
            entity_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "Computing pioneer",
                    "notes": "Profile notes.",
                    "title": "",
                    "given_name": "Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "",
                    "birthday": "1815-12-10",
                    "email": "ada@example.test",
                    "phone": "",
                },
            )
            record = get_entity(connection, self.definition, entity_id)

        html = views.entity_detail_page(record, [])

        for heading in (
            "Overview",
            "Relationships",
            "Related Entities",
            "Notes",
            "Documents",
            "Timeline",
            "Metadata",
        ):
            self.assertIn(heading, html)
        self.assertIn("1815-12-10", html)
        self.assertNotIn("Summary", html)

    def test_relationships_connect_any_entity_types_bidirectionally(self) -> None:
        organisation_definition = DEFINITIONS_BY_SLUG["organisations"]
        with connect(self.database_path) as connection:
            person_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "",
                    "notes": "",
                    "title": "",
                    "given_name": "Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "",
                    "email": "",
                    "phone": "",
                },
            )
            organisation_id = create_entity(
                connection,
                organisation_definition,
                {
                    "display_name": "Analytical Engine Guild",
                    "summary": "",
                    "notes": "",
                    "organisation_type": "Group",
                    "website": "",
                    "email": "",
                    "phone": "",
                },
            )

            values = normalise_relationship_values(
                {
                    "source_entity_id": str(person_id),
                    "target_entity_id": str(organisation_id),
                    "type": "works_for",
                    "status": "active",
                    "started_at": "1843-01-01",
                    "started_at_precision": "approximate",
                    "notes": "Shared relationship model.",
                }
            )
            self.assertEqual(validate_relationship_values(connection, values), [])
            relationship_id = create_relationship(connection, values)

            relationship = get_relationship(connection, relationship_id)
            self.assertIsNotNone(relationship)
            self.assertEqual(relationship.source.display_name, "Ada Lovelace")
            self.assertEqual(relationship.target.display_name, "Analytical Engine Guild")
            self.assertEqual(relationship.label_from(person_id), "works for")
            self.assertEqual(relationship.label_from(organisation_id), "has worker")
            self.assertEqual(relationship.other_entity(person_id).id, organisation_id)
            self.assertEqual(relationship.started_at, "1843-01-01")
            self.assertEqual(relationship.started_at_precision, "approximate")

            self.assertEqual(len(list_relationships(connection)), 1)
            self.assertEqual(len(list_relationships_for_entity(connection, person_id)), 1)
            self.assertEqual(len(list_relationships_for_entity(connection, organisation_id)), 1)

            update_relationship(
                connection,
                relationship_id,
                {
                    **relationship.to_form_values(),
                    "status": "former",
                    "ended_at": "1852-11-27",
                    "ended_at_precision": "exact",
                },
            )
            updated = get_relationship(connection, relationship_id)
            self.assertEqual(updated.status, "former")
            self.assertEqual(updated.ended_at, "1852-11-27")
            self.assertEqual(updated.ended_at_precision, "exact")

            delete_relationship(connection, relationship_id)
            self.assertIsNone(get_relationship(connection, relationship_id))

    def test_discovery_supports_favourites_recent_and_relationship_search(self) -> None:
        organisation_definition = DEFINITIONS_BY_SLUG["organisations"]
        with connect(self.database_path) as connection:
            person_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "Computing pioneer",
                    "notes": "Mathematician who worked on analytical machinery.",
                    "title": "",
                    "given_name": "Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "",
                    "birthday": "1815-12-10",
                    "email": "ada@example.test",
                    "phone": "",
                },
            )
            organisation_id = create_entity(
                connection,
                organisation_definition,
                {
                    "display_name": "Analytical Engine Guild",
                    "summary": "Research group",
                    "notes": "",
                    "organisation_type": "Group",
                    "website": "",
                    "email": "",
                    "phone": "",
                },
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(person_id),
                    "target_entity_id": str(organisation_id),
                    "type": "works_for",
                    "status": "active",
                    "started_at": "",
                    "started_at_precision": "exact",
                    "ended_at": "",
                    "ended_at_precision": "exact",
                    "notes": "collaboration on computation",
                },
            )

            set_entity_favourite(connection, person_id, True)
            mark_entity_viewed(connection, organisation_id)

            favourites = list_favourite_entities(connection)
            recent = list_recent_entities(connection)
            filtered_people = list_entities(connection, self.definition, "math", True)
            relationship_results = search_entities(connection, "guild")

        self.assertEqual([record.id for record in favourites], [person_id])
        self.assertEqual([record.id for record in recent], [organisation_id])
        self.assertEqual([record.id for record in filtered_people], [person_id])
        result_ids = {result["entity"].id for result in relationship_results}
        self.assertIn(person_id, result_ids)
        self.assertIn(organisation_id, result_ids)

    def test_relationship_validation_rejects_same_or_missing_entities(self) -> None:
        with connect(self.database_path) as connection:
            entity_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "",
                    "notes": "",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "email": "",
                    "phone": "",
                },
            )
            errors = validate_relationship_values(
                connection,
                {
                    "source_entity_id": str(entity_id),
                    "target_entity_id": str(entity_id),
                    "type": "works_for",
                    "status": "active",
                    "started_at": "",
                    "ended_at": "",
                    "notes": "",
                },
            )
            self.assertEqual(errors, ["A relationship must connect two different entities."])

    def test_display_name_is_required(self) -> None:
        values = normalise_form_values(self.definition, {"display_name": "  "})
        errors = validate_entity_values(self.definition, values)
        self.assertEqual(errors, ["Person name is required."])

    def test_summary_is_not_rendered_on_entity_forms(self) -> None:
        for definition in ENTITY_DEFINITIONS:
            html = views.entity_form_page(definition, {}, [], "Create")
            self.assertNotIn('name="summary"', html)
            self.assertNotIn(">Summary<", html)

    def test_controlled_entity_fields_and_custom_values(self) -> None:
        organisation_definition = DEFINITIONS_BY_SLUG["organisations"]
        project_definition = DEFINITIONS_BY_SLUG["projects"]
        asset_definition = DEFINITIONS_BY_SLUG["assets"]

        organisation_html = views.entity_form_page(organisation_definition, {}, [], "Create")
        project_html = views.entity_form_page(project_definition, {}, [], "Create")
        asset_html = views.entity_form_page(asset_definition, {}, [], "Create")

        self.assertIn('list="organisation_type_options"', organisation_html)
        self.assertIn('<option value="Government agency"></option>', organisation_html)
        self.assertIn('<option value="Active" selected>Active</option>', project_html)
        self.assertIn('value="Owned"', asset_html)
        self.assertIn('pattern="[0-9]*"', asset_html)

        custom_values = normalise_form_values(
            organisation_definition,
            {
                "display_name": "Analytical Engine Guild",
                "organisation_type": "Research collective",
            },
        )
        self.assertEqual(custom_values["organisation_type"], "Research collective")

    def test_asset_value_must_be_whole_number_and_displays_as_currency(self) -> None:
        asset_definition = DEFINITIONS_BY_SLUG["assets"]

        for raw_value in ("$1200", "1200.50"):
            values = normalise_form_values(
                asset_definition,
                {"display_name": "Field Laptop", "value": raw_value},
            )
            self.assertEqual(
                validate_entity_values(asset_definition, values),
                ["Value must be a whole number without a dollar sign."],
            )

        with connect(self.database_path) as connection:
            entity_id = create_entity(
                connection,
                asset_definition,
                {
                    "display_name": "Field Laptop",
                    "notes": "",
                    "asset_type": "Computer",
                    "status": "Owned",
                    "serial_number": "ABC123",
                    "acquisition_date": "",
                    "value": "1200",
                    "latitude": "",
                    "longitude": "",
                },
            )
            record = get_entity(connection, asset_definition, entity_id)

        html = views.entity_detail_page(record, [])
        self.assertIn("$1200", html)

    def test_renamed_location_and_asset_fields_migrate_from_legacy_columns(self) -> None:
        legacy_path = Path(self.temp_dir.name) / "legacy-renames.sqlite3"
        with sqlite3.connect(legacy_path) as connection:
            connection.executescript(
                """
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('location', 'asset')),
                    display_name TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_viewed_at TEXT NOT NULL DEFAULT '',
                    is_favourite INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO entities (id, type, display_name, summary, notes, created_at, updated_at)
                VALUES
                    (1, 'location', 'Legacy Place', '', '', 'now', 'now'),
                    (2, 'asset', 'Legacy Laptop', '', '', 'now', 'now');
                CREATE TABLE locations (
                    entity_id INTEGER PRIMARY KEY,
                    formatted_address TEXT NOT NULL DEFAULT '',
                    address_line_1 TEXT NOT NULL DEFAULT '',
                    address_line_2 TEXT NOT NULL DEFAULT '',
                    locality TEXT NOT NULL DEFAULT '',
                    region TEXT NOT NULL DEFAULT '',
                    postal_code TEXT NOT NULL DEFAULT '',
                    country TEXT NOT NULL DEFAULT '',
                    latitude TEXT NOT NULL DEFAULT '',
                    longitude TEXT NOT NULL DEFAULT '',
                    geocoding_source TEXT NOT NULL DEFAULT ''
                );
                INSERT INTO locations (
                    entity_id, locality, region, postal_code, geocoding_source
                )
                VALUES (1, 'Brisbane', 'Queensland', '4000', 'manual');
                CREATE TABLE assets (
                    entity_id INTEGER PRIMARY KEY,
                    asset_type TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    serial_number TEXT NOT NULL DEFAULT '',
                    purchase_date TEXT NOT NULL DEFAULT '',
                    value TEXT NOT NULL DEFAULT '',
                    latitude TEXT NOT NULL DEFAULT '',
                    longitude TEXT NOT NULL DEFAULT ''
                );
                INSERT INTO assets (entity_id, status, purchase_date, value)
                VALUES (2, 'active', '2026-06-21', '1200');
                """
            )

        initialise_database(legacy_path)
        with connect(legacy_path) as connection:
            location = get_entity(connection, DEFINITIONS_BY_SLUG["locations"], 1)
            asset = get_entity(connection, DEFINITIONS_BY_SLUG["assets"], 2)

        self.assertEqual(location.metadata["city"], "Brisbane")
        self.assertEqual(location.metadata["state"], "Queensland")
        self.assertEqual(location.metadata["post_code"], "4000")
        self.assertEqual(location.metadata["source"], "manual")
        self.assertEqual(asset.metadata["status"], "Owned")
        self.assertEqual(asset.metadata["acquisition_date"], "2026-06-21")

    def test_map_payload_uses_location_entities_and_relationships(self) -> None:
        location_definition = DEFINITIONS_BY_SLUG["locations"]
        organisation_definition = DEFINITIONS_BY_SLUG["organisations"]
        with connect(self.database_path) as connection:
            location_id = create_entity(
                connection,
                location_definition,
                {
                    "display_name": "Brisbane City Hall",
                    "summary": "Civic landmark",
                    "notes": "",
                    "formatted_address": "64 Adelaide St, Brisbane City QLD 4000, Australia",
                    "address_line_1": "64 Adelaide St",
                    "address_line_2": "",
                    "suburb": "Brisbane City",
                    "city": "Brisbane",
                    "state": "Queensland",
                    "post_code": "4000",
                    "country": "Australia",
                    "latitude": "-27.4689",
                    "longitude": "153.0235",
                    "source": "manual",
                },
            )
            unmapped_location_id = create_entity(
                connection,
                location_definition,
                {
                    "display_name": "Unplaced archive",
                    "summary": "",
                    "notes": "",
                    "formatted_address": "",
                    "address_line_1": "",
                    "address_line_2": "",
                    "suburb": "",
                    "city": "",
                    "state": "",
                    "post_code": "",
                    "country": "",
                    "latitude": "",
                    "longitude": "",
                    "source": "",
                },
            )
            organisation_id = create_entity(
                connection,
                organisation_definition,
                {
                    "display_name": "City Records Office",
                    "summary": "",
                    "notes": "",
                    "organisation_type": "Office",
                    "website": "",
                    "email": "",
                    "phone": "",
                },
            )
            person_id = create_entity(
                connection,
                self.definition,
                {
                    "display_name": "Ada Lovelace",
                    "summary": "",
                    "notes": "",
                    "title": "",
                    "given_name": "Ada",
                    "middle_name": "",
                    "family_name": "Lovelace",
                    "preferred_name": "",
                    "birthday": "",
                    "email": "",
                    "phone": "",
                },
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(organisation_id),
                    "target_entity_id": str(location_id),
                    "type": "located_at",
                    "status": "active",
                    "started_at": "",
                    "started_at_precision": "exact",
                    "ended_at": "",
                    "ended_at_precision": "exact",
                    "notes": "",
                },
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(person_id),
                    "target_entity_id": str(unmapped_location_id),
                    "type": "located_at",
                    "status": "active",
                    "started_at": "",
                    "started_at_precision": "exact",
                    "ended_at": "",
                    "ended_at_precision": "exact",
                    "notes": "",
                },
            )

            payload = build_map_payload(connection)

        layers = {layer["id"] for layer in payload["layers"]}
        marker_titles = {marker["title"] for marker in payload["markers"]}
        marker_layers = {marker["title"]: marker["layerId"] for marker in payload["markers"]}
        enabled_layers = {layer["id"] for layer in payload["layers"] if layer["enabled"]}
        self.assertEqual(layers, {"locations", "organisations", "people", "assets"})
        self.assertEqual(enabled_layers, {"locations"})
        self.assertIn("Brisbane City Hall", marker_titles)
        self.assertIn("City Records Office", marker_titles)
        self.assertNotIn("Unplaced archive", marker_titles)
        self.assertNotIn("Ada Lovelace", marker_titles)
        self.assertEqual(marker_layers["Brisbane City Hall"], "locations")
        self.assertEqual(marker_layers["City Records Office"], "organisations")

    def test_new_domains_share_entity_relationship_search_and_map_architecture(self) -> None:
        project_definition = DEFINITIONS_BY_SLUG["projects"]
        document_definition = DEFINITIONS_BY_SLUG["documents"]
        asset_definition = DEFINITIONS_BY_SLUG["assets"]
        location_definition = DEFINITIONS_BY_SLUG["locations"]
        with connect(self.database_path) as connection:
            project_id = create_entity(
                connection,
                project_definition,
                {
                    "display_name": "Operation Eddy",
                    "summary": "Local-first information platform",
                    "notes": "",
                    "project_type": "Software",
                    "status": "Active",
                    "started_at": "2026-06-21",
                },
            )
            document_id = create_entity(
                connection,
                document_definition,
                {
                    "display_name": "Architecture Note",
                    "summary": "Documents are entities",
                    "notes": "",
                    "document_type": "Note",
                    "document_date": "2026-06-21",
                    "issuer": "",
                    "file_name": "architecture.txt",
                    "file_path": "documents/example.txt",
                    "mime_type": "text/plain",
                    "file_size": "12 B",
                },
            )
            asset_id = create_entity(
                connection,
                asset_definition,
                {
                    "display_name": "Field Laptop",
                    "summary": "Work asset",
                    "notes": "",
                    "asset_type": "Laptop",
                    "status": "Owned",
                    "serial_number": "ABC123",
                    "acquisition_date": "2026-06-21",
                    "value": "1200",
                    "latitude": "-27.4700",
                    "longitude": "153.0200",
                },
            )
            location_id = create_entity(
                connection,
                location_definition,
                {
                    "display_name": "Project Office",
                    "summary": "",
                    "notes": "",
                    "formatted_address": "Brisbane QLD, Australia",
                    "address_line_1": "",
                    "address_line_2": "",
                    "suburb": "",
                    "city": "Brisbane",
                    "state": "Queensland",
                    "post_code": "",
                    "country": "Australia",
                    "latitude": "-27.4689",
                    "longitude": "153.0235",
                    "source": "manual",
                },
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(document_id),
                    "target_entity_id": str(project_id),
                    "type": "references",
                    "status": "active",
                    "started_at": "",
                    "started_at_precision": "exact",
                    "ended_at": "",
                    "ended_at_precision": "exact",
                    "notes": "architecture milestone",
                },
            )
            create_relationship(
                connection,
                {
                    "source_entity_id": str(asset_id),
                    "target_entity_id": str(location_id),
                    "type": "located_at",
                    "status": "active",
                    "started_at": "",
                    "started_at_precision": "exact",
                    "ended_at": "",
                    "ended_at_precision": "exact",
                    "notes": "",
                },
            )

            relationship_results = search_entities(connection, "architecture milestone")
            payload = build_map_payload(connection)

        result_ids = {result["entity"].id for result in relationship_results}
        self.assertIn(project_id, result_ids)
        self.assertIn(document_id, result_ids)
        marker_layers = {marker["title"]: marker["layerId"] for marker in payload["markers"]}
        self.assertEqual(marker_layers["Field Laptop"], "assets")
        self.assertEqual(marker_layers["Project Office"], "locations")
        self.assertNotIn("Operation Eddy", marker_layers)
        self.assertNotIn("Architecture Note", marker_layers)

    def test_entity_type_constraint_migrates_for_new_domains(self) -> None:
        legacy_path = Path(self.temp_dir.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_path) as connection:
            connection.executescript(
                """
                CREATE TABLE entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK (type IN ('person', 'organisation', 'location')),
                    display_name TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_viewed_at TEXT NOT NULL DEFAULT '',
                    is_favourite INTEGER NOT NULL DEFAULT 0
                );
                """
            )

        initialise_database(legacy_path)
        with connect(legacy_path) as connection:
            project_id = create_entity(
                connection,
                DEFINITIONS_BY_SLUG["projects"],
                {
                    "display_name": "House Purchase",
                    "summary": "",
                    "notes": "",
                    "project_type": "Personal",
                    "status": "Active",
                    "started_at": "",
                },
            )
            project = get_entity(connection, DEFINITIONS_BY_SLUG["projects"], project_id)

        self.assertIsNotNone(project)

    def test_map_page_contains_layer_controls_and_marker_links(self) -> None:
        payload = {
            "defaultCenter": {"latitude": -27.4698, "longitude": 153.0251, "zoom": 11},
            "layers": [
                {"id": "locations", "label": "Locations", "entity_type": "location", "enabled": True},
                {"id": "organisations", "label": "Organisations", "entity_type": "organisation", "enabled": False},
            ],
            "markers": [
                {
                    "id": "locations-1",
                    "layerId": "locations",
                    "entityId": 1,
                    "entityType": "location",
                    "title": "Brisbane City Hall",
                    "entityLabel": "Location",
                    "locationTitle": "Brisbane City Hall",
                    "address": "64 Adelaide St",
                    "latitude": -27.4689,
                    "longitude": 153.0235,
                    "url": "/locations/1",
                }
            ],
        }

        html = views.map_page(payload)

        self.assertIn('data-layer-toggle="locations" checked', html)
        self.assertIn('data-layer-toggle="organisations">', html)
        self.assertIn("Brisbane City Hall", html)
        self.assertIn("/locations/1", html)

    def test_location_form_uses_explicit_address_lookup(self) -> None:
        location_definition = DEFINITIONS_BY_SLUG["locations"]

        html = views.entity_form_page(location_definition, {}, [], "Create")

        self.assertIn('id="address_search_button"', html)
        self.assertIn('id="address_results"', html)
        self.assertIn("Search Address", html)
        self.assertNotIn("address_suggestions", html)


if __name__ == "__main__":
    unittest.main()
