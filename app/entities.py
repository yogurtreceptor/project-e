from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: str
    multiline: bool = False
    overview: bool = True
    input_type: str = "text"


@dataclass(frozen=True)
class EntityDefinition:
    type: str
    slug: str
    singular: str
    plural: str
    table: str
    fields: tuple[FieldDefinition, ...]

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)


@dataclass(frozen=True)
class EntityRecord:
    id: int
    definition: EntityDefinition
    display_name: str
    summary: str
    notes: str
    created_at: str
    updated_at: str
    last_viewed_at: str
    is_favourite: bool
    metadata: dict[str, str]

    @property
    def type(self) -> str:
        return self.definition.type

    @property
    def slug(self) -> str:
        return self.definition.slug

    @property
    def title(self) -> str:
        return self.display_name

    def field_value(self, field: FieldDefinition) -> str:
        return self.metadata.get(field.name, "")

    def field_items(self) -> list[tuple[FieldDefinition, str]]:
        return [(field, self.field_value(field)) for field in self.definition.fields]

    def to_form_values(self) -> dict[str, str]:
        values = {
            "display_name": self.display_name,
            "summary": self.summary,
            "notes": self.notes,
        }
        values.update(self.metadata)
        return values


ENTITY_DEFINITIONS: tuple[EntityDefinition, ...] = (
    EntityDefinition(
        type="person",
        slug="people",
        singular="Person",
        plural="People",
        table="people",
        fields=(
            FieldDefinition("given_name", "Given name"),
            FieldDefinition("family_name", "Family name"),
            FieldDefinition("birthday", "Birthday", input_type="date"),
            FieldDefinition("occupation", "Occupation"),
            FieldDefinition("email", "Email"),
            FieldDefinition("phone", "Phone"),
        ),
    ),
    EntityDefinition(
        type="organisation",
        slug="organisations",
        singular="Organisation",
        plural="Organisations",
        table="organisations",
        fields=(
            FieldDefinition("organisation_type", "Organisation type"),
            FieldDefinition("address_line_1", "Address line 1"),
            FieldDefinition("locality", "Locality"),
            FieldDefinition("region", "Region"),
            FieldDefinition("country", "Country"),
            FieldDefinition("website", "Website"),
            FieldDefinition("email", "Email"),
            FieldDefinition("phone", "Phone"),
        ),
    ),
    EntityDefinition(
        type="location",
        slug="locations",
        singular="Location",
        plural="Locations",
        table="locations",
        fields=(
            FieldDefinition("address_line_1", "Address line 1"),
            FieldDefinition("address_line_2", "Address line 2"),
            FieldDefinition("locality", "Locality"),
            FieldDefinition("region", "Region"),
            FieldDefinition("country", "Country"),
            FieldDefinition("latitude", "Latitude"),
            FieldDefinition("longitude", "Longitude"),
        ),
    ),
)


DEFINITIONS_BY_SLUG = {definition.slug: definition for definition in ENTITY_DEFINITIONS}
DEFINITIONS_BY_TYPE = {definition.type: definition for definition in ENTITY_DEFINITIONS}


def to_entity_record(definition: EntityDefinition, row: Any) -> EntityRecord:
    return EntityRecord(
        id=int(row["id"]),
        definition=definition,
        display_name=row["display_name"],
        summary=row["summary"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_viewed_at=row["last_viewed_at"],
        is_favourite=bool(row["is_favourite"]),
        metadata={field.name: row[field.name] for field in definition.fields},
    )
