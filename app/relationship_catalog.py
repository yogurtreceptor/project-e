from dataclasses import dataclass


@dataclass(frozen=True)
class LabelSet:
    neutral: str
    male: str = ""
    female: str = ""

    def resolve(self, sex: str = "") -> str:
        normalised = sex.strip().lower()
        if normalised == "male" and self.male:
            return self.male
        if normalised == "female" and self.female:
            return self.female
        return self.neutral


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
    role_labels: tuple[LabelSet, LabelSet] | None = None
    display_labels: tuple[LabelSet, LabelSet] | None = None

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

    def role_label(self, role: str, sex: str = "") -> str:
        if self.role_labels:
            return self.role_labels[0 if role == "source" else 1].resolve(sex)
        return self.subtype or self.label

    def label_for_role(self, role: str, sex: str = "") -> str:
        if self.display_labels:
            return self.display_labels[0 if role == "source" else 1].resolve(sex)
        return self.label if role == "source" else self.inverse_label

    def _matches(self, source_type: str, target_type: str) -> bool:
        return (self.source_type in {source_type, "entity"}) and (self.target_type in {target_type, "entity"})


LabelSpec = str | tuple[str, str, str]


def label_set(value: LabelSpec) -> LabelSet:
    if isinstance(value, str):
        return LabelSet(value)
    return LabelSet(*value)


def label_pair(values: tuple[LabelSpec, LabelSpec] | None) -> tuple[LabelSet, LabelSet] | None:
    if values is None:
        return None
    return label_set(values[0]), label_set(values[1])


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
    roles: tuple[LabelSpec, LabelSpec] | None = None,
    labels: tuple[LabelSpec, LabelSpec] | None = None,
) -> RelationshipType:
    return RelationshipType(
        key, source_type, target_type, category, subtype, label, inverse_label,
        directional=directional, notes=notes, selectable=selectable,
        role_labels=label_pair(roles), display_labels=label_pair(labels),
    )


PERSON_PERSON_TYPES: tuple[RelationshipType, ...] = (
    rt("parent_child", "person", "person", "Family", "Parent / child", "parent of", "child of", notes="Neutral family-tree-ready parent to child relationship.", roles=(('Parent', 'Father', 'Mother'), ('Child', 'Son', 'Daughter')), labels=(('parent of', 'father of', 'mother of'), ('child of', 'son of', 'daughter of'))),
    rt("sibling_of", "person", "person", "Family", "Sibling", "sibling of", "sibling of", directional=False, roles=(('Sibling', 'Brother', 'Sister'), ('Sibling', 'Brother', 'Sister')), labels=(('sibling of', 'brother of', 'sister of'), ('sibling of', 'brother of', 'sister of'))),
    rt("spouse_of", "person", "person", "Family", "Spouse", "spouse of", "spouse of", directional=False),
    rt("partner_of", "person", "person", "Family", "Partner", "partner of", "partner of", directional=False),
    rt("grandparent_child", "person", "person", "Family", "Grandparent / grandchild", "grandparent of", "grandchild of", roles=(('Grandparent', 'Grandfather', 'Grandmother'), ('Grandchild', 'Grandson', 'Granddaughter')), labels=(('grandparent of', 'grandfather of', 'grandmother of'), ('grandchild of', 'grandson of', 'granddaughter of'))),
    rt("aunt_uncle_niece_nephew", "person", "person", "Family", "Aunt/uncle / niece/nephew", "aunt/uncle of", "niece/nephew of", roles=(('Aunt/uncle', 'Uncle', 'Aunt'), ('Niece/nephew', 'Nephew', 'Niece')), labels=(('aunt/uncle of', 'uncle of', 'aunt of'), ('niece/nephew of', 'nephew of', 'niece of'))),
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
)


PERSON_ORGANISATION_TYPES: tuple[RelationshipType, ...] = (
    rt("works_for", "person", "organisation", "Role", "Employee / employer", "employee of", "employer of", roles=('Employee', 'Employer')),
    rt("manager_at", "person", "organisation", "Role", "Manager", "manager at", "managed by", roles=('Manager', 'Managed by')),
    rt("director_of", "person", "organisation", "Role", "Director", "director of", "directed by", roles=('Director', 'Directed by')),
    rt("member_of", "person", "organisation", "Membership", "Member", "member of", "has member", roles=('Member', 'Has member')),
    rt("volunteer_for", "person", "organisation", "Role", "Volunteer", "volunteer for", "has volunteer", roles=('Volunteer', 'Has volunteer')),
    rt("student_at", "person", "organisation", "Education", "Student", "student at", "educational institution for", roles=('Student', 'Educational institution')),
    rt("patient_client_of", "person", "organisation", "Service", "Patient / client", "patient/client of", "provider for", roles=('Patient / client', 'Provider')),
    rt("customer_of", "person", "organisation", "Service", "Customer", "customer of", "provider for", roles=('Customer', 'Provider')),
    rt("owner_of", "person", "organisation", "Ownership", "Owner", "owner of", "owned by", roles=('Owner', 'Owned by')),
    rt("person_organisation_other", "person", "organisation", "Other", "Other", "associated with", "associated with", directional=False),
)


PERSON_LOCATION_TYPES: tuple[RelationshipType, ...] = (
    rt("lives_at", "person", "location", "Location", "Lives at", "lives at", "residence of", roles=('Resident', 'Residence')),
    rt("works_at_location", "person", "location", "Location", "Works at", "works at", "workplace of", roles=('Worker', 'Workplace')),
    rt("visited_location", "person", "location", "Location", "Visited", "visited", "visited by", roles=('Visitor', 'Visited place')),
    rt("born_at", "person", "location", "Location", "Born at", "born at", "birthplace of", roles=('Person born there', 'Birthplace')),
    rt("person_located_at", "person", "location", "Location", "Located at", "located at", "location of", roles=('Located entity', 'Location')),
    rt("person_location_other", "person", "location", "Other", "Other", "associated with", "associated with", directional=False),
)


PERSON_PROJECT_TYPES: tuple[RelationshipType, ...] = (
    rt("project_involves_person", "project", "person", "Project", "Involves", "involves", "involved in", roles=('Project', 'Involved person')),
    rt("project_managed_by", "project", "person", "Project", "Managed by", "managed by", "manages", roles=('Managed project', 'Manager')),
    rt("project_owned_by", "project", "person", "Project", "Owner", "owned by", "owns project", roles=('Owned project', 'Owner')),
    rt("project_contributor", "person", "project", "Project", "Contributor", "contributes to", "has contributor", roles=('Contributor', 'Project')),
    rt("person_project_other", "person", "project", "Other", "Other", "associated with", "associated with", directional=False),
)


ORGANISATION_LOCATION_TYPES: tuple[RelationshipType, ...] = (
    rt("located_at_org", "organisation", "location", "Location", "Located at", "located at", "location of", roles=('Located organisation', 'Location')),
    rt("headquartered_at", "organisation", "location", "Location", "Headquartered at", "headquartered at", "headquarters of", roles=('Headquartered organisation', 'Headquarters')),
    rt("branch_at", "organisation", "location", "Location", "Branch at", "branch at", "branch location for", roles=('Branch', 'Branch location')),
    rt("operates_at", "organisation", "location", "Location", "Operates at", "operates at", "operating location for", roles=('Operator', 'Operating location')),
    rt("organisation_location_other", "organisation", "location", "Other", "Other", "associated with", "associated with", directional=False),
)


ORGANISATION_PROJECT_TYPES: tuple[RelationshipType, ...] = (
    rt("project_involves_organisation", "project", "organisation", "Project", "Involves", "involves", "involved in", roles=('Project', 'Involved organisation')),
    rt("project_sponsored_by", "project", "organisation", "Project", "Sponsored by", "sponsored by", "sponsors", roles=('Sponsored project', 'Sponsor')),
    rt("project_owned_by_organisation", "project", "organisation", "Project", "Owner", "owned by", "owns project", roles=('Owned project', 'Owner')),
    rt("organisation_project_other", "organisation", "project", "Other", "Other", "associated with", "associated with", directional=False),
)


ASSET_LOCATION_TYPES: tuple[RelationshipType, ...] = (
    rt("stored_at", "asset", "location", "Location", "Stored at", "stored at", "stores", roles=('Stored asset', 'Storage location')),
    rt("asset_located_at", "asset", "location", "Location", "Located at", "located at", "location of", roles=('Located asset', 'Location')),
    rt("last_known_at", "asset", "location", "Location", "Last known at", "last known at", "last known location for", roles=('Asset', 'Last known location')),
    rt("asset_location_other", "asset", "location", "Other", "Other", "associated with", "associated with", directional=False),
)


DOCUMENT_PERSON_TYPES: tuple[RelationshipType, ...] = (
    rt("document_belongs_to_person", "document", "person", "Document", "Belongs to", "belongs to", "has document", roles=('Document', 'Document holder')),
    rt("document_created_by_person", "document", "person", "Document", "Created by", "created by", "created", roles=('Document', 'Creator')),
    rt("document_issued_to_person", "document", "person", "Document", "Issued to", "issued to", "holds issued document", roles=('Issued document', 'Document holder')),
    rt("document_references_person", "document", "person", "Document", "References", "references", "referenced by", roles=('Document', 'Referenced person')),
    rt("document_person_other", "document", "person", "Document", "Other", "relates to", "related document", directional=False),
)


DOCUMENT_ORGANISATION_TYPES: tuple[RelationshipType, ...] = (
    rt("document_belongs_to_organisation", "document", "organisation", "Document", "Belongs to", "belongs to", "has document", roles=('Document', 'Document holder')),
    rt("document_created_by_organisation", "document", "organisation", "Document", "Created by", "created by", "created", roles=('Document', 'Creator')),
    rt("document_issued_by_organisation", "document", "organisation", "Document", "Issued by", "issued by", "issued", roles=('Document', 'Issuer')),
    rt("document_references_organisation", "document", "organisation", "Document", "References", "references", "referenced by", roles=('Document', 'Referenced organisation')),
    rt("document_organisation_other", "document", "organisation", "Document", "Other", "relates to", "related document", directional=False),
)


DOCUMENT_ASSET_TYPES: tuple[RelationshipType, ...] = (
    rt("document_belongs_to_asset", "document", "asset", "Document", "Belongs to", "belongs to", "has document", roles=('Document', 'Documented asset')),
    rt("receipt_for", "document", "asset", "Document", "Receipt for", "receipt for", "has receipt", roles=('Receipt', 'Purchased asset')),
    rt("manual_for", "document", "asset", "Document", "Manual for", "manual for", "has manual", roles=('Manual', 'Documented asset')),
    rt("document_references_asset", "document", "asset", "Document", "References", "references", "referenced by", roles=('Document', 'Referenced asset')),
    rt("document_asset_other", "document", "asset", "Document", "Other", "relates to", "related document", directional=False),
)


DOCUMENT_PROJECT_TYPES: tuple[RelationshipType, ...] = (
    rt("document_belongs_to_project", "document", "project", "Document", "Belongs to", "belongs to", "has document", roles=('Document', 'Project')),
    rt("document_created_for_project", "document", "project", "Document", "Created for", "created for", "has created document", roles=('Document', 'Project')),
    rt("references", "document", "project", "Document", "References", "references", "referenced by", roles=('Document', 'Referenced project')),
    rt("document_project_other", "document", "project", "Document", "Other", "relates to", "related document", directional=False),
)


LEGACY_TYPES: tuple[RelationshipType, ...] = (
    rt("located_at", "entity", "location", "Location", "Located at", "located at", "location of", notes="Legacy location relationship. Existing records still load and map; new records use pair-specific location types.", selectable=False),
    rt("related_to", "entity", "entity", "Legacy / Other", "Related to", "related to", "related to", directional=False, notes="Legacy fallback. Preserved for existing relationships, not offered for specific supported pairs.", selectable=False),
    rt("associated_with", "entity", "entity", "Legacy / Other", "Associated with", "associated with", "associated with", directional=False, notes="Legacy fallback. Preserved for existing relationships, not offered for specific supported pairs.", selectable=False),
    rt("mother_of", "person", "person", "Legacy / Family", "Mother", "mother of", "child of", notes="Legacy gendered type; use Parent / child for new records.", selectable=False),
    rt("father_of", "person", "person", "Legacy / Family", "Father", "father of", "child of", notes="Legacy gendered type; use Parent / child for new records.", selectable=False),
    rt("child_of", "person", "person", "Legacy / Family", "Child", "child of", "parent of", notes="Legacy directional type; use Parent / child for new records.", selectable=False),
)


RELATIONSHIP_TYPE_GROUPS: tuple[tuple[RelationshipType, ...], ...] = (
    PERSON_PERSON_TYPES,
    PERSON_ORGANISATION_TYPES,
    PERSON_LOCATION_TYPES,
    PERSON_PROJECT_TYPES,
    ORGANISATION_LOCATION_TYPES,
    ORGANISATION_PROJECT_TYPES,
    ASSET_LOCATION_TYPES,
    DOCUMENT_PERSON_TYPES,
    DOCUMENT_ORGANISATION_TYPES,
    DOCUMENT_ASSET_TYPES,
    DOCUMENT_PROJECT_TYPES,
    LEGACY_TYPES,
)

RELATIONSHIP_TYPES = tuple(
    relationship_type
    for group in RELATIONSHIP_TYPE_GROUPS
    for relationship_type in group
)

RELATIONSHIP_TYPES_BY_KEY = {item.key: item for item in RELATIONSHIP_TYPES}
if len(RELATIONSHIP_TYPES_BY_KEY) != len(RELATIONSHIP_TYPES):
    raise ValueError("Relationship type keys must be unique.")
