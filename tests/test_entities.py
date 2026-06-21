import tempfile
import unittest
from pathlib import Path

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
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "email": "",
                    "phone": "",
                },
            )

            created = get_entity(connection, self.definition, entity_id)
            self.assertIsNotNone(created)
            self.assertEqual(created.display_name, "Ada Lovelace")
            self.assertEqual(created.field_value(self.definition.fields[0]), "Ada")

            update_entity(
                connection,
                self.definition,
                entity_id,
                {
                    "display_name": "Augusta Ada Lovelace",
                    "summary": "Computing pioneer",
                    "notes": "",
                    "given_name": "Augusta Ada",
                    "family_name": "Lovelace",
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
                self.assertEqual(record.to_form_values()["summary"], "Shared flow")
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
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "birthday": "1815-12-10",
                    "occupation": "Mathematician",
                    "email": "ada@example.test",
                    "phone": "",
                },
            )
            record = get_entity(connection, self.definition, entity_id)

        html = views.entity_detail_page(record, [], [])

        for heading in (
            "Overview",
            "Relationships",
            "Related Entities",
            "Notes",
            "Attachments",
            "Timeline",
            "Metadata",
        ):
            self.assertIn(heading, html)
        self.assertIn("1815-12-10", html)
        self.assertIn("Mathematician", html)

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
                    "given_name": "Ada",
                    "family_name": "Lovelace",
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
                    "notes": "Worked on analytical machinery.",
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "birthday": "1815-12-10",
                    "occupation": "Mathematician",
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
                    "address_line_1": "",
                    "locality": "",
                    "region": "",
                    "country": "",
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


if __name__ == "__main__":
    unittest.main()

