# Architecture

Operation Eddy uses a simple local-first architecture for Stage 1.

## Shape

The system is organised around three practical layers:

- Local UI for browsing, editing, searching and navigating information.
- Local application layer for validation, persistence rules and view logic.
- Embedded SQLite database for durable local storage.

The core application uses only the Python standard library. Map tiles, browser map assets and address lookup are optional external services; core record workflows do not require them.

## Current Implementation

- `run.py` starts a local HTTP server.
- `app/web.py` handles HTTP routing, request parsing and responses. `app/document_storage.py` owns uploaded-file persistence and path safety, `app/document_lifecycle.py` protects reference-aware cleanup, and `app/relationship_workflow.py` owns inline relationship-target creation.
- `app/views.py` is the stable public facade for page rendering. Focused implementations live in `app/view_pages/` modules for layout, dashboard, entities, relationships, forms, search and maps.
- `app/db.py` is the stable database facade. `app/db_schema.py` owns connection, the append-only migration ledger and additive schema repair; entity, relationship and discovery persistence live in focused repository modules.
- `app/entities.py` defines the common entity model, metadata and supported entity types.
- `app/relationship_catalog.py` owns grouped relationship type metadata; `app/relationships.py` owns relationship records, selection rules and bidirectional behavior.
- `instance/documents/` stores uploaded document files referenced by Document entity metadata.
- `app/static/styles.css` provides the shared UI styling.

## Local Data Boundary

`instance/` is the private runtime boundary and is intentionally ignored by Git.
On startup the application creates the directory, an empty SQLite database and the
`instance/documents/` upload directory when they are absent. Source code, schema
logic, documentation and intentionally reviewed fictional fixtures remain tracked;
real entity records and uploaded files do not.

Developers do not need a copied database or sample profile to run the application.
A fresh clone starts with clean empty dashboard and browse states. If shareable
examples are introduced later, they should be minimal, fictional and kept outside
the ignored runtime directories.

## Boundaries

Stage 1 may use deterministic in-process assistance and internal maintenance when behaviour is local, explainable and preserves user control. Duplicate warnings, derived views, display-name maintenance, review-batch archival and relationship candidate recomputation fit this boundary. Consequential mutations require explicit user confirmation.

Stage 1 should not introduce AI, autonomous goal-directed workflow, dispatcher, scheduling, authentication or cloud service layers, nor perform unreviewed consequential actions or autonomous external side effects.

The application should not depend on WAN access for normal operation. Optional network aids must leave core records and workflows usable without them.

## Entity Architecture

Current domains inherit from a common entity architecture:

- `EntityDefinition` describes each domain type, route slug, table, domain-specific fields and strong fields used for duplicate warnings.
- `FieldDefinition` describes reusable field metadata, including overview visibility, input type, structured value kind, controlled options, custom-value support, defaults, display formatting, previous field names for safe renames and value aliases for controlled-value cleanup.
- `EntityRecord` is the shared runtime model for all entity instances.
- Shared active fields are `display_name`, `notes`, `created_at` and `updated_at`. For People, `display_name` is internal derived data generated from `given_name` plus `family_name`; it is not a separate user-entered field.
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
- Derived timeline for creation, modification, edit history and relationship events.
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

### Relationship Visualisation Framework

Relationship visualisations are derived views over canonical entity and relationship records; they do not introduce graph-specific persistence. Data selection is separate from layout and rendering: the relationships view selects the largest complete connected family component, while `person_family_subgraph` provides the bounded person-centred selector intended for later record-local views; both feed the same family layout engine. `app/relationship_graph.py` separates relationship extraction from presentation by adapting `RelationshipRecord` instances into deduplicated `RelationshipGraph` nodes and edges. The family adapter maps Person parent/child, grandparent, spouse and partner records, then limits the rendered graph to same-generation and adjacent-generation edges. Explicit sibling records remain canonical relationship data but do not become tree edges; siblings are visible together only through a shared exact-parent-set connector. Multi-generation records remain canonical data but are represented visually through their parent/child chain rather than redundant direct lines.

`app/graph_layout.py` now applies a family-tree-specific layered model over the extracted graph contract. It builds fixed generation rows, groups children by complete incoming parent set, orders ancestry and child blocks, then applies spouse/partner components as the final indivisible row constraint before assigning connector lanes. This ensures sibling placement can move around a partner unit but can never split it. Zero-rank-connected nodes are grouped onto the same row and kept adjacent. Endpoints that connect to the same opposite node with the same rank delta are also aligned, so missing nodes leave generational space instead of pulling a shorter branch upward. Positive-rank edges then establish the generational grid. Deterministic neighbour-based ordering sweeps place each node near its actual adjacent-row connections, and differing hierarchy-neighbour sets receive extra horizontal separation to avoid visually implying unstored links. Positive-rank cycles are detected and marked rather than repeatedly traversed, and nodes are keyed by canonical entity ID. Server-rendered SVG uses short, direct horizontal spouse/partner connectors and orthogonal parent/child connectors. No sibling-to-sibling connector is rendered. Hierarchy targets are bundled only when their complete incoming-source sets match. Every distinct source combination receives independent source-node ports, routing lanes, trunks and target bars; generation spacing expands with bundle count. Before rendering, bounded deterministic searches reorder small parent rows, keep partner units and exact-parent-set child blocks contiguous, try alternate lane orders and score legal trunk positions against accepted connector segments. Connector casing is emitted only when all non-crossing placements and routes are exhausted, making overpasses a fallback rather than the default. No connector group shares a stem or junction across different endpoint sets.

The proof of concept favours deterministic, understandable placement over pedigree-chart optimisation. Partner units affect placement only: the view does not infer unstored parent, spouse or partner relationships, and it does not guarantee ideal ordering in unusually dense or contradictory datasets. Future visualisations should add an extractor (and, where necessary, a different reusable layout strategy) while retaining the same canonical graph contract.

## Discovery Architecture

Discovery uses shared entity and relationship query primitives:

- Global search matches canonical entity fields, typed profile fields, notes and relationship context.
- Search currently scans the local dataset in memory. This is intentionally retained until representative data shows a performance problem; SQLite filtering or FTS5 are the preferred future paths if scale requires them.
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

Documentation is part of each feature, behaviour, workflow, schema and architecture change. Agents must audit and update every affected planning/reference document, including feature status, roadmap, architecture, database design, ontology/glossary, UI workflow and build log where relevant. Commit subjects must describe the delivered change; agent attribution is a final trailer only.

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

## Data Quality and Merge Architecture

Relationship integrity is evaluated by `app/integrity.py` from raw relationship rows so orphan endpoints, unknown types, invalid/self references, duplicates and suspicious family combinations can be reported without preventing the audit itself. Warnings use the existing relationship browser and entity-profile surfaces.

`app/entity_merge.py` provides a reusable same-type preview-and-commit workflow. A merge is transactional: compatible blank fields are filled, notes are combined, relationships are repointed, duplicate/self relationships are removed, and the retired record plus conflicts and relationship snapshots are retained in append-only edit history. Normal entity edits also add history events.

Structured search filters are registry-driven in `app/structured_filters.py`. Each filter declares its key, label, applicable entity types, optional input and predicate; search applies the registry after shared text/type/favourite filtering. New filters should extend this registry rather than add route-specific query logic.


## Deterministic relationship inference

Family inference is implemented in `app/relationship_inference.py` as a reusable rule engine. Rules consume active person-to-person facts and return neutral, canonical candidates plus supporting relationship IDs. The initial rules cover grandparent/grandchild, full sibling, aunt/uncle and niece/nephew, and cousin. Parent/child remains manually entered source evidence. Full-sibling inference requires the same complete known parent set with at least two parents, so half relationships are not inferred accidentally.

Inference is local, deterministic and explainable; it does not use AI or autonomous automation. Mutation hooks rerun the engine after relationship changes and relevant person date changes, but no candidate becomes a relationship without explicit confirmation in the Inference Review Queue. For direct-generation relationships (parent/child and grandparent/grandchild), the younger person's DOB alone can establish the relationship start; an older person's DOB alone cannot. For sibling, partner, aunt/uncle, cousin, and other peer or collateral relationships, both people must have DOBs and the chronologically lower DOB is used. Candidates are fingerprinted from their rule, inferred date, and exact supporting rows, so a later DOB change is material evidence and may produce a new pending suggestion. Enriching the date of an already-confirmed relationship can be added later as a separate review rule. Manual records win conflicts. Self links, ancestry conflicts, duplicates, and cycles are filtered or rejected.

Candidates enter an Inference Review Queue rather than the active relationship set. A batch groups suggestions created by one recomputation trigger and presents one pending card at a time. It is archived automatically after its final decision; historic batches retain per-decision undo controls that reopen review. Confirmation creates a normal, user-owned relationship that is editable and deletable like a manually entered row. Dedicated audit fields retain its inference origin, source batch, rule, supporting relationship IDs, evidence fingerprint, and timestamps. Rejection stores the reviewed fingerprint as a suppression record. Changed or removed evidence invalidates pending suggestions, but confirmed relationships remain active and receive a non-blocking `changed` evidence-health flag. Confirmation triggers a fresh recomputation and any ripple suggestions go into a new batch.

## Derived platform services

`audit`, `query_engine`, `data_quality`, and `timeline` are independent reusable services. Registries allow domain rules and derivations to be added without changing their cores. Audit history records system mutations; timelines derive real-world events only. Data-quality findings and search results are derived views over canonical entities and relationships.
