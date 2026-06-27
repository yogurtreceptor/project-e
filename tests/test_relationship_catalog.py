import unittest
from itertools import combinations_with_replacement

from app.relationships import (
    RELATIONSHIP_TYPES,
    RELATIONSHIP_TYPES_BY_KEY,
    relationship_types_for_pair,
    role_label,
)


EXPECTED_SELECTABLE_KEYS_BY_PAIR = {
    ("person", "person"): (
        "parent_child", "sibling_of", "spouse_of", "partner_of",
        "grandparent_child", "aunt_uncle_niece_nephew", "cousin_of",
        "family_other", "coworker_of", "manager_person", "team_member_of",
        "student_teacher", "classmate_of", "clinician_patient", "friend_of",
        "knows", "person_person_other",
    ),
    ("person", "organisation"): (
        "works_for", "manager_at", "director_of", "member_of",
        "volunteer_for", "student_at", "patient_client_of", "customer_of",
        "owner_of", "person_organisation_other",
    ),
    ("person", "location"): (
        "lives_at", "works_at_location", "visited_location", "born_at",
        "person_located_at", "person_location_other",
    ),
    ("person", "project"): (
        "project_involves_person", "project_managed_by", "project_owned_by",
        "project_contributor", "person_project_other",
    ),
    ("organisation", "location"): (
        "located_at_org", "headquartered_at", "branch_at", "operates_at",
        "organisation_location_other",
    ),
    ("organisation", "project"): (
        "project_involves_organisation", "project_sponsored_by",
        "project_owned_by_organisation", "organisation_project_other",
    ),
    ("asset", "location"): (
        "stored_at", "asset_located_at", "last_known_at",
        "asset_location_other",
    ),
    ("document", "person"): (
        "document_belongs_to_person", "document_created_by_person",
        "document_issued_to_person", "document_references_person",
        "document_person_other",
    ),
    ("document", "organisation"): (
        "document_belongs_to_organisation",
        "document_created_by_organisation",
        "document_issued_by_organisation",
        "document_references_organisation", "document_organisation_other",
    ),
    ("document", "asset"): (
        "document_belongs_to_asset", "receipt_for", "manual_for",
        "document_references_asset", "document_asset_other",
    ),
    ("document", "project"): (
        "document_belongs_to_project", "document_created_for_project",
        "references", "document_project_other",
    ),
}


class RelationshipCatalogueTests(unittest.TestCase):
    def test_keys_are_unique_and_indexed(self) -> None:
        keys = [relationship_type.key for relationship_type in RELATIONSHIP_TYPES]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), set(RELATIONSHIP_TYPES_BY_KEY))

    def test_selectable_keys_for_every_entity_pair(self) -> None:
        entity_types = (
            "person", "organisation", "location",
            "project", "document", "asset",
        )
        for pair in combinations_with_replacement(entity_types, 2):
            expected_keys = EXPECTED_SELECTABLE_KEYS_BY_PAIR.get(
                pair, EXPECTED_SELECTABLE_KEYS_BY_PAIR.get(tuple(reversed(pair)), ())
            )
            with self.subTest(pair=pair):
                actual = tuple(item.key for item in relationship_types_for_pair(*pair))
                reverse = tuple(item.key for item in relationship_types_for_pair(*reversed(pair)))
                self.assertEqual(actual, expected_keys)
                self.assertEqual(reverse, expected_keys)

    def test_gender_aware_roles_and_display_labels_are_catalogue_metadata(self) -> None:
        parent_child = RELATIONSHIP_TYPES_BY_KEY["parent_child"]
        self.assertEqual(role_label(parent_child, "source", "Female"), "Mother")
        self.assertEqual(role_label(parent_child, "target", "Male"), "Son")
        self.assertEqual(parent_child.label_for_role("source", "Female"), "mother of")
        self.assertEqual(parent_child.label_for_role("target", "Male"), "son of")

        sibling = RELATIONSHIP_TYPES_BY_KEY["sibling_of"]
        self.assertEqual(role_label(sibling, "source", "Unknown"), "Sibling")
        self.assertEqual(sibling.label_for_role("target", "Female"), "sister of")


if __name__ == "__main__":
    unittest.main()
