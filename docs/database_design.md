# Database Design

Stage 1 uses SQLite through Python's standard library.

The design keeps canonical identity, typed domain data, relationships and future attachments clear enough to maintain.

## Core Tables

Current tables:

- `entities`: canonical identity for every entity.
- `people`: Person-specific fields keyed by `entity_id`.
- `organisations`: Organisation-specific fields keyed by `entity_id`.
- `locations`: Location-specific fields keyed by `entity_id`.
- `relationships`: first-class links between any two canonical entities.
- `attachments`: attachment metadata linked to canonical entities.

Planned later tables:

- `aliases`: alternate names for entities.
- `imports`: optional records for simple import runs.

## Entities

`entities` holds shared fields:

- `id`
- `type`
- `display_name`
- `summary`
- `notes`
- `created_at`
- `updated_at`

Entity type is constrained to the configured Stage 1 entity definitions unless a later architecture decision expands the ontology.

## Typed Profile Tables

Typed tables contain fields specific to each entity type while preserving the canonical entity record.

Typed tables are generated from `EntityDefinition` entries. Missing field columns are added during schema initialisation so future fields can be introduced without deleting the local database.

## Relationships

`relationships` holds:

- `id`
- `source_entity_id`
- `target_entity_id`
- `type`
- `status`
- `started_at`
- `started_at_precision`
- `ended_at`
- `ended_at_precision`
- `notes`
- `created_at`
- `updated_at`

Both endpoints reference `entities` and use `ON DELETE CASCADE`. A check constraint prevents a relationship from connecting an entity to itself.

The database stores one canonical relationship row rather than duplicating inverse rows.

## Attachments

`attachments` currently holds metadata only:

- `id`
- `entity_id`
- `file_name`
- `file_path`
- `notes`
- `created_at`

Upload, file storage and preview behaviour are future work. The table exists so entity pages can be designed around attachments now.

## Search

Search should be planned early and implemented before maps.

Search-ready data may come from:

- entity display names
- aliases
- typed profile fields
- relationship labels or notes
- attachment metadata

SQLite full-text search can be considered when simple indexed queries are no longer enough.
