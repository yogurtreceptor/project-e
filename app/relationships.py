from dataclasses import dataclass

from app.entities import DEFINITIONS_BY_TYPE, EntityRecord


@dataclass(frozen=True)
class RelationshipType:
    key: str
    label: str
    inverse_label: str
    category: str
    subtype: str = ""
    pairs: tuple[tuple[str, str], ...] = ()
    option_label: str = ""
    directional: bool = True

    @property
    def display_label(self) -> str:
        return self.option_label or self.subtype or self.label

    def supports_pair(self, source_type: str, target_type: str) -> bool:
        if not self.pairs:
            return True
        return (source_type, target_type) in self.pairs or (target_type, source_type) in self.pairs


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
            RelationshipType(self.type_key, self.type_key.replace("_", " "), self.type_key.replace("_", " "), "Other"),
        )

    @property
    def label(self) -> str:
        return self.type.label

    def label_from(self, entity_id: int) -> str:
        if entity_id == self.source.id:
            return self.type.label
        if entity_id == self.target.id:
            return self.type.inverse_label
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


PERSON_PERSON = (("person", "person"),)
PERSON_ORGANISATION = (("person", "organisation"),)
PERSON_LOCATION = (("person", "location"),)
ORGANISATION_LOCATION = (("organisation", "location"),)
ASSET_LOCATION = (("asset", "location"),)
DOCUMENT_LINKS = (
    ("document", "person"),
    ("document", "organisation"),
    ("document", "asset"),
    ("document", "project"),
)


RELATIONSHIP_TYPES: tuple[RelationshipType, ...] = (
    RelationshipType("family", "family of", "family of", "Family", "Other", PERSON_PERSON, "Family", directional=False),
    RelationshipType("mother_of", "mother of", "child of", "Family", "Mother", PERSON_PERSON),
    RelationshipType("father_of", "father of", "child of", "Family", "Father", PERSON_PERSON),
    RelationshipType("child_of", "child of", "parent of", "Family", "Child", PERSON_PERSON),
    RelationshipType("sibling_of", "sibling of", "sibling of", "Family", "Sibling", PERSON_PERSON, directional=False),
    RelationshipType("partner_of", "partner of", "partner of", "Family", "Partner", PERSON_PERSON, directional=False),
    RelationshipType("spouse_of", "spouse of", "spouse of", "Family", "Spouse", PERSON_PERSON, directional=False),
    RelationshipType("coworker_of", "coworker of", "coworker of", "Work", "Coworker", PERSON_PERSON, directional=False),
    RelationshipType("boss_of", "boss of", "reports to", "Work", "Boss", PERSON_PERSON),
    RelationshipType("team_member_of", "team member of", "team member of", "Work", "Team member", PERSON_PERSON, directional=False),
    RelationshipType("student_of", "student of", "teacher of", "Education", "Student", PERSON_PERSON),
    RelationshipType("teacher_of", "teacher of", "student of", "Education", "Teacher", PERSON_PERSON),
    RelationshipType("classmate_of", "classmate of", "classmate of", "Education", "Classmate", PERSON_PERSON, directional=False),
    RelationshipType("doctor_of", "doctor of", "patient of", "Health", "Doctor", PERSON_PERSON),
    RelationshipType("nurse_of", "nurse of", "patient of", "Health", "Nurse", PERSON_PERSON),
    RelationshipType("psychologist_of", "psychologist of", "patient of", "Health", "Psychologist", PERSON_PERSON),
    RelationshipType("specialist_of", "specialist of", "patient of", "Health", "Specialist", PERSON_PERSON),
    RelationshipType("friend_of", "friend of", "friend of", "Friend / social", "Friend / social", PERSON_PERSON, directional=False),
    RelationshipType("knows", "knows", "knows", "Friend / social", "Other", PERSON_PERSON, "Other", directional=False),
    RelationshipType("works_for", "works for", "has worker", "Work", "Employee", PERSON_ORGANISATION, "Employee"),
    RelationshipType("manager_at", "manager at", "has manager", "Work", "Manager", PERSON_ORGANISATION),
    RelationshipType("director_of", "director of", "has director", "Work", "Director", PERSON_ORGANISATION),
    RelationshipType("member_of", "member of", "has member", "Membership", "Member", PERSON_ORGANISATION),
    RelationshipType("volunteer_for", "volunteer for", "has volunteer", "Volunteer", "Volunteer", PERSON_ORGANISATION),
    RelationshipType("patient_client_of", "patient / client of", "has patient / client", "Service", "Patient / client", PERSON_ORGANISATION),
    RelationshipType("student_at", "student at", "has student", "Education", "Student", PERSON_ORGANISATION),
    RelationshipType("customer_of", "customer of", "has customer", "Commercial", "Customer", PERSON_ORGANISATION),
    RelationshipType("owner_of", "owner of", "owned by", "Ownership", "Owner", PERSON_ORGANISATION),
    RelationshipType("person_organisation_other", "associated with", "associated with", "Other", "Other", PERSON_ORGANISATION, "Other", directional=False),
    RelationshipType("located_at", "located at", "has location", "Location", "Located at", PERSON_LOCATION + ORGANISATION_LOCATION + ASSET_LOCATION),
    RelationshipType("headquartered_at", "headquartered at", "headquarters for", "Location", "Headquartered at", ORGANISATION_LOCATION),
    RelationshipType("branch_at", "branch at", "has branch", "Location", "Branch at", ORGANISATION_LOCATION),
    RelationshipType("operates_at", "operates at", "operating location for", "Location", "Operates at", ORGANISATION_LOCATION),
    RelationshipType("stored_at", "stored at", "stores", "Location", "Stored at", ASSET_LOCATION),
    RelationshipType("last_known_at", "last known at", "last known location for", "Location", "Last known at", ASSET_LOCATION),
    RelationshipType("location_other", "associated with", "associated with", "Other", "Other", ORGANISATION_LOCATION + ASSET_LOCATION, "Other", directional=False),
    RelationshipType("belongs_to", "belongs to", "has document", "Document", "Belongs to", DOCUMENT_LINKS),
    RelationshipType("issued_by", "issued by", "issued", "Document", "Issued by", DOCUMENT_LINKS),
    RelationshipType("created_by", "created by", "created", "Document", "Created by", DOCUMENT_LINKS),
    RelationshipType("references", "references", "referenced by", "Document", "References", DOCUMENT_LINKS),
    RelationshipType("receipt_for", "receipt for", "has receipt", "Document", "Receipt for", DOCUMENT_LINKS),
    RelationshipType("manual_for", "manual for", "has manual", "Document", "Manual for", DOCUMENT_LINKS),
    RelationshipType("document_other", "relates to", "relates to", "Document", "Other", DOCUMENT_LINKS, "Other", directional=False),
    RelationshipType("related_to", "related to", "related to", "Other", "Other", directional=False),
    RelationshipType("associated_with", "associated with", "associated with", "Other", "Other", directional=False),
)

RELATIONSHIP_TYPES_BY_KEY = {relationship_type.key: relationship_type for relationship_type in RELATIONSHIP_TYPES}
RELATIONSHIP_STATUSES = ("active", "former", "unknown")
DATE_PRECISIONS = ("exact", "approximate", "unknown")


def entity_type_label(entity_type: str) -> str:
    definition = DEFINITIONS_BY_TYPE.get(entity_type)
    return definition.plural if definition else entity_type.title()


def relationship_types_for_pair(source_type: str, target_type: str) -> tuple[RelationshipType, ...]:
    specific = tuple(
        relationship_type
        for relationship_type in RELATIONSHIP_TYPES
        if relationship_type.pairs and relationship_type.supports_pair(source_type, target_type)
    )
    if specific:
        return specific
    return tuple(
        relationship_type
        for relationship_type in RELATIONSHIP_TYPES
        if not relationship_type.pairs
    )


def relationship_type_is_valid_for_pair(type_key: str, source_type: str, target_type: str) -> bool:
    return any(
        relationship_type.key == type_key
        for relationship_type in relationship_types_for_pair(source_type, target_type)
    )
