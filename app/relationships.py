from dataclasses import dataclass

from app.entities import DEFINITIONS_BY_TYPE, EntityRecord


@dataclass(frozen=True)
class RelationshipType:
    key: str
    source_type: str
    target_type: str
    category: str
    subtype: str
    label: str
    inverse_label: str
    directional: bool = True
    notes: str = ""
    selectable: bool = True

    @property
    def display_label(self) -> str:
        if self.category and self.subtype and self.category != self.subtype:
            return f"{self.category}: {self.subtype}"
        return self.subtype or self.label

    @property
    def pairs(self) -> tuple[tuple[str, str], ...]:
        return ((self.source_type, self.target_type),)

    def supports_pair(self, source_type: str, target_type: str) -> bool:
        return self._matches(source_type, target_type) or self._matches(target_type, source_type)

    def is_canonical_direction(self, source_type: str, target_type: str) -> bool:
        return self._matches(source_type, target_type)

    def _matches(self, source_type: str, target_type: str) -> bool:
        return (self.source_type in {source_type, "entity"}) and (self.target_type in {target_type, "entity"})


@dataclass(frozen=True)
class RelationshipRecord:
    id: int
    type_key: str
    source: EntityRecord
    target: EntityRecord
    status: str
    started_at: str
    started_at_precision: str
    ended_at: str
    ended_at_precision: str
    notes: str
    created_at: str
    updated_at: str

    @property
    def type(self) -> RelationshipType:
        return RELATIONSHIP_TYPES_BY_KEY.get(
            self.type_key,
            RelationshipType(
                self.type_key,
                self.source.type,
                self.target.type,
                "Legacy / Other",
                self.type_key.replace("_", " "),
                self.type_key.replace("_", " "),
                self.type_key.replace("_", " "),
                directional=False,
                notes="Unknown legacy relationship type.",
                selectable=False,
            ),
        )

    @property
    def label(self) -> str:
        return self.label_from(self.source.id)

    def label_from(self, entity_id: int) -> str:
        if entity_id == self.source.id:
            return relationship_label_for_entity(self.type, self.source, self.target, from_source=True)
        if entity_id == self.target.id:
            return relationship_label_for_entity(self.type, self.source, self.target, from_source=False)
        return self.type.label

    def other_entity(self, entity_id: int) -> EntityRecord:
        if entity_id == self.source.id:
            return self.target
        if entity_id == self.target.id:
            return self.source
        raise ValueError(f"Entity {entity_id} is not part of relationship {self.id}")

    def to_form_values(self) -> dict[str, str]:
        return {
            "source_entity_id": str(self.source.id),
            "target_entity_id": str(self.target.id),
            "type": self.type_key,
            "status": self.status,
            "started_at": self.started_at,
            "started_at_precision": self.started_at_precision,
            "ended_at": self.ended_at,
            "ended_at_precision": self.ended_at_precision,
            "notes": self.notes,
        }


def rt(
    key: str,
    source_type: str,
    target_type: str,
    category: str,
    subtype: str,
    label: str,
    inverse_label: str,
    directional: bool = True,
    notes: str = "",
    selectable: bool = True,
) -> RelationshipType:
    return RelationshipType(
        key,
        source_type,
        target_type,
        category,
        subtype,
        label,
        inverse_label,
        directional=directional,
        notes=notes,
        selectable=selectable,
    )


RELATIONSHIP_TYPES: tuple[RelationshipType, ...] = (
    rt("parent_child", "person", "person", "Family", "Parent / child", "parent of", "child of", notes="Neutral family-tree-ready parent to child relationship."),
    rt("sibling_of", "person", "person", "Family", "Sibling", "sibling of", "sibling of", directional=False),
    rt("spouse_of", "person", "person", "Family", "Spouse", "spouse of", "spouse of", directional=False),
    rt("partner_of", "person", "person", "Family", "Partner", "partner of", "partner of", directional=False),
    rt("grandparent_child", "person", "person", "Family", "Grandparent / grandchild", "grandparent of", "grandchild of"),
    rt("aunt_uncle_niece_nephew", "person", "person", "Family", "Aunt/uncle / niece/nephew", "aunt/uncle of", "niece/nephew of"),
    rt("cousin_of", "person", "person", "Family", "Cousin", "cousin of", "cousin of", directional=False),
    rt("family_other", "person", "person", "Family", "Other family", "family of", "family of", directional=False),
    rt("coworker_of", "person", "person", "Work", "Coworker", "coworker of", "coworker of", directional=False),
    rt("manager_person", "person", "person", "Work", "Manager / reports to", "manager of", "reports to"),
    rt("team_member_of", "person", "person", "Work", "Team member", "team member of", "team member of", directional=False),
    rt("student_teacher", "person", "person", "Education", "Student / teacher", "teacher of", "student of"),
    rt("classmate_of", "person", "person", "Education", "Classmate", "classmate of", "classmate of", directional=False),
    rt("clinician_patient", "person", "person", "Health", "Clinician / patient", "clinician for", "patient of"),
    rt("friend_of", "person", "person", "Social", "Friend", "friend of", "friend of", directional=False),
    rt("knows", "person", "person", "Social", "Other social", "knows", "knows", directional=False),
    rt("person_person_other", "person", "person", "Other", "Other", "related to", "related to", directional=False),
    rt("works_for", "person", "organisation", "Role", "Employee / employer", "employee of", "employer of"),
    rt("manager_at", "person", "organisation", "Role", "Manager", "manager at", "managed by"),
    rt("director_of", "person", "organisation", "Role", "Director", "director of", "directed by"),
    rt("member_of", "person", "organisation", "Membership", "Member", "member of", "has member"),
    rt("volunteer_for", "person", "organisation", "Role", "Volunteer", "volunteer for", "has volunteer"),
    rt("student_at", "person", "organisation", "Education", "Student", "student at", "educational institution for"),
    rt("patient_client_of", "person", "organisation", "Service", "Patient / client", "patient/client of", "provider for"),
    rt("customer_of", "person", "organisation", "Service", "Customer", "customer of", "provider for"),
    rt("owner_of", "person", "organisation", "Ownership", "Owner", "owner of", "owned by"),
    rt("person_organisation_other", "person", "organisation", "Other", "Other", "associated with", "associated with", directional=False),
    rt("lives_at", "person", "location", "Location", "Lives at", "lives at", "residence of"),
    rt("works_at_location", "person", "location", "Location", "Works at", "works at", "workplace of"),
    rt("visited_location", "person", "location", "Location", "Visited", "visited", "visited by"),
    rt("born_at", "person", "location", "Location", "Born at", "born at", "birthplace of"),
    rt("person_located_at", "person", "location", "Location", "Located at", "located at", "location of"),
    rt("person_location_other", "person", "location", "Other", "Other", "associated with", "associated with", directional=False),
    rt("project_involves_person", "project", "person", "Project", "Involves", "involves", "involved in"),
    rt("project_managed_by", "project", "person", "Project", "Managed by", "managed by", "manages"),
    rt("project_owned_by", "project", "person", "Project", "Owner", "owned by", "owns project"),
    rt("project_contributor", "person", "project", "Project", "Contributor", "contributes to", "has contributor"),
    rt("person_project_other", "person", "project", "Other", "Other", "associated with", "associated with", directional=False),
    rt("located_at_org", "organisation", "location", "Location", "Located at", "located at", "location of"),
    rt("headquartered_at", "organisation", "location", "Location", "Headquartered at", "headquartered at", "headquarters of"),
    rt("branch_at", "organisation", "location", "Location", "Branch at", "branch at", "branch location for"),
    rt("operates_at", "organisation", "location", "Location", "Operates at", "operates at", "operating location for"),
    rt("organisation_location_other", "organisation", "location", "Other", "Other", "associated with", "associated with", directional=False),
    rt("project_involves_organisation", "project", "organisation", "Project", "Involves", "involves", "involved in"),
    rt("project_sponsored_by", "project", "organisation", "Project", "Sponsored by", "sponsored by", "sponsors"),
    rt("project_owned_by_organisation", "project", "organisation", "Project", "Owner", "owned by", "owns project"),
    rt("organisation_project_other", "organisation", "project", "Other", "Other", "associated with", "associated with", directional=False),
    rt("stored_at", "asset", "location", "Location", "Stored at", "stored at", "stores"),
    rt("asset_located_at", "asset", "location", "Location", "Located at", "located at", "location of"),
    rt("last_known_at", "asset", "location", "Location", "Last known at", "last known at", "last known location for"),
    rt("asset_location_other", "asset", "location", "Other", "Other", "associated with", "associated with", directional=False),
    rt("document_belongs_to_person", "document", "person", "Document", "Belongs to", "belongs to", "has document"),
    rt("document_created_by_person", "document", "person", "Document", "Created by", "created by", "created"),
    rt("document_issued_to_person", "document", "person", "Document", "Issued to", "issued to", "holds issued document"),
    rt("document_references_person", "document", "person", "Document", "References", "references", "referenced by"),
    rt("document_person_other", "document", "person", "Document", "Other", "relates to", "related document", directional=False),
    rt("document_belongs_to_organisation", "document", "organisation", "Document", "Belongs to", "belongs to", "has document"),
    rt("document_created_by_organisation", "document", "organisation", "Document", "Created by", "created by", "created"),
    rt("document_issued_by_organisation", "document", "organisation", "Document", "Issued by", "issued by", "issued"),
    rt("document_references_organisation", "document", "organisation", "Document", "References", "references", "referenced by"),
    rt("document_organisation_other", "document", "organisation", "Document", "Other", "relates to", "related document", directional=False),
    rt("document_belongs_to_asset", "document", "asset", "Document", "Belongs to", "belongs to", "has document"),
    rt("receipt_for", "document", "asset", "Document", "Receipt for", "receipt for", "has receipt"),
    rt("manual_for", "document", "asset", "Document", "Manual for", "manual for", "has manual"),
    rt("document_references_asset", "document", "asset", "Document", "References", "references", "referenced by"),
    rt("document_asset_other", "document", "asset", "Document", "Other", "relates to", "related document", directional=False),
    rt("document_belongs_to_project", "document", "project", "Document", "Belongs to", "belongs to", "has document"),
    rt("document_created_for_project", "document", "project", "Document", "Created for", "created for", "has created document"),
    rt("references", "document", "project", "Document", "References", "references", "referenced by"),
    rt("document_project_other", "document", "project", "Document", "Other", "relates to", "related document", directional=False),
    rt("located_at", "entity", "location", "Location", "Located at", "located at", "location of", notes="Legacy location relationship. Existing records still load and map; new records use pair-specific location types.", selectable=False),
    rt("related_to", "entity", "entity", "Legacy / Other", "Related to", "related to", "related to", directional=False, notes="Legacy fallback. Preserved for existing relationships, not offered for specific supported pairs.", selectable=False),
    rt("associated_with", "entity", "entity", "Legacy / Other", "Associated with", "associated with", "associated with", directional=False, notes="Legacy fallback. Preserved for existing relationships, not offered for specific supported pairs.", selectable=False),
    rt("mother_of", "person", "person", "Legacy / Family", "Mother", "mother of", "child of", notes="Legacy gendered type; use Parent / child for new records.", selectable=False),
    rt("father_of", "person", "person", "Legacy / Family", "Father", "father of", "child of", notes="Legacy gendered type; use Parent / child for new records.", selectable=False),
    rt("child_of", "person", "person", "Legacy / Family", "Child", "child of", "parent of", notes="Legacy directional type; use Parent / child for new records.", selectable=False),
)



ROLE_LABELS_BY_KEY: dict[str, tuple[str, str]] = {
    "works_for": ("Employee", "Employer"),
    "manager_at": ("Manager", "Managed by"),
    "director_of": ("Director", "Directed by"),
    "member_of": ("Member", "Has member"),
    "volunteer_for": ("Volunteer", "Has volunteer"),
    "student_at": ("Student", "Educational institution"),
    "patient_client_of": ("Patient / client", "Provider"),
    "customer_of": ("Customer", "Provider"),
    "owner_of": ("Owner", "Owned by"),
    "lives_at": ("Resident", "Residence"),
    "works_at_location": ("Worker", "Workplace"),
    "visited_location": ("Visitor", "Visited place"),
    "born_at": ("Person born there", "Birthplace"),
    "person_located_at": ("Located entity", "Location"),
    "project_involves_person": ("Project", "Involved person"),
    "project_managed_by": ("Managed project", "Manager"),
    "project_owned_by": ("Owned project", "Owner"),
    "project_contributor": ("Contributor", "Project"),
    "located_at_org": ("Located organisation", "Location"),
    "headquartered_at": ("Headquartered organisation", "Headquarters"),
    "branch_at": ("Branch", "Branch location"),
    "operates_at": ("Operator", "Operating location"),
    "project_involves_organisation": ("Project", "Involved organisation"),
    "project_sponsored_by": ("Sponsored project", "Sponsor"),
    "project_owned_by_organisation": ("Owned project", "Owner"),
    "stored_at": ("Stored asset", "Storage location"),
    "asset_located_at": ("Located asset", "Location"),
    "last_known_at": ("Asset", "Last known location"),
    "document_belongs_to_person": ("Document", "Document holder"),
    "document_created_by_person": ("Document", "Creator"),
    "document_issued_to_person": ("Issued document", "Document holder"),
    "document_references_person": ("Document", "Referenced person"),
    "document_belongs_to_organisation": ("Document", "Document holder"),
    "document_created_by_organisation": ("Document", "Creator"),
    "document_issued_by_organisation": ("Document", "Issuer"),
    "document_references_organisation": ("Document", "Referenced organisation"),
    "document_belongs_to_asset": ("Document", "Documented asset"),
    "receipt_for": ("Receipt", "Purchased asset"),
    "manual_for": ("Manual", "Documented asset"),
    "document_references_asset": ("Document", "Referenced asset"),
    "document_belongs_to_project": ("Document", "Project"),
    "document_created_for_project": ("Document", "Project"),
    "references": ("Document", "Referenced project"),
}


def relationship_choices_for_context(
    context_type: str,
    connected_type: str,
    connected_sex: str = "",
) -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = []
    for relationship_type in relationship_types_for_pair(context_type, connected_type):
        if relationship_type.source_type == relationship_type.target_type == connected_type == context_type:
            choices.extend(same_type_choices(relationship_type, connected_sex))
            continue
        if relationship_type._matches(connected_type, context_type):
            choices.append((relationship_choice_value(relationship_type, "source"), role_label(relationship_type, "source", connected_sex)))
        if relationship_type._matches(context_type, connected_type):
            choices.append((relationship_choice_value(relationship_type, "target"), role_label(relationship_type, "target", connected_sex)))
    return choices


def same_type_choices(relationship_type: RelationshipType, connected_sex: str) -> list[tuple[str, str]]:
    if not relationship_type.directional:
        return [(relationship_choice_value(relationship_type, "source"), role_label(relationship_type, "source", connected_sex))]
    return [
        (relationship_choice_value(relationship_type, "source"), role_label(relationship_type, "source", connected_sex)),
        (relationship_choice_value(relationship_type, "target"), role_label(relationship_type, "target", connected_sex)),
    ]


def relationship_choice_value(relationship_type: RelationshipType, connected_role: str) -> str:
    return f"{relationship_type.key}::{connected_role}"


def split_relationship_choice(value: str) -> tuple[str, str]:
    if "::" not in value:
        return value, ""
    key, connected_role = value.split("::", 1)
    return key, connected_role


def role_label(relationship_type: RelationshipType, connected_role: str, sex: str = "") -> str:
    if relationship_type.key == "parent_child":
        if connected_role == "source":
            return sex_label(sex, "Parent", "Father", "Mother")
        return sex_label(sex, "Child", "Son", "Daughter")
    if relationship_type.key == "sibling_of":
        return sex_label(sex, "Sibling", "Brother", "Sister")
    if relationship_type.key == "grandparent_child":
        if connected_role == "source":
            return sex_label(sex, "Grandparent", "Grandfather", "Grandmother")
        return sex_label(sex, "Grandchild", "Grandson", "Granddaughter")
    if relationship_type.key == "aunt_uncle_niece_nephew":
        if connected_role == "source":
            return sex_label(sex, "Aunt/uncle", "Uncle", "Aunt")
        return sex_label(sex, "Niece/nephew", "Nephew", "Niece")
    labels = ROLE_LABELS_BY_KEY.get(relationship_type.key)
    if labels:
        return labels[0] if connected_role == "source" else labels[1]
    return relationship_type.subtype or relationship_type.label

RELATIONSHIP_TYPES_BY_KEY = {relationship_type.key: relationship_type for relationship_type in RELATIONSHIP_TYPES}
RELATIONSHIP_STATUSES = ("active", "former", "unknown")
DATE_PRECISIONS = ("exact", "approximate", "unknown")


def entity_type_label(entity_type: str) -> str:
    definition = DEFINITIONS_BY_TYPE.get(entity_type)
    return definition.plural if definition else entity_type.title()


def relationship_types_for_pair(source_type: str, target_type: str) -> tuple[RelationshipType, ...]:
    return tuple(
        relationship_type
        for relationship_type in RELATIONSHIP_TYPES
        if relationship_type.selectable and relationship_type.supports_pair(source_type, target_type)
    )


def relationship_type_is_valid_for_pair(type_key: str, source_type: str, target_type: str) -> bool:
    relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(type_key)
    return (
        relationship_type is not None
        and relationship_type.selectable
        and relationship_type.supports_pair(source_type, target_type)
    )


def relationship_label_for_entity(
    relationship_type: RelationshipType,
    source: EntityRecord,
    target: EntityRecord,
    from_source: bool,
) -> str:
    if relationship_type.key == "parent_child":
        return gendered_label(source if from_source else target, "parent of", "father of", "mother of") if from_source else gendered_label(target, "child of", "son of", "daughter of")
    if relationship_type.key == "sibling_of":
        viewer = source if from_source else target
        return gendered_label(viewer, "sibling of", "brother of", "sister of")
    if relationship_type.key == "grandparent_child":
        if from_source:
            return gendered_label(source, "grandparent of", "grandfather of", "grandmother of")
        return gendered_label(target, "grandchild of", "grandson of", "granddaughter of")
    if relationship_type.key == "aunt_uncle_niece_nephew":
        if from_source:
            return gendered_label(source, "aunt/uncle of", "uncle of", "aunt of")
        return gendered_label(target, "niece/nephew of", "nephew of", "niece of")
    return relationship_type.label if from_source else relationship_type.inverse_label


def gendered_label(record: EntityRecord, neutral: str, male: str, female: str) -> str:
    return sex_label(record.metadata.get("sex", ""), neutral, male, female)


def sex_label(value: str, neutral: str, male: str, female: str) -> str:
    sex = value.strip().lower()
    if sex == "male":
        return male
    if sex == "female":
        return female
    return neutral
