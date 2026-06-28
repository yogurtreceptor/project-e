# Build Log

## 2026-06-28

Person title deferred.

What changed:

- Removed Title from the active Person form and model. Existing additive database columns are left intact for compatibility until optional fields are implemented later.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

People naming simplified.

What changed:

- Removed user-entered Person name and preferred name fields.
- Made given name the only required Person naming field; middle and family names remain optional.
- Generate the internal Person display name from given plus family name across normal forms, inline relationship creation and merges. Middle name remains stored but is not displayed in the normal name.
- Preserved legacy stored display names until an existing Person is edited or merged; additive legacy columns are not destructively removed.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`
- Local HTTP smoke test covered the People create form and structured-name submission.

Family tree visualisation proof of concept completed.

What changed:

- Added a Family tree view to the relationship browser using only existing canonical Person relationships.
- Added reusable relationship-to-graph extraction with canonical entity-ID node deduplication.
- Added a generic layered graph layout based on edge rank differences, independent of family terminology.
- Rendered generations above descendants using adjacent parent/child edges only, with siblings naturally sharing a row and sibling/spouse/partner links shown as same-level connections where data permits. Stored multi-generation relationships are represented through the parent/child chain without redundant direct lines.
- Added deterministic cycle detection, safe empty states and tests for hierarchy, deduplication, unrelated relationship filtering and cyclic input.
- Aligned zero-rank relationship groups on a clean generational grid, kept partners and siblings together, rendered orthogonal parent/child connectors, and added distinct partner/spouse and sibling connector styles with an on-page key.
- Aligned equivalent hierarchy endpoints before rank assignment, keeping co-parents and co-children on the same generation when one branch has deeper known ancestry and leaving visual space for missing ancestors.
- Ordered generational rows by adjacent hierarchy connections and widened gaps between differing connection sets, so mixed parent sets stay visually attached to only their recorded children.
- Bundled hierarchy connectors by exact incoming parent set, giving every unique parent combination an independent trunk and grouping only children who share that complete set.
- Isolated exact-parent-set bundles onto separate source ports and routing lanes, with adaptive generation spacing and regression coverage for A-only, A+B and A+C half-sibling groups.
- Replaced generic row heuristics with family-specific partner units and exact-parent-set child blocks; added bounded parent-row/lane/trunk crossing minimisation so casing is used only for unavoidable intersections.
- Removed explicit sibling connectors and made partner units the final hard row-ordering constraint; siblings now appear only through shared exact-parent-set child connectors and are arranged around, never inside, partner units.

Current limitations:

- The view is a simple whole-dataset diagram with deterministic row ordering; it does not yet offer focus, zoom controls, branch collapsing or pedigree-grade family-unit routing.
- Aunt/uncle, cousin and generic family records are not inferred into generations because the view does not invent missing parent/child links.
- Dense, disconnected or contradictory data may be visually wide; contradictory parent cycles are retained as dashed warning edges without affecting layout generation.

Extension path:

- New graph views can supply a relationship edge mapper to the extraction framework and reuse the layered layout and renderer contract.
- Alternative generic layouts can consume the same `RelationshipGraph` when mixed-entity or highly connected graphs need force-directed, radial or component-aware placement.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-22

Relationship question wording clarified.

What changed:

- Replaced ambiguous relationship prompt fallback wording with explicit entity names whenever a connected entity name is available.
- Existing-entity relationship prompts now render as `What is Test3 in relation to Test4?` when both entities are known.
- New-entity relationship prompts use the typed name on re-render and update live in the browser as the active new entity name changes, even when multiple inline entity forms are available.
- Kept relationship choices as short role nouns such as Employee, Daughter, Parent and Sibling; inverse relationship storage/display remains unchanged.

Architectural correction:

- The perspective-based relationship model was sound, but the UI still used the phrase `this entity` when no selected target name had been injected into the prompt. That phrasing made users remember which workflow side was being described. The prompt now treats the connected entity name as first-class display state and updates it from either the selected existing entity or the new entity name field.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-22

Relationship workflow toggle regression fixed.

What changed:

- Fixed the client-side workflow toggle so selecting New Entity immediately hides Existing Entity and shows the New Entity form.
- Kept Existing Entity selected by default on page load.
- Added a regression assertion for the rendered workflow script so the broken selector shape cannot return unnoticed.

Architectural correction:

- The previous cleanup fixed server-rendered hidden panels but left a malformed JavaScript selector in the inline script. That syntax error prevented workflow change listeners from attaching, so clicking the New Entity radio did nothing. The selector now uses a valid quoted CSS selector, allowing the same mutual-exclusion model to work after page load.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`
- Local smoke test confirmed `/relationships/new` renders Existing checked, New hidden, the workflow change listener present, and the broken selector absent.

## 2026-06-22

Relationship workflow visibility cleanup completed.

What changed:

- Made Existing Entity the default relationship workflow.
- Ensured only the selected workflow panel is visible at a time.
- Removed the search input from the Existing Entity workflow for now, leaving a reliable entity selector plus relationship fields.
- Kept relationship role, dates, date certainty and notes available in both Existing Entity and New Entity workflows.
- Added regression coverage for mutual workflow visibility and hidden-panel CSS behavior.

Architectural correction:

- The inactive workflow panels used the HTML `hidden` attribute, but `.relationship-step { display: grid; }` could override the browser default hidden styling. Added an explicit `[hidden] { display: none !important; }` rule so inactive workflow panels are truly hidden and users never scroll through fields from the other workflow.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-22

Relationship creation workflow simplification completed.

What changed:

- Changed relationship creation to ask what the connected entity is in relation to the currently viewed entity.
- Added perspective relationship choices such as Daughter, Father, Employee and Employer that translate into canonical source/target/type storage automatically.
- Split the relationship form into independent Existing entity and New entity workflows. Only the selected workflow is visible.
- Kept relationship metadata consistent across both workflows: relationship role, status, start/end dates, date certainty and notes.
- Replaced free-text Gender / sex with controlled Person Sex values: Male, Female, Other and Unknown.
- Updated family role labels so Male/Female can display father, mother, son, daughter, brother or sister, while Other/Unknown use neutral labels.
- Preserved existing relationship storage and inverse display behavior.

Architectural correction:

- The previous form mixed existing-entity linking and new-entity creation in one long surface, and exposed canonical relationship type labels rather than the connected entity's role from the current page's perspective. The UI now has two separate workflow panels and a perspective-to-canonical translation layer before validation and save. This keeps the database model stable while removing user-facing direction ambiguity.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-22

Relationship taxonomy correction completed.

What changed:

- Reworked relationship definitions into ordered source/target definitions with category, subtype, forward label, reverse label, direction flag, usage notes and selectability.
- Removed legacy/gendered family types from new relationship choices and replaced them with neutral family-tree-ready definitions such as Parent / child and Sibling.
- Added optional Person Sex field support for display labels only. Relationship creation does not require it.
- Added sex-aware family labels for parent/child, sibling, grandparent/grandchild and aunt/uncle relationships, with neutral fallback labels when Sex is Other or Unknown.
- Tightened the relationship form so forced entity-pair workflows only render and send valid options for that pair. Organisation to Person no longer contains Family options in the dropdown or page option payload.
- Added Person-Location, Person-Project, Organisation-Project, Organisation-Location, Asset-Location and Document pair definitions that match current Stage 1 domains.
- Preserved legacy keys such as `located_at`, `mother_of`, `father_of`, `child_of`, `related_to` and `associated_with` as loadable but non-selectable definitions.

Architectural correction:

- Relationship definitions were previously close to pair-aware but still behaved like unordered pairs with generic and legacy definitions available to the browser. This allowed inappropriate options to leak into workflows and made family inverse labels brittle. Definitions now have canonical direction and selectability, and both server validation and UI rendering use the same selectable pair-filtered taxonomy.

Migration approach:

- Existing relationships are not rewritten during startup. Old keys remain readable as legacy definitions so existing records continue to load. Safe legacy `located_at` rows still contribute to Geography and Map views. New relationship creation uses only selectable pair-specific definitions.

Manual testing steps:

1. Open an Organisation page and add a Person relationship; confirm Family options are not shown.
2. Open a Person page and add a Person relationship; confirm Family options are shown.
3. Confirm Person to Organisation shows employment, member, provider/customer and ownership-style options.
4. Confirm Organisation to Location shows only location-specific options.
5. Change the connected entity type and confirm the relationship options change.
6. Create a Parent / child relationship and confirm it displays naturally from both Person pages.
7. Create a Sibling relationship and confirm it displays naturally from both Person pages.
8. Set Person Sex to Male or Female and confirm labels such as father, mother, son, daughter, brother or sister are used where relevant.
9. Set Person Sex to Unknown and confirm neutral labels such as parent, child or sibling are used.
10. Open existing relationships and confirm they still load.
11. Try submitting an invalid type for a pair, such as Parent / child for Person to Organisation, and confirm validation rejects it.
12. Navigate from each connected entity page and confirm the relationship is visible from both sides.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-22

Entity-first relationship creation redesign completed.

What changed:

- Reworked relationship creation so the connected entity is chosen before the relationship category/type.
- Added pair-aware relationship definitions with category, subtype, option label, valid entity-type pairs and bidirectional labels.
- Added context-aware relationship type filtering for Person-Person, Person-Organisation, Organisation-Location, Asset-Location and Document links to Person, Organisation, Asset or Project.
- Added inline connected-entity creation for Person, Organisation and Location records from the relationship workflow.
- Added existing-entity filtering inside the relationship form.
- Added relationship direction normalisation so workflows can start from either side while display labels remain semantically correct.
- Kept the relationship database row lightweight: source, target, type key, status, dates, date certainty and notes.
- Updated Geography and Map relationship handling so all location-category relationship types can contribute to location display, not only `located_at`.

Architectural correction:

- Relationship types were previously a flat global list, which allowed irrelevant options to appear for unrelated entity pairs. Relationship definitions now own pair applicability and category/subtype metadata, and validation rejects relationship types that are not valid for the selected endpoints.

Decision captured:

- Phone numbers, emails and websites remain simple direct fields for Stage 1.
- The recommended future path is a lightweight Contact Method model linked to entities when multiple contact points, preference flags or validity dates become necessary. A full Communications domain remains out of scope.

Manual testing steps:

1. Open an Organisation page and choose Add person relationship.
2. Confirm the form starts with the connected entity choice before relationship type.
3. Select an existing Person and confirm relationship options include Work: Employee/Manager/Director and do not include Family options.
4. Open a Person page, add a Person relationship and confirm Family, Work, Education, Health and Friend / social options appear.
5. Open an Organisation page, add a Location relationship and confirm location-related options such as Located at, Headquartered at, Branch at and Operates at appear.
6. From an Organisation relationship workflow, choose Create new entity, create a new Person, choose Work: Employee and save.
7. Confirm the new Person record and relationship both save, then the app returns to the original Organisation page.
8. Open both connected entity pages and confirm the relationship appears on both sides with correct labels.
9. Open the global Relationships page and confirm existing relationships still load.
10. Confirm irrelevant relationship types, such as Family options for Person-Organisation, are not offered.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## 2026-06-21

Entity form standardisation milestone completed.

What changed:

- Removed the generic `summary` control from entity creation and edit forms.
- Kept `notes` as the flexible free-text area and retained the database `summary` column only as legacy compatibility/search fallback.
- Added structured Person fields for title, middle name and preferred name while keeping simple phone/email fields for Stage 1.
- Added controlled preset-backed Organisation, Project, Document and Asset category fields, with custom values allowed where useful.
- Made Project status controlled with Active, Paused, Completed and Abandoned.
- Renamed Location fields from locality/region/postal code/geocoding source to city/state/post code/source, and added suburb.
- Updated address lookup normalisation and form fill logic so suburb can be populated when available.
- Removed Project and Document reference fields from active forms.
- Renamed Asset purchase date to acquisition date and serial number label to serial number / asset number.
- Made Asset value whole-number-only in validation and display it with a dollar sign on detail pages.

Architectural correction:

- Field definitions now own controlled options, custom-value support, defaults, display prefixes and previous field aliases. This keeps form rendering, read formatting and additive migrations in one reusable definition path instead of scattering one-off behavior across views and database code.
- Renamed fields are migrated by copying legacy column values into new active columns on startup while leaving old columns in place. This protects existing local databases without destructive rewrites.
- Legacy controlled values can be normalised with field-level value aliases; existing lowercase Project status `active` becomes `Active`, and existing Asset status `active` becomes `Owned`.

Decision captured:

- Phone/email and website fields remain simple direct fields for Stage 1.
- Contact methods may later become first-class related records, but no Communications domain is introduced in this milestone.
- Controlled custom values are stored in the same typed table text column as preset values rather than in separate lookup tables.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

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

Additional domains milestone completed.

What changed:

- Added Projects, Documents and Assets as definition-driven entity domains.
- Added typed tables for `projects`, `documents` and `assets` through the existing schema creation path.
- Added local Document upload handling with files stored under `instance/documents/` and file metadata stored on Document entities.
- Replaced the active attachment UI concept with relationship-driven Document links.
- Added reusable relationship types for `belongs_to` and `references`.
- Added Assets to the map layer registry, including markers from direct coordinates and `located_at` Location relationships.
- Kept Projects and Documents out of map marker payloads.
- Confirmed dashboard cards, navigation, entity lists, forms, detail pages, search and relationships use the existing shared architecture.

Architectural correction:

- Existing SQLite databases created before new domains would reject new entity types because `entities.type` used a generated `CHECK` constraint. Startup now rebuilds the `entities` table constraint when entity definitions add new types.
- The old attachment table path is no longer created by active schema initialisation because Documents are now first-class entities.

Decision captured:

- Projects, Documents and Assets are normal entity domains.
- Documents are file-bearing entities, not nested attachments.
- Assets are the only new domain that can appear on the map.

Verification:

- `python3 -m compileall app run.py tests`
- `python3 -m unittest discover -s tests`

## Relationship integrity, merge and structured filters — 2026-06-28

- Added raw-row relationship auditing for orphan/broken/self/duplicate links and suspicious family-role combinations.
- Surfaced audit warnings in relationship and entity views.
- Added transactional, preview-first duplicate record merging with relationship repointing/deduplication and append-only edit history.
- Added a declarative structured-filter registry with birthday month/year/missing birthday and organisation-without-location filters.
- Added migration, repository, UI and focused regression coverage; full suite passes.

## Shared relationship entity creation form — 2026-06-28

- Reused the definition-driven standard entity form fields in the Add Relationship new-entity workflow.
- Added Birthday and all other Person fields to inline creation without a separate field allowlist.
- Preserved submitted inline values on validation errors and retained transactional person-plus-relationship creation.
- Added regression coverage ensuring every Person definition field renders inline and Birthday persists on the linked Person.
