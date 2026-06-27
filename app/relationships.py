from dataclasses import dataclass

from app.entities import DEFINITIONS_BY_TYPE, EntityRecord
from app.relationship_catalog import (
    RELATIONSHIP_TYPES,
    RELATIONSHIP_TYPES_BY_KEY,
    RelationshipType,
    rt,
)


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
    return relationship_type.role_label(connected_role, sex)


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
    record = source if from_source else target
    role = "source" if from_source else "target"
    return relationship_type.label_for_role(role, record.metadata.get("sex", ""))


def gendered_label(record: EntityRecord, neutral: str, male: str, female: str) -> str:
    return sex_label(record.metadata.get("sex", ""), neutral, male, female)


def sex_label(value: str, neutral: str, male: str, female: str) -> str:
    sex = value.strip().lower()
    if sex == "male":
        return male
    if sex == "female":
        return female
    return neutral
