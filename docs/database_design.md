# Database Design

Stage 1 uses SQLite through Python's standard library.

The design should keep identity, typed domain data and relationships clear enough to maintain.

## Core Tables

Current foundation tables are created from the central entity definitions.

Current foundation tables:

- `entities`: canonical identity for every Person, Organisation and Location.
- `people`: Person-specific fields keyed by `entity_id`.
- `organisations`: Organisation-specific fields keyed by `entity_id`.
- `locations`: Location-specific fields keyed by `entity_id`.

Planned later tables:

- `relationships`: first-class links between two entities.
- `aliases`: alternate names for entities.
- `imports`: optional records for simple import runs.

## Entities

`entities` should hold shared fields:

- `id`
- `type`
- `display_name`
- `summary`
- `notes`
- `created_at`
- `updated_at`

Entity type should be constrained to the Stage 1 domain types unless a later ADR expands the ontology.

## Typed Profile Tables

Typed tables should contain fields specific to each entity type while preserving the canonical entity record.

- `people` stores person-specific profile fields.
- `organisations` stores organisation-specific profile fields.
- `locations` stores place and address fields.

The implementation should avoid duplicating canonical names or identity fields across typed tables unless there is a clear search or display reason.

Typed tables are generated from `EntityDefinition` entries so future domains can be added with minimal schema and UI duplication. Existing databases may need explicit migrations when definitions change after data exists.

## Relationships

Relationships are not implemented in the initial application foundation.

When added, `relationships` should hold:

- `id`
- `source_entity_id`
- `target_entity_id`
- `type`
- `direction`
- `status`
- `started_at`
- `ended_at`
- `notes`
- `created_at`
- `updated_at`

Both endpoints should reference `entities`.

Relationship records should support navigation in both directions, even when the relationship type has directional meaning.

## Search

Search should be planned early and implemented before maps.

Search-ready data may come from:

- entity display names
- aliases
- typed profile fields
- relationship labels or notes

SQLite full-text search can be considered when simple indexed queries are no longer enough.

## Imports

Import support should remain simple in Stage 1.

Imports may record source filename, import time, row counts and notes. Import logic should create or update canonical entities and relationships rather than maintaining a separate imported-data model.

