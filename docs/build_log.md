# Build Log

## 2026-06-21

Architecture foundation documentation created for Operation Eddy.

Decisions captured:

- Stage 1 is a local-first structured information platform.
- Initial domains are People, Organisations and Locations.
- Entities are canonical records for real-world objects.
- Relationships are first-class records.
- Search and relationship navigation come before maps.
- Maps are a later Stage 1 view over Location data.
- AI, chat, dispatcher behaviour, scheduling, login, WAN features and automation are excluded from Stage 1.
- Simple import and export tools are allowed when they help populate, migrate or protect local data.
- SQLite or an equivalent embedded local database is the default persistence direction.

Initial application foundation implemented.

What changed:

- Added a no-dependency Python local web application.
- Added SQLite schema creation for `entities`, `people`, `organisations` and `locations`.
- Added reusable entity definitions to keep future entity types extensible.
- Added dashboard, browse pages, create/edit forms, detail pages and delete actions.
- Added shared layout and CSS.
- Added focused database CRUD tests.

Relationship features were intentionally not added in this pass.

Reusable entity architecture milestone completed.

What changed:

- Added a shared `EntityRecord` model for all domains.
- Moved reusable page layout, navigation, list, detail and form rendering into `app/views.py`.
- Changed schema creation to derive entity types and typed tables from `EntityDefinition`.
- Kept People, Organisations and Locations on the same CRUD flow.
- Added graceful server shutdown handling for `Ctrl+C`.

Architectural correction:

- Raw SQLite rows are no longer passed through route rendering as the domain model. This was corrected so future entity types can share behaviour, metadata and UI without copying route code.

Relationship-centred platform milestone completed.

What changed:

- Added first-class `RelationshipType` and `RelationshipRecord` models.
- Added SQLite `relationships` table referencing canonical `entities` at both endpoints.
- Added relationship CRUD, relationship browser, relationship detail pages and reusable relationship forms.
- Added bidirectional relationship panels on entity detail pages.
- Added central relationship type definitions with inverse labels.
- Added tests for cross-domain relationships and validation.

Architectural correction:

- Relationships are implemented as their own central model rather than domain-specific fields or duplicated inverse records. This keeps future entity domains relationship-capable without redesign.

Entity-first relationship UX completed.

What changed:

- Relationship creation is now primarily launched from entity detail pages.
- Entity pages group relationships by connected entity type: People, Organisations and Locations.
- Relationship rows can be edited or deleted from the entity context.
- The global relationship browser remains available for browsing and audit, but is no longer the main creation path.
- Relationship start and end fields now use calendar date inputs with date certainty metadata for exact, approximate or unknown dates.

Decision captured:

- Relationships remain centrally stored as first-class records, but the user workflow is entity-first. This keeps the data model correct while matching how users naturally add knowledge.

Reusable entity profile milestone completed.

What changed:

- Reworked entity detail pages into reusable profile pages rather than database-record views.
- Added shared profile sections: header, overview, relationships, related entities, notes, attachments, timeline and metadata.
- Added richer overview fields for People, Organisations and Locations through `FieldDefinition` metadata.
- Added additive schema evolution for typed entity tables so future fields can be introduced without deleting the local database.
- Added attachment metadata table architecture and an entity-page attachments placeholder.
- Added a regression test for reusable entity profile sections.

Architectural corrections:

- Documentation drift was corrected after `architecture.md`, `database_design.md` and `ui_principles.md` were found to contain ontology content. These documents were restored before completing the milestone.
- Typed entity tables now add missing definition-driven columns during schema initialisation. This corrects the previous assumption that `CREATE TABLE IF NOT EXISTS` was enough for evolving local schemas.

Discovery milestone completed.

What changed:

- Added global search across entity names, summaries, notes, typed fields and relationship context.
- Added entity list filtering by text and favourites.
- Added persisted favourite support on canonical entities.
- Added persisted recent-entity tracking through `last_viewed_at`.
- Added dashboard discovery sections for search, recent entities and favourites.
- Added relationship-aware search results that surface matching relationship context.
- Added tests for discovery, favourites, recent entities and relationship-aware search.

Architectural correction:

- Discovery is implemented through reusable data-layer query primitives rather than dashboard-specific logic. This keeps future entity types discoverable through the same search, filtering, favourite and recent-entity paths.

Geographic foundation milestone completed.

What changed:

- Added Location address fields for formatted address, structured address parts, latitude, longitude and geocoding source.
- Removed Organisation address fields from the active model so Organisations reference Location entities through relationships.
- Added `app/geo.py` for map layer definitions, marker payload assembly and replaceable geocoding provider logic.
- Added `/map` with Leaflet/OpenStreetMap rendering, pan/zoom, layer toggles, markers, popups and entity links.
- Added `/geocoding/search` using OpenStreetMap Nominatim through a provider boundary.
- Added address lookup on Location forms while preserving manual address and coordinate editing.
- Added Geography sections to entity pages with map jumps and Location relationship links.
- Added tests for map payload generation and map page marker/layer rendering.

Architectural correction:

- Corrected the remaining documentation drift in `database_design.md` and `ui_principles.md` before completing the milestone.
- Confirmed the map architecture is not a separate data store. It is a configurable view over canonical entities and `located_at` relationships.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`
- Local smoke test: `/`, `/map` and `/geocoding/search?q=Brisbane` returned HTTP 200.

Map and address lookup UX adjustment completed.

What changed:

- Changed Location address lookup from autocomplete-style typing to explicit Search Address results selection.
- Kept manual address and coordinate editing available when lookup results are incomplete or unavailable.
- Changed map layer defaults so only Locations are enabled initially; People and Organisations remain available as optional layers.
- Adjusted initial map fitting to prefer enabled layers.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`
- Local smoke test: `/map`, `/locations/new` and `/geocoding/search?q=Casino%20Drive%20Brisbane` returned HTTP 200.

G-NAF geocoding architecture decision documented.

Decision captured:

- G-NAF is the preferred future path for Australian house-level address coordinates.
- G-NAF will be treated as an optional local address index or plugin-style data pack rather than a mandatory Stage 1 dependency.
- The main Operation Eddy database should store selected Location records only, not the full G-NAF dataset.
- Nominatim remains the current lightweight lookup and future fallback for places, non-Australian addresses and cases where G-NAF is unavailable or does not match.

No code changes were made for this decision.
