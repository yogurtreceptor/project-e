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
    optional: bool = False
    optional_group: str = ""
    optional_group_label: str = ""
    storage_kind: str = "scalar"
    reference_type: str = ""
    multiple: bool = False
    measurement_category: str = ""

    @property
    def typed_column(self) -> bool:
        return self.storage_kind == "scalar"


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
        return tuple(field.name for field in self.fields if field.typed_column)


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
    deleted_at: str = ""

    @property
    def type(self) -> str:
        return self.definition.type

    @property
    def slug(self) -> str:
        return self.definition.slug

    @property
    def is_deleted(self) -> bool:
        return bool(self.deleted_at)

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
    "Letter",
    "Licence",
    "Receipt",
    "Certificate",
    "Statement",
    "Contract",
    "Invoice",
    "Manual",
    "Other",
)

ASSET_TYPES = (
    "Vehicle",
    "Appliance",
    "Tool",
    "Electronic device",
    "Computer",
    "Phone",
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
            FieldDefinition("alias", "Alias", optional=True),
            FieldDefinition("nickname", "Nickname", optional=True),
            FieldDefinition(
                "height", "Height", optional=True, storage_kind="measurement",
                measurement_category="length",
            ),
            FieldDefinition(
                "weight", "Weight", optional=True, storage_kind="measurement",
                measurement_category="mass",
            ),
            FieldDefinition(
                "languages", "Languages", optional=True, storage_kind="reference",
                reference_type="language", multiple=True,
            ),
            FieldDefinition(
                "nationalities", "Nationalities", optional=True, storage_kind="reference",
                reference_type="country", multiple=True,
            ),
            FieldDefinition(
                "ethnicities", "Ethnicities", optional=True, storage_kind="reference",
                reference_type="ethnicity", multiple=True,
            ),
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
            FieldDefinition("organisation_type", "Organisation classification", storage_kind="taxonomy"),
            FieldDefinition("aliases", "Other names", optional=True, storage_kind="alias", multiple=True),
            FieldDefinition("website", "Website", optional=True),
            FieldDefinition("phone", "Phone", optional=True),
            FieldDefinition("email", "Email", optional=True),
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
            FieldDefinition("formatted_address", "Address", multiline=True, optional=True),
            FieldDefinition("address_line_1", "Address line 1", optional=True),
            FieldDefinition("address_line_2", "Address line 2", optional=True),
            FieldDefinition("suburb", "Suburb", optional=True),
            FieldDefinition("city", "City", previous_names=("locality",), optional=True),
            FieldDefinition("state", "State", previous_names=("region",), optional=True),
            FieldDefinition("post_code", "Post code", previous_names=("postal_code",), optional=True),
            FieldDefinition("country", "Country", optional=True),
            FieldDefinition("latitude", "Latitude", input_type="number", value_kind="latitude", optional=True, optional_group="coordinates", optional_group_label="Coordinates"),
            FieldDefinition("longitude", "Longitude", input_type="number", value_kind="longitude", optional=True, optional_group="coordinates", optional_group_label="Coordinates"),
            FieldDefinition("source", "Source", previous_names=("geocoding_source",), optional=True),
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
            FieldDefinition("started_at", "Started", input_type="date", value_kind="date", optional=True),
            FieldDefinition("target_date", "Target date", input_type="date", value_kind="date", optional=True),
            FieldDefinition("ended_at", "Ended / completed", input_type="date", value_kind="date", optional=True),
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
            FieldDefinition("document_type", "Document purpose", options=DOCUMENT_TYPES, allow_custom=True),
            FieldDefinition("document_date", "Document date", input_type="date", value_kind="date", optional=True),
            FieldDefinition("identifier", "Identifier / reference number", optional=True),
            FieldDefinition("expiry_date", "Expiry date", input_type="date", value_kind="date", optional=True),
            FieldDefinition("file_name", "File name", editable=False),
            FieldDefinition("file_path", "Stored file path", overview=False, editable=False),
            FieldDefinition("mime_type", "MIME type", editable=False),
            FieldDefinition("file_size", "File size", editable=False),
        ),
        duplicate_fields=("file_name", "identifier"),
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
            FieldDefinition("manufacturer", "Manufacturer", optional=True),
            FieldDefinition("model", "Model", optional=True),
            FieldDefinition("serial_number", "Serial number / asset number", optional=True),
            FieldDefinition("acquisition_date", "Acquisition date", input_type="date", value_kind="date", previous_names=("purchase_date",), optional=True),
            FieldDefinition("value", "Value", input_type="number", value_kind="whole_number", display_prefix="$", optional=True),
            FieldDefinition("latitude", "Latitude", input_type="number", value_kind="latitude", optional=True, optional_group="coordinates", optional_group_label="Coordinates"),
            FieldDefinition("longitude", "Longitude", input_type="number", value_kind="longitude", optional=True, optional_group="coordinates", optional_group_label="Coordinates"),
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
        deleted_at=row["deleted_at"],
        metadata={
            field.name: row[field.name] if field.typed_column else ""
            for field in definition.fields
        },
    )
