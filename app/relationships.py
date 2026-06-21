from dataclasses import dataclass

from app.entities import DEFINITIONS_BY_TYPE, EntityRecord


@dataclass(frozen=True)
class RelationshipType:
    key: str
    label: str
    inverse_label: str
    directional: bool = True


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
            RelationshipType(self.type_key, self.type_key.replace("_", " "), self.type_key.replace("_", " ")),
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


RELATIONSHIP_TYPES: tuple[RelationshipType, ...] = (
    RelationshipType("associated_with", "associated with", "associated with", directional=False),
    RelationshipType("knows", "knows", "knows", directional=False),
    RelationshipType("works_for", "works for", "has worker"),
    RelationshipType("located_at", "located at", "has location"),
    RelationshipType("member_of", "member of", "has member"),
    RelationshipType("belongs_to", "belongs to", "has item"),
    RelationshipType("references", "references", "referenced by"),
    RelationshipType("related_to", "related to", "related to", directional=False),
)

RELATIONSHIP_TYPES_BY_KEY = {relationship_type.key: relationship_type for relationship_type in RELATIONSHIP_TYPES}
RELATIONSHIP_STATUSES = ("active", "former", "unknown")
DATE_PRECISIONS = ("exact", "approximate", "unknown")


def entity_type_label(entity_type: str) -> str:
    definition = DEFINITIONS_BY_TYPE.get(entity_type)
    return definition.plural if definition else entity_type.title()
