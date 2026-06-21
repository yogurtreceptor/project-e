# Database Design

Operation Eddy uses SQLite as the embedded local database for Stage 1.

## Core Tables

- `entities` stores shared identity and metadata for every canonical record.
- `people`, `organisations` and `locations` store type-specific fields keyed by `entity_id`.
- `relationships` stores first-class links between any two entities.
- `attachments` stores attachment metadata linked to entities; binary/file handling is deferred.

## Entity Storage

Every real-world object starts in `entities` with:

- `id`
- `type`
- `display_name`
- `summary`
- `notes`
- timestamps
- discovery metadata such as favourite and last viewed state

Typed tables hold fields that only apply to one entity type. Schema creation is definition-driven, and missing typed columns are added during startup so local databases can evolve additively.

## Location Storage

Locations are the canonical place/address records. The active `locations` table fields include:

- `formatted_address`
- `address_line_1`
- `address_line_2`
- `locality`
- `region`
- `postal_code`
- `country`
- `latitude`
- `longitude`
- `geocoding_source`

Coordinates are optional text fields at this stage so users can save incomplete locations and manually enter coordinates without a migration-heavy geospatial dependency. Validation for map display happens in the application layer.

## Address Ownership

People and Organisations do not own address columns. They reference Location entities through `located_at` relationships where appropriate. This keeps one canonical record per real-world place and avoids duplicate address data.

Older local databases may still contain previously-created Organisation address columns. They are no longer part of the active entity definition and are ignored by the application.

## Relationship Storage

Relationships store source and target entity IDs, type, status, optional dates, date certainty and notes. The database stores one row per relationship; inverse navigation is derived from relationship metadata.

## Map Storage

The map has no separate persistence table. It is built as a view over existing `locations`, `entities` and `relationships` data. Future map layers should add canonical entity/relationship data first, then expose that data through the map layer registry.
