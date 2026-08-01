# Architecture

Project E uses a simple local-first architecture. Phases 1 and 2 are complete development milestones; this document describes their current implementation. [Future direction](future_direction.md) describes later capability layers.

## Shape

The system is organised around three practical layers:

- Local UI for browsing, editing, searching and navigating information.
- Local application layer for validation, persistence rules and view logic.
- Embedded SQLite database for durable local storage.

The core application uses only the Python standard library. Map tiles, browser map assets, address lookup and explicitly configured public-HTTPS Calendar subscriptions are optional external services; core record workflows do not require them.

## Current Implementation

- `run.py` starts a local HTTP server through `app/http_server.py`. Each server receives an immutable path configuration, so tests and later runtime variants do not mutate shared handler class state.
- `app/web.py` remains the domain-controller boundary for server-rendered requests. `app/web_router.py` owns the top-level route map, `app/web_support.py` owns transport/form/response mechanics, and `app/event_forms.py` owns pure Event and recurrence form parsing. `app/document_storage.py` owns uploaded-file persistence and path safety, `app/document_lifecycle.py` protects reference-aware cleanup, and `app/relationship_workflow.py` owns inline relationship-target creation. `app/icalendar_service.py` owns bounded iCalendar parsing, preview-first local import and selectable Calendar ZIP export; `app/calendar_subscription_service.py` owns safe public-HTTPS subscription fetches, last-known-good caches and read-only Calendar projection.
- `app/views.py` is the stable public facade for page rendering. Focused implementations live in `app/view_pages/` modules for layout, dashboard, entities, relationships, forms, search and maps.
- `app/db.py` is the stable database facade. `app/db_schema.py` owns connection, the append-only migration ledger and additive schema repair; entity, relationship, Inbox, journal and discovery persistence live in focused repository modules. `app/entity_service.py` coordinates canonical entity lifecycle consequences such as birthday synchronisation, reminder resolution and relationship-inference recomputation without making the entity repository import those higher-level services.
- `app/entities.py` defines the common entity model, metadata and supported entity types.
- `app/defaults.py` is the single runtime definition for platform timezone, Calendar colours and durations, birthday settings and reminder timing defaults. Schema repair, services, routes and views consume those values rather than maintaining parallel literals; historical migration SQL retains the values that belonged to its original ledger step.
- `app/taxonomy.py` owns reusable three-level taxonomy persistence, migration and lookup. Relationship-specific pair, direction and inverse-label metadata is attached to relationship taxonomy entries; `app/relationships.py` remains the stable selection and bidirectional-behaviour facade.
- `TaxonomyChoice` is the shared presentation boundary for Organisation and Relationship comboboxes. It carries the submitted value, contextual label, complete path, depth and availability without changing either domain's persistence contract.
- `/system-tools` is a navigation hub over Search, Data Quality, Taxonomies, Recycle Bin, Audit, and Import and Export; child pages share its active navigation state.
- `instance/documents/` stores uploaded document files referenced by Document entity metadata.
- `app/static/styles.css` is the ordered application stylesheet manifest. It loads `foundation.css` for tokens, themes and global focus/motion policy, followed by focused modules for document defaults, application shells, Calendar, shared components, Inbox, System Tools, records, discovery, specialist views and shared interactions. The local static handler safely serves valid top-level stylesheet modules without maintaining a parallel filename list; `inbox-count.js` is the small visibility-aware count projection for the Browse shell.

The [Experience Philosophy](experience_philosophy.md) and [design documentation](design/README.md) govern the intended experience. The persistent shell, shared foundation and representative Person, Document and Project page compositions are implemented; the [page catalogue](design/page_and_view_catalogue.md) distinguishes current renderers, remaining verification and future direction.

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

The delivered Phase 1 foundation uses deterministic in-process assistance and internal maintenance only when behaviour is local, explainable and preserves user control. Duplicate warnings, derived views, display-name maintenance, review-batch archival and relationship candidate recomputation fit this boundary. Consequential mutations require explicit user confirmation.

Phase 2's original foundation is complete and its Event-focused refinement workspace remains active. Local reminder resolution and a durable Inbox provide configurable defaults and overrides, scoped recurring Event reminder edits, URL Calendar notification defaults over non-canonical cached occurrences, synchronised birthday Events, derived Document-expiry occurrences, lifecycle suppression, bounded archive presentation and append-only delivery transitions. A one-minute in-process registered job performs delivery and serial startup recovery with durable leases, runs and checkpoints; that registered maintenance boundary also refreshes enabled public Calendar subscriptions only when stale. `app.automation_service.py` adds a separate registry-only deterministic automation boundary: database rules reference only built-in trigger/action names and each logical execution has a durable run. Its sole current action evaluates due reminders, stores no executable user-authored code and cannot mutate a canonical Event; general proposal/approval infrastructure remains deferred. The experimental Task workflow and its proposal infrastructure were retired in migration `20260801_31_retire_task_subsystem`; historical migrations remain ledger-compatible, but no Task runtime modules, tables, entity type, relationships or tests remain. The architecture does not add AI, agents, cloud service layers, external notification channels or autonomous external side effects.

The protected built-in Birthdays Calendar is the exception to ordinary Calendar creation: each Person birthday synchronises to a linked canonical yearly all-day Event, and its defaults are configured as a Calendar Event policy. It cannot receive ordinary Events or become the ordinary Event default.

Calendar interchange preserves an explicit ownership boundary. Uploading an iCalendar file is a one-time, previewed and confirmed operation that creates canonical local Events through the existing Calendar/Event/recurrence services. Adding a public HTTPS address creates a renewable read-only subscription instead: configuration and parsed last-known-good items live in operational cache tables, remain outside canonical `calendars`, `entities` and `events`, and are projected only under Other calendars. The settings shell mirrors that distinction through **Settings for my calendars** and **Settings for other calendars**; each URL Calendar can edit its local name, colour, IANA timezone and notification defaults but has no default Event duration or item-level mutation controls. Its Calendar-level reminder policy may create local Inbox attention from stable cached occurrence identity without converting the source item into a canonical Event. Calendar ZIP export serializes selected local sources and selected cached external sources without mutating either or fetching from the network. This interoperability surface is separate from whole-platform portability.

These are current-phase boundaries. The architecture should not prematurely implement future AI or agent layers, but should continue strengthening the shared platform capabilities they would eventually consume: deterministic rules, validation, relationships, provenance, audit history, data quality and safe domain operations. SQLite remains the canonical source of truth.

The current deployment is for one private user without authentication. Future trusted multi-user support is not in Phase 1, but domain and audit design should avoid unnecessary assumptions that would prevent later identity, attribution or permission boundaries.

The application should not depend on WAN access for normal operation. Optional network aids must leave core records and workflows usable without them.

## Entity Architecture

Current domains inherit from a common entity architecture:

- `EntityDefinition` describes each domain type, route slug, table, domain-specific fields and strong fields used for duplicate warnings.
- `FieldDefinition` describes reusable field metadata, including overview visibility, optional on-demand form presentation, optional compound grouping, input type, structured value kind and storage strategy. Scalar fields use typed-table columns; reference-backed, measurement-backed and alias fields use normalized external stores. Optional details render inline in definition order, remain visible when populated, and may be hidden without clearing their values. These flags are presentation metadata, not user-defined schema.
- `EntityRecord` is the shared runtime model for all entity instances.
- Shared active fields are `display_name`, `notes`, `created_at` and `updated_at`. For People, `display_name` is internal derived data generated from `given_name` plus `family_name`; it is not a separate user-entered field.
- `summary` remains in the shared table only as legacy storage/search fallback. It is not exposed on entity creation or edit forms.
- Domain-specific data is exposed as metadata on the same record object.
- Entity profile pages are generated from entity definitions and shared page sections.

People, Organisations, Locations, Projects, Documents and Assets all use this structure.

`app/reference_data.py` provides a platform catalogue of typed, stable reference items and ordered entity-to-item links. Languages and countries/regions are generated into `app/reference_catalogue.py` from a pinned IANA Language Subtag Registry snapshot by `tools/update_reference_catalogue.py`; runtime use remains fully local and dependency-free. Other reference types retain intentionally small demonstrative seeds. `app/units.py` extends measurement-unit reference items with category, symbol, canonical designation and affine conversion parameters. Entity measurements store a canonical value plus the selected display unit, keeping persistence independent from presentation. New reference types, items and measurement categories do not require entity-specific tables or form code.

The ethnicity catalogue is independently generated into `app/ethnicity_catalogue.py` from the 276 detailed groups in the Australian Bureau of Statistics ASCCEG 2025 Table 1.3. It uses the same generic entity-reference links and searchable multi-value control as languages and nationalities. The classification is an Australian-context selection aid, not an inference mechanism or an assertion that identity can be derived from nationality, language or relationships.

Architectural correction: typed tables now receive missing definition-driven columns during schema initialisation. The central `entities.type` SQLite `CHECK` constraint is also rebuilt when entity definitions add new types. Field renames use `FieldDefinition.previous_names` so data from old columns can be copied into renamed active columns without deleting the legacy column. Controlled fields can use value aliases to clean up legacy values such as lowercase statuses. This prevents future entity field or domain additions from breaking existing local databases.

## Entity Page Architecture

Entity pages are primary views over canonical records. `entity_detail_page()` retains one stable facade and shared frame, then delegates the Overview composition by domain: Person contact and relationship-derived locations; Organisation classification/contact/location; Location address/coordinates; Project status/milestones; Document safe file actions and document facts; and Asset identity/status/value/location.

Every entity detail page shares breadcrumbs, identity, Edit/Delete, grouped Views, restrained overflow actions, interpretation warnings, a concise relationship summary, linked Documents and derived real-world Timeline. Routine IDs, timestamps, storage metadata, full change history and duplicated related-record groups do not appear on Overview; the System Audit is the administrative lens. Person Journal remains the deliberate domain exception. Future domains add an `EntityDefinition` and an explicit Overview strategy rather than inheriting an undifferentiated field dump.

Entity deletion uses focused repository persistence coordinated by the shared entity-lifecycle service. Normal entity hydration excludes rows with `deleted_at`; because relationship records resolve both endpoints through that same boundary, deleted entities and their relationships disappear consistently from profiles, global relationship views, search, maps and derived navigation. The lifecycle service also synchronises birthday Events, resolves obsolete Inbox attention and recomputes family inferences where applicable, without introducing repository-to-service import cycles. The Recycle Bin is the sole opt-in deleted-record view. Restore clears one entity's deleted state while leaving other deleted endpoints untouched. Permanent deletion is a separate confirmed action that previews active relationships, recycled relationships and journal dependencies, creates a local recovery bundle, then cascades removal; audit history remains append-only.

`JournalEntry` and `app/journal_repository.py` use a reusable entity type/ID association, but the current HTTP surface deliberately exposes journals only below Person routes. Archived entries remain stored but are omitted from the active stream. Journal entries are separate operational notes and are not folded into the derived real-world timeline.

Journals are expected to become platform-wide later, with first-class entries linked to entities rather than embedded entity data. This milestone does not generalise the UI. Journals remain internal observations, history, maintenance, progress and notes; Documents remain real-world physical or digital artefacts.

## Relationship Architecture

Relationships are a central application model:

- `RelationshipRecord` links two `EntityRecord` instances, so endpoints can be any current or future entity type.
- `RelationshipType` is hydrated from database-backed relationship taxonomy definitions. The code catalogue seeds fresh databases and provides legacy compatibility rather than being the canonical runtime store.
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
- Document issuer/creator semantics are relationship-only. Existing relationship types distinguish creator and issuer endpoints; no scalar issuer/creator field remains and no entity is inferred from old text.
- Document purpose describes the record; MIME type and stored file metadata describe format.
- Uploaded files are stored locally under `instance/documents/`.
- File metadata such as original file name, MIME type, stored path and file size lives on the Document entity.
- Documents link to People, Organisations, Locations, Projects, Assets or other Documents through relationships.
- Assets are things and Documents are records. Neither domain contains a compatibility type that overlaps the other.

Older local databases may still contain an unused `attachments` table. It is no longer created or rendered by the active application because file-bearing records should be Documents.

## Current Domain Deferrals

This milestone does not redesign Locations, migrate Location countries or provenance, integrate G-NAF, expand contact methods, redesign Asset value/currency, add currency conversion, or broaden taxonomies beyond the relationship work required here. Revisit these only when a concrete workflow needs the additional structure. Journal generalisation is separately described above and remains unimplemented.

## Documentation Rule

Documentation is part of each feature, behaviour, workflow, schema and architecture change. Contributors must audit and update every affected planning/reference document, including feature status, roadmap, architecture, database design, ontology/glossary, UI workflow and build log where relevant. Commit messages describe the delivered change without agent, model or tool attribution.

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

`app/entity_merge.py` provides a reusable same-type preview-and-commit workflow. A merge is transactional: compatible blank fields are filled, notes are combined, active and recycled relationships are repointed, duplicate/self relationships are removed only after their counts are previewed, and the retired record plus conflicts and relationship snapshots are retained in append-only edit and platform audit history. A recovery bundle is created before the transaction. Normal entity edits also add history events.

Structured search filters are registry-driven in `app/structured_filters.py`. Each filter declares its key, label, applicable entity types, optional input and predicate; search applies the registry after shared text/type/favourite filtering. New filters should extend this registry rather than add route-specific query logic.


## Deterministic relationship inference

Family inference is implemented in `app/relationship_inference.py` as a reusable rule engine. Rules consume active person-to-person facts and return neutral, canonical candidates plus supporting relationship IDs. The initial rules cover grandparent/grandchild, full sibling, aunt/uncle and niece/nephew, and cousin. Parent/child remains manually entered source evidence. Full-sibling inference requires the same complete known parent set with at least two parents, so half relationships are not inferred accidentally.

Inference is local, deterministic and explainable; it does not use AI or autonomous automation. Mutation hooks rerun the engine after relationship changes and relevant person date changes, but no candidate becomes a relationship without explicit confirmation in the Inference Review Queue. For direct-generation relationships (parent/child and grandparent/grandchild), the younger person's DOB alone can establish the relationship start; an older person's DOB alone cannot. For sibling, partner, aunt/uncle, cousin, and other peer or collateral relationships, both people must have DOBs and the chronologically lower DOB is used. Candidates are fingerprinted from their rule, inferred date, and exact supporting rows, so a later DOB change is material evidence and may produce a new pending suggestion. Enriching the date of an already-confirmed relationship can be added later as a separate review rule. Manual records win conflicts. Self links, ancestry conflicts, duplicates, and cycles are filtered or rejected.

Candidates enter an Inference Review Queue rather than the active relationship set. A batch groups suggestions created by one recomputation trigger and presents one pending card at a time. It is archived automatically after its final decision; historic batches retain per-decision undo controls that reopen review. Confirmation creates a normal, user-owned relationship that is editable and deletable like a manually entered row. Dedicated audit fields retain its inference origin, source batch, rule, supporting relationship IDs, evidence fingerprint, and timestamps. Rejection stores the reviewed fingerprint as a suppression record. Changed or removed evidence invalidates pending suggestions, but confirmed relationships remain active and receive a non-blocking `changed` evidence-health flag. Confirmation triggers a fresh recomputation and any ripple suggestions go into a new batch.

## Derived platform services

`audit`, `query_engine`, `data_quality`, and `timeline` are independent reusable services. Registries allow domain rules and derivations to be added without changing their cores. Audit history records system mutations; timelines derive real-world events only. The timeline date-field registry feeds both record-local timelines and a de-duplicated Universal Timeline; derived events retain canonical origin links and associated entity IDs for direct-relation filtering without storing duplicate event rows. Data-quality findings and search results are derived views over canonical entities and relationships.

Record-derived Calendar and reminder behaviour follows one implemented provider boundary in `app/temporal_occurrences.py`. It adapts canonical Events, protected Birthday Events, cached URL Calendar items and derived Document expiries into stable, traceable occurrences carrying source/context identity, due and end boundaries, destination semantics and persistent/transient behaviour. Calendar consumes projection-eligible Event sources and reminder evaluation consumes reminder-eligible occurrences from the same boundary; Document expiry deliberately remains Calendar-hidden until that workflow is separately designed. The source record continues to own the date, and a source becomes a canonical Event only when its product model deliberately requires Event identity and lifecycle. New sources must add a provider rather than a parallel scheduler, reminder scanner or Inbox-delivery implementation. Future non-temporal approvals and system failures would retain separate operational semantics and do not pass through the temporal pipeline; neither general approval infrastructure nor System Health is delivered here.

## Platform maturity boundary

Phase 1's information model and main human-facing platform are complete as a development milestone. Phase 2's original foundation is complete and its expanded workspace remains active. `app/temporal.py` owns IANA-timezone wall-time normalization, precise UTC instants and end-exclusive all-day intervals. `app/timezones.py` supplies locally derived IANA timezone-picker metadata from the installed timezone database; `app/view_pages/timezones.py` renders the shared collapsed combobox for Calendar and Event forms. It visibly defaults to `Australia/Brisbane` and reveals its searchable, scrollable choices only when opened or edited. It stores only the selected IANA identifier, not a display label or offset. `app/calendar_service.py` owns Calendar validation, configuration changes, active-default safeguards, archive lifecycle, append-only Calendar history, audit and provenance. Local Calendars are the sole canonical Event grouping/configuration records and own Event colour, default timezone, default duration, ordering, archive state and local Event-notification policy. Calendar editing uses a compact circular colour control and keeps repeatable notification rows beside the Calendar defaults in the dedicated Calendar Settings workspace. URL Calendar configuration is operational rather than canonical but reuses the applicable name, colour, timezone and notification controls; it omits default Event duration because its source owns every schedule. Each notification row is an integer plus a unit, capped at ten Calendar defaults and ten effective Event notifications; reminder services persist canonical validated tokens rather than parsing comma-separated text. The notification creator has no policy-state picker: empty Calendar rows inherit platform Event defaults, while canonical Events with no specific rows inherit their linked local Calendar defaults. `app/event_service.py` owns canonical Event validation, persistence, detail edits, dedicated cancellation/reinstatement/rescheduling, and archive operations over shared `entities` identity and Event-specific storage. Calendar archival retains Event assignments, while explicit Event editing is the only current reassignment path; empty non-default Calendars alone can be permanently deleted. Event is registered as a canonical type for schema integrity, portability and standard relationships, but remains outside generic browsing and creation because human-created Events originate in the `/calendar` workflow. `app/view_pages/calendar.py` renders dedicated Calendar Event forms, the settings navigation and Calendar configuration forms, compact Event previews, Calendar-only header navigation, collapsible Calendar groups, and deterministic Month, Monday-first Week and Day projections. Each enabled local or URL Calendar row provides a direct, context-preserving shortcut to its applicable Calendar Settings editor. `app/view_pages/layout.py` supplies standard Browse, Calendar and stripped-back Calendar Settings shell variants behind the stable view facade. The settings shell omits Project E/global navigation, retains only a context-preserving Calendar return in its header, and keeps local creation/editing functional. General and Calendar discovery remain presentation-only; Import, Export and From URL provide preview-first iCalendar interchange and read-only public subscription workflows. The Calendar shell gives its sidebar an independent scroll boundary, supports accessible drag-only ordering within the separate local and external ownership groups, and fits the complete Month grid plus its ISO week-number rail into the remaining fixed viewport; Week and Day retain their own two-axis scroll region and show an adjacent ISO week companion. The route uses the active default Calendar timezone as the current display timezone; Week and Day draw timed intervals as hourly-grid duration blocks, clip overnight spans into each display day, and place a client-updated current-time line on the present display-timezone day, while Calendar visibility filters alter the projection only. `app/event_recurrence.py` stores versioned series definitions, derives bounded Event occurrences at read time, applies persisted cancellation and override exceptions, and creates traceable successor series for prospective changes without duplicate occurrences. Calendar previews preserve an occurrence identity for the Event editor and deletion flow; their this-occurrence, this-and-following and all-occurrences mutations are recorded in Event history, audit and provenance. The HTTP handler routes forms through `create_event`, `update_event`, `reschedule_event` and the standard Recycle Bin lifecycle, while relationship entry remains the shared Relationship workflow. Global Search and existing relationship links open read-only Event projections with Calendar-derived colour, temporal/lifecycle facts, relationships and change history. The relationship catalogue connects Events to every current canonical peer type using the normal recoverable relationship lifecycle. Phase 2A is complete.

Phases 2B–2F extended that foundation. `app/reminder_service.py` resolves policy defaults and overrides over the shared occurrence providers, selects only the latest due configured timing, reconciles visible attention and materialises durable delivery history. Birthday Calendar Events inherit the Birthday timing defaults when no explicit Calendar policy exists, including calendar-month leads. `app/inbox_repository.py` owns reusable delivery-state transitions and lifecycle resolution, allowing Event, recurrence, subscription and entity services to suppress obsolete attention without importing the cross-domain reminder projector back into themselves. Stable negative source identifiers distinguish external cached items from canonical Event identifiers while their source-scoped UIDs retain identity across refresh. `app/view_pages/inbox.py` renders the chronological reminder queue plus archive and deep history; `inbox_items` retains the current projection and occurrence-end boundary while append-only `inbox_item_actions` retains each delivery and transition. Exact-occurrence open clears Event attention but not persistent Document-expiry attention. `app/view_pages/layout.py` renders the initial active reminder count and `inbox-count.js` refreshes the read-only count projection while visible. `app/scheduler_service.py` provides the replaceable in-process scheduler boundary, application-owned handler registry, SQLite job leases, Job Runs and startup/clean-shutdown checkpoints. `app.automation_service.py` is deliberately distinct from Jobs: it persists registered rules and idempotent automation runs, and it calls normal services rather than storing executable code. System Tools exposes scheduler and automation state.

Relationships use the same recoverable lifecycle pattern as entities: `deleted_at` is canonical soft-delete state, active repositories exclude recycled rows by default, and the Recycle Bin restores them. Audit records remain append-only and reference records by kind and identifier even while those records are deleted. The platform-wide System Audit reads the existing audit tables through a small action/record-kind normalization layer; it is a view, not a second event store. Timelines remain derived real-world chronology and intentionally exclude operational mutation events.


## Portability and recovery

`app/portability.py` owns the stable bundle boundary. An export uses SQLite's online backup API to produce a consistent database snapshot, includes every referenced uploaded document, and writes a versioned manifest with SHA-256 checksums and record counts. Import extracts only safe paths into staging, verifies the manifest, checksums, SQLite integrity, foreign keys, migration set, entity typed rows, relationship endpoints/types and document membership, then presents a count preview. Apply is restricted to an empty target and explicit confirmation. Database and document replacements are staged on the local filesystem, an import audit event is appended, and a recovery bundle is created first.

The same recovery bundle primitive runs before confirmed merge and permanent deletion. `tools/restore_backup.py` validates in preview mode by default and requires `--confirm-replace` before restoring a non-empty installation. Bundles, backups and staging files remain under Git-ignored local storage and never become application dependencies.
