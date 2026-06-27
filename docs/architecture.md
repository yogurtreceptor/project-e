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
- `app/web.py` handles HTTP routing, request parsing and responses. `app/document_storage.py` owns uploaded-file persistence and path safety; `app/relationship_workflow.py` owns inline relationship-target creation.
- `app/views.py` is the stable public facade for page rendering. Focused implementations live in `app/view_pages/` modules for layout, dashboard, entities, relationships, forms, search and maps.
- `app/db.py` is the stable database facade. `app/db_schema.py` owns connection, the append-only migration ledger and additive schema repair; entity, relationship and discovery persistence live in focused repository modules.
- `app/entities.py` defines the common entity model, metadata and supported entity types.
- `app/relationship_catalog.py` owns grouped relationship type metadata; `app/relationships.py` owns relationship records, selection rules and bidirectional behavior.
- `instance/documents/` stores uploaded document files referenced by Document entity metadata.
- `app/static/styles.css` provides the shared UI styling.

## Boundaries

Stage 1 should not introduce separate AI, automation, dispatcher, scheduling, authentication or cloud service layers.

The application should not depend on WAN access for normal operation.

## Entity Architecture

Current domains inherit from a common entity architecture:

- `EntityDefinition` describes each domain type, route slug, table and domain-specific fields.
- `FieldDefinition` describes reusable field metadata, including overview visibility, input type, controlled options, custom-value support, default values, display formatting, previous field names for safe renames and value aliases for controlled-value cleanup.
- `EntityRecord` is the shared runtime model for all entity instances.
- Shared active fields are `display_name`, `notes`, `created_at` and `updated_at`.
- `summary` remains in the shared table only as legacy storage/search fallback. It is not exposed on entity creation or edit forms.
- Domain-specific data is exposed as metadata on the same record object.
- Entity profile pages are generated from entity definitions and shared page sections.

People, Organisations, Locations, Projects, Documents and Assets all use this structure.

Architectural correction: typed tables now receive missing definition-driven columns during schema initialisation. The central `entities.type` SQLite `CHECK` constraint is also rebuilt when entity definitions add new types. Field renames use `FieldDefinition.previous_names` so data from old columns can be copied into renamed active columns without deleting the legacy column. Controlled fields can use value aliases to clean up legacy values such as lowercase statuses. This prevents future entity field or domain additions from breaking existing local databases.

## Entity Page Architecture

Entity pages are the primary interaction surface. Opening any entity should feel like opening a complete profile of a real-world object.

Reusable entity pages include:

- Header with name, type and quick actions.
- Overview with concise structured fields from the entity definition.
- Relationships grouped by connected entity type.
- Related Entities for graph exploration.
- Notes for free-text information.
- Documents section backed by first-class Document entity relationships.
- Timeline placeholder for created, modified and relationship events.
- Metadata with system information.

Future domains should inherit this structure by adding an `EntityDefinition` and fields, not by creating a one-off page.

## Relationship Architecture

Relationships are a central application model:

- `RelationshipRecord` links two `EntityRecord` instances, so endpoints can be any current or future entity type.
- `RelationshipType` centralises ordered source/target entity types, category, subtype, option labels, inverse labels, direction semantics, usage notes and selectability.
- Entity-page relationship panels are the primary relationship creation and editing surface.
- The relationship browser remains a global browse/audit view.
- Bidirectional navigation is derived from source and target endpoints instead of duplicating inverse rows.
- Relationship creation is entity-first and perspective-based: users choose an existing-entity or new-entity workflow, then select what the connected entity is in relation to the current entity.
- Directional relationship types normalise source/target storage during save while preserving the user's original page context for redirects.
- Person-to-Person family relationships use neutral canonical definitions and derive optional sex-aware display labels from Person metadata.
- Legacy relationship keys remain loadable but non-selectable so existing data is preserved without offering invalid new options.

Date uncertainty is represented as metadata beside structured calendar date values.

## Discovery Architecture

Discovery uses shared entity and relationship query primitives:

- Global search matches canonical entity fields, typed profile fields, notes and relationship context.
- Entity list pages support text filtering and favourites-only filtering.
- Favourites are persisted as shared entity metadata.
- Recent entities are tracked with `last_viewed_at` when an entity profile is opened.
- Dashboard discovery panels read from the same reusable queries as search and filters.

Architectural correction: discovery is not implemented as dashboard-only shortcuts. It lives in the data layer so every current and future entity type participates without custom code.

## Document Architecture

Documents are first-class entities rather than attachments stored inside another entity.

- Document records use the same entity, form, search, dashboard, relationship and detail-page architecture as other domains.
- Uploaded files are stored locally under `instance/documents/`.
- File metadata such as original file name, MIME type, stored path and file size lives on the Document entity.
- Documents link to People, Organisations, Locations, Projects, Assets or other Documents through relationships.

Older local databases may still contain an unused `attachments` table. It is no longer created or rendered by the active application because file-bearing records should be Documents.

## Documentation Rule

Planning documents should be updated when architecture, scope, data model or domain boundaries change.

## Geographic Architecture

Maps are implemented as views over the entity and relationship system, not as a separate data store.

- Location entities own address and coordinate fields.
- People and Organisations reference Location entities through `located_at` relationships.
- `app/geo.py` assembles map payloads from canonical entities and relationships.
- The map layer registry exposes Locations, Organisations, People and Assets.
- Future layers should be added by registering a new layer and deriving markers from canonical records, not by creating map-only persistence.
- Locations without valid coordinates remain valid records and are omitted from marker payloads until coordinates are added.
- Assets can appear when they have valid direct coordinates or a `located_at` relationship to a coordinate-bearing Location.
- Projects and Documents do not appear as map markers, even when related to Locations.

Address lookup is behind a small geocoder boundary. The current provider uses OpenStreetMap Nominatim and returns normalised address fields, coordinates and source metadata. Manual address and coordinate editing remains authoritative.

G-NAF is the preferred future option for Australian house-level geocoding, but it is intentionally deferred. It should be treated as an optional local address index or plugin-style data pack with setup instructions, not a mandatory dependency or a table inside the main entity database. Nominatim remains useful for lightweight lookup, places, fallback search and non-Australian addresses.

Architectural correction: Organisation address fields were removed from the active entity definition. Organisation geography now comes from Location relationships so there is one canonical place record per real-world address or place.
