from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDefinition:
    name: str
    label: str
    multiline: bool = False
    overview: bool = True
    input_type: str = "text"
    value_kind: str = ""
    editable: bool = True
    options: tuple[str, ...] = ()
    allow_custom: bool = False
    previous_names: tuple[str, ...] = ()
    display_prefix: str = ""
    default: str = ""
    value_aliases: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class EntityDefinition:
    type: str
    slug: str
    singular: str
    plural: str
    table: str
    fields: tuple[FieldDefinition, ...]
    duplicate_fields: tuple[str, ...] = ()

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

    def display_field_value(self, field: FieldDefinition) -> str:
        value = self.field_value(field)
        if value and field.display_prefix:
            return f"{field.display_prefix}{value}"
        return value

    def field_items(self) -> list[tuple[FieldDefinition, str]]:
        return [(field, self.field_value(field)) for field in self.definition.fields]

    def to_form_values(self) -> dict[str, str]:
        values = {
            "display_name": self.display_name,
            "notes": self.notes,
        }
        values.update(self.metadata)
        return values


ORGANISATION_TYPES = (
    "Business",
    "Government agency",
    "School",
    "University",
    "Medical practice",
    "Employer",
    "Bank",
    "Utility",
    "Club",
    "Charity",
    "Political party",
    "Other",
)

PROJECT_TYPES = (
    "Personal",
    "Work",
    "Education",
    "Health",
    "Finance",
    "Home",
    "Vehicle",
    "Travel",
    "Civic",
    "Other",
)

PROJECT_STATUSES = ("Active", "Paused", "Completed", "Abandoned")

DOCUMENT_TYPES = (
    "Identification",
    "Certificate",
    "Contract",
    "Receipt",
    "Invoice",
    "Manual",
    "Medical",
    "Government",
    "Letter",
    "Image",
    "PDF",
    "Other",
)

ASSET_TYPES = (
    "Vehicle",
    "Appliance",
    "Tool",
    "Electronic device",
    "Computer",
    "Phone",
    "Document-like asset",
    "Smart device",
    "Furniture",
    "Other",
)

ASSET_STATUSES = (
    "Owned",
    "Sold",
    "Lost",
    "Destroyed",
    "In disrepair",
    "Loaned out",
    "Other",
)

SEX_OPTIONS = (
    "Male",
    "Female",
    "Other",
    "Unknown",
)


ENTITY_DEFINITIONS: tuple[EntityDefinition, ...] = (
    EntityDefinition(
        type="person",
        slug="people",
        singular="Person",
        plural="People",
        table="people",
        fields=(
            FieldDefinition("title", "Title"),
            FieldDefinition("given_name", "Given name"),
            FieldDefinition("middle_name", "Middle name"),
            FieldDefinition("family_name", "Family name"),
            FieldDefinition(
                "sex",
                "Sex",
                options=SEX_OPTIONS,
                default="Unknown",
                previous_names=("gender_sex",),
                value_aliases=(
                    ("male", "Male"),
                    ("female", "Female"),
                    ("Non-binary", "Other"),
                    ("Prefer not to say", "Unknown"),
                    ("", "Unknown"),
                ),
            ),
            FieldDefinition("birthday", "Birthday", input_type="date", value_kind="date"),
            FieldDefinition("email", "Email"),
            FieldDefinition("phone", "Phone"),
        ),
        duplicate_fields=("email", "phone"),
    ),
    EntityDefinition(
        type="organisation",
        slug="organisations",
        singular="Organisation",
        plural="Organisations",
        table="organisations",
        fields=(
            FieldDefinition("organisation_type", "Organisation type", options=ORGANISATION_TYPES, allow_custom=True),
            FieldDefinition("website", "Website"),
            FieldDefinition("phone", "Phone"),
            FieldDefinition("email", "Email"),
        ),
        duplicate_fields=("website", "email", "phone"),
    ),
    EntityDefinition(
        type="location",
        slug="locations",
        singular="Location",
        plural="Locations",
        table="locations",
        fields=(
            FieldDefinition("formatted_address", "Address", multiline=True),
            FieldDefinition("address_line_1", "Address line 1"),
            FieldDefinition("address_line_2", "Address line 2"),
            FieldDefinition("suburb", "Suburb"),
            FieldDefinition("city", "City", previous_names=("locality",)),
            FieldDefinition("state", "State", previous_names=("region",)),
            FieldDefinition("post_code", "Post code", previous_names=("postal_code",)),
            FieldDefinition("country", "Country"),
            FieldDefinition("latitude", "Latitude", input_type="number", value_kind="latitude"),
            FieldDefinition("longitude", "Longitude", input_type="number", value_kind="longitude"),
            FieldDefinition("source", "Source", previous_names=("geocoding_source",)),
        ),
        duplicate_fields=("formatted_address",),
    ),
    EntityDefinition(
        type="project",
        slug="projects",
        singular="Project",
        plural="Projects",
        table="projects",
        fields=(
            FieldDefinition("project_type", "Project type", options=PROJECT_TYPES, allow_custom=True),
            FieldDefinition(
                "status",
                "Status",
                options=PROJECT_STATUSES,
                default="Active",
                value_aliases=(
                    ("active", "Active"),
                    ("paused", "Paused"),
                    ("completed", "Completed"),
                    ("abandoned", "Abandoned"),
                ),
            ),
            FieldDefinition("started_at", "Started", input_type="date", value_kind="date"),
        ),
        duplicate_fields=(),
    ),
    EntityDefinition(
        type="document",
        slug="documents",
        singular="Document",
        plural="Documents",
        table="documents",
        fields=(
            FieldDefinition("document_type", "Document type", options=DOCUMENT_TYPES, allow_custom=True),
            FieldDefinition("document_date", "Document date", input_type="date", value_kind="date"),
            FieldDefinition("issuer", "Issuer / created by"),
            FieldDefinition("file_name", "File name", editable=False),
            FieldDefinition("file_path", "Stored file path", overview=False, editable=False),
            FieldDefinition("mime_type", "MIME type", editable=False),
            FieldDefinition("file_size", "File size", editable=False),
        ),
        duplicate_fields=("file_name",),
    ),
    EntityDefinition(
        type="asset",
        slug="assets",
        singular="Asset",
        plural="Assets",
        table="assets",
        fields=(
            FieldDefinition("asset_type", "Asset type", options=ASSET_TYPES, allow_custom=True),
            FieldDefinition(
                "status",
                "Status",
                options=ASSET_STATUSES,
                allow_custom=True,
                default="Owned",
                value_aliases=(("active", "Owned"),),
            ),
            FieldDefinition("serial_number", "Serial number / asset number"),
            FieldDefinition("acquisition_date", "Acquisition date", input_type="date", value_kind="date", previous_names=("purchase_date",)),
            FieldDefinition("value", "Value", input_type="number", value_kind="whole_number", display_prefix="$"),
            FieldDefinition("latitude", "Latitude", input_type="number", value_kind="latitude"),
            FieldDefinition("longitude", "Longitude", input_type="number", value_kind="longitude"),
        ),
        duplicate_fields=("serial_number",),
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
