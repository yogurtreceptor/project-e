# Architecture

Operation Eddy uses a simple local-first architecture for Stage 1.

## Shape

The system is organised around three practical layers:

- Local UI for browsing, editing, searching and navigating information.
- Local application layer for validation, persistence rules and view logic.
- Embedded SQLite database for durable local storage.

No external runtime dependencies are required for the current foundation.

## Current Implementation

- `run.py` starts a local HTTP server.
- `app/web.py` handles HTTP routing and request/response concerns.
- `app/views.py` owns reusable page layouts, navigation, entity profiles, relationship views and forms.
- `app/db.py` owns SQLite connection, definition-driven schema creation, additive field migration and CRUD operations.
- `app/entities.py` defines the common entity model, metadata and supported entity types.
- `app/relationships.py` defines relationship records, relationship types and bidirectional labels.
- `app/static/styles.css` provides the shared UI styling.

## Boundaries

Stage 1 should not introduce separate AI, automation, dispatcher, scheduling, authentication or cloud service layers.

The application should not depend on WAN access for normal operation.

## Entity Architecture

Current domains inherit from a common entity architecture:

- `EntityDefinition` describes each domain type, route slug, table and domain-specific fields.
- `FieldDefinition` describes reusable field metadata, including overview visibility and input type.
- `EntityRecord` is the shared runtime model for all entity instances.
- Shared fields are `display_name`, `summary`, `notes`, `created_at` and `updated_at`.
- Domain-specific data is exposed as metadata on the same record object.
- Entity profile pages are generated from entity definitions and shared page sections.

Architectural correction: typed tables now receive missing definition-driven columns during schema initialisation. This prevents future entity field additions from breaking existing local databases.

## Entity Page Architecture

Entity pages are the primary interaction surface. Opening any entity should feel like opening a complete profile of a real-world object.

Reusable entity pages include:

- Header with name, type, summary and quick actions.
- Overview with concise structured fields from the entity definition.
- Relationships grouped by connected entity type.
- Related Entities for graph exploration.
- Notes for free-text information.
- Attachments section backed by attachment table architecture.
- Timeline placeholder for created, modified and relationship events.
- Metadata with system information.

Future domains should inherit this structure by adding an `EntityDefinition` and fields, not by creating a one-off page.

## Relationship Architecture

Relationships are a central application model:

- `RelationshipRecord` links two `EntityRecord` instances, so endpoints can be any current or future entity type.
- `RelationshipType` centralises labels, inverse labels and direction semantics.
- Entity-page relationship panels are the primary relationship creation and editing surface.
- The relationship browser remains a global browse/audit view.
- Bidirectional navigation is derived from source and target endpoints instead of duplicating inverse rows.

Date uncertainty is represented as metadata beside structured calendar date values.

## Discovery Architecture

Discovery uses shared entity and relationship query primitives:

- Global search matches canonical entity fields, typed profile fields, notes and relationship context.
- Entity list pages support text filtering and favourites-only filtering.
- Favourites are persisted as shared entity metadata.
- Recent entities are tracked with `last_viewed_at` when an entity profile is opened.
- Dashboard discovery panels read from the same reusable queries as search and filters.

Architectural correction: discovery is not implemented as dashboard-only shortcuts. It lives in the data layer so every current and future entity type participates without custom code.

## Attachments Architecture

Attachments are prepared as first-class entity-adjacent records, but full upload handling is deferred.

The current architecture supports attachment metadata linked to canonical entities. Later milestones can add file selection, storage rules, previews and indexing without redesigning entity pages.

## Documentation Rule

Planning documents should be updated when architecture, scope, data model or domain boundaries change.

## Geographic Architecture

Maps are implemented as views over the entity and relationship system, not as a separate data store.

- Location entities own address and coordinate fields.
- People and Organisations reference Location entities through `located_at` relationships.
- `app/geo.py` assembles map payloads from canonical entities and relationships.
- The map layer registry initially exposes Locations, Organisations and People.
- Future layers should be added by registering a new layer and deriving markers from canonical records, not by creating map-only persistence.
- Locations without valid coordinates remain valid records and are omitted from marker payloads until coordinates are added.

Address lookup is behind a small geocoder boundary. The current provider uses OpenStreetMap Nominatim and returns normalised address fields, coordinates and source metadata. Manual address and coordinate editing remains authoritative.

G-NAF is the preferred future option for Australian house-level geocoding, but it is intentionally deferred. It should be treated as an optional local address index or plugin-style data pack with setup instructions, not a mandatory dependency or a table inside the main entity database. Nominatim remains useful for lightweight lookup, places, fallback search and non-Australian addresses.

Architectural correction: Organisation address fields were removed from the active entity definition. Organisation geography now comes from Location relationships so there is one canonical place record per real-world address or place.
