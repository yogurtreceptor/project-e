# Architecture

This document describes Project E's current runtime structure and ownership boundaries. Product meaning belongs in [Ontology](ontology.md), persistence details in [Database Design](database_design.md), delivered Phase 2 behaviour in the [Phase 2 record](phase_2_workspace.md), and future direction in the [Roadmap](../ROADMAP.md).

## System shape

Project E is a server-rendered local web application for one private user:

```text
Browser
  ↕ local HTTP
Routing and request handling
  ↕ validated application services
Repositories and derived services
  ↕
SQLite + private local files
```

The runtime uses standard-library Python and embedded SQLite. Core record workflows require no WAN connection. Optional map resources, address lookup and explicitly configured public iCalendar sources sit behind replaceable network boundaries.

`instance/` is the private runtime boundary. It contains the database, uploaded documents, import staging, recovery artifacts, disposable journey cache and replaceable spatial packs and is ignored by Git. A fresh clone creates empty local storage; tracked examples must be deliberately fictional.

## Stable entry points

| Boundary | Owner |
| --- | --- |
| Process and server setup | `run.py`, `app/config.py`, `app/http_server.py` |
| Route selection | `app/web_router.py` |
| Domain request handling | `app/web.py` |
| HTTP/form/response mechanics | `app/web_support.py` |
| Rendering facade | `app/views.py` |
| Focused page rendering | `app/view_pages/` |
| Database facade | `app/db.py` |
| Connections, schema and migrations | `app/db_schema.py` |
| Shared entity definitions | `app/entities.py` |
| Product defaults | `app/defaults.py` |

`app/db.py` and `app/views.py` are stable public facades. New work should keep focused implementation behind them rather than expand them into monoliths.

Styles follow the same pattern: `app/static/styles.css` is an ordered manifest, `foundation.css` owns tokens/themes/global interaction policy, and focused stylesheets own shell, Calendar, component and page-family rules. Small local JavaScript files enhance server-rendered controls without becoming a second application state model.

## Application boundaries

### Canonical entities

`EntityDefinition` and `FieldDefinition` describe each canonical domain, its typed fields, validation and presentation metadata. `EntityRecord` is the shared runtime representation. The current types are Person, Organisation, Location, Project, Document, Asset and Event.

Responsibilities are separated:

- `app/entity_repository.py` reads and writes entity persistence.
- `app/entity_service.py` coordinates lifecycle consequences such as Birthday Event synchronisation, reminder resolution and inference recomputation.
- `app/place_repository.py` owns canonical Location address, geometry and provider-reference persistence; `app/place_service.py` owns the preferred physical-address and representative-point edit projection and merge behaviour.
- `app/map_feature_service.py` owns reviewed external-feature promotion, duplicate evidence, portable Map-list membership and its recovery validation. Browsing remains a read projection; only the dedicated review/list actions mutate durable state.
- Focused modules own external field stores: aliases, reference values, measurements and journal entries.
- `app/duplicate_detection.py`, `app/entity_merge.py` and `app/integrity.py` provide reviewable maintenance instead of hidden automatic mutation.

Entity pages share one frame but use explicit domain compositions. The Overview is a human record view, not a dump of every stored column; audit history and storage metadata belong in administrative views.

### Relationships

Relationships are first-class rows between any two canonical entities. `app/relationship_repository.py` owns persistence, `app/relationships.py` is the selection/label facade, and `app/relationship_catalog.py` seeds definitions and legacy mappings. Runtime definitions are taxonomy-backed and encode valid endpoint pairs, canonical direction and inverse labels. Active `contains_location` Relationships form a single-parent, cycle-safe Location hierarchy; address inheritance is a display projection and never copied truth.

The UI asks for the connected entity's role from the current entity's perspective; saving normalises that choice into one canonical row. Reverse navigation is derived, never stored as a duplicate inverse Relationship.

Family graphs remain projections over the same records. `app/relationship_graph.py` extracts a canonical graph; `app/graph_layout.py` performs deterministic family-tree layout; rendering adds no graph persistence and infers no missing family facts.

### Documents and local files

Documents are canonical entities; uploaded files are private local resources they reference. `app/document_storage.py` owns safe paths and writes. `app/document_lifecycle.py` deletes only confined, unreferenced files after database state is safe. Replacing, recycling and permanently deleting a Document follow different cleanup rules.

### Time and attention

The temporal stack is intentionally layered:

```text
Canonical source facts
  → Event/record occurrence adapters
  → Calendar projection and reminder evaluation
  → durable Inbox attention
  → registered scheduled execution
```

- `app/temporal.py` owns timezone and interval semantics.
- `app/calendar_service.py` owns local Calendar configuration and lifecycle.
- `app/event_service.py` owns canonical Event writes; `app/event_recurrence.py` owns deterministic series and exceptions.
- `app/temporal_occurrences.py` adapts eligible sources into stable occurrences. New temporal sources extend this provider boundary rather than add a separate scanner or delivery path.
- `app/reminder_service.py` resolves policies and materialises attention; `app/inbox_repository.py` owns reusable state transitions.
- `app/scheduler_service.py` owns registered Jobs, leases, runs and startup recovery.
- `app/automation_service.py` owns deterministic registered trigger/action rules and separate Automation Runs.

Jobs, Automation Runs, Inbox items, audit events and canonical Events retain separate identities. Database rows select only registered handlers/actions and never contain executable user code. Current automation evaluates reminders and cannot mutate a canonical Event.

### Calendar interchange

`app/icalendar_service.py` owns bounded parsing, preview-first file import and selected Calendar ZIP export. Confirmed import uses normal Calendar, Event and recurrence services to create canonical local records.

`app/calendar_subscription_service.py` owns safe public-HTTPS sources. Subscription configuration and a last-known-good cache are operational local state, not canonical Calendars or Events. Calendar projection can display cached items and reminder evaluation can create local attention, but external items remain read-only and receive no Relationships or entity lifecycle.

### Journey foundation

`app/journey_contract.py` owns provider-independent endpoint, capability—including static/live transit input—request, normalized stage/result, provenance, explanation, failure and full-dependency fingerprint types. `app/journey_service.py` resolves deliberate current Location route-anchor/entrance/representative-point geometry, refuses unsupported requirements before an adapter call and validates every result afterward. Adapters are replaceable calculators: they cannot own mobility profiles, routing policies, canonical geometry or silently omit a requested requirement.

`app/journey_repository.py` owns audited user configuration identity and revisions for mobility profiles and routing policies. Their exact production values and provider translations remain later implementation evidence work. `app/journey_cache.py` stores only bounded disposable results in a separate ignored SQLite file; fresh, stale and miss are explicit, invalid cache payloads are discarded and clearing it loses no personal configuration. X1 identified capability-specific routing front-runners, but no current journey operation calls one, creates Events or adopts a production provider.

### Installed spatial packs

`app/spatial_pack.py` owns the non-canonical regional resource boundary. Spatial-pack schema version 1 is an exact bounded ZIP containing `manifest.json`, vector `basemap.mbtiles`, read-only `search.sqlite3` and `coverage.geojson`. Inspection validates safe paths and membership, sizes and SHA-256 digests, disk reserve, SQLite identities/integrity/schema, declared zoom/bounds and coverage geometry before anything can activate. Validated immutable versions live under ignored `instance/spatial-packs/`; a small atomically replaced `active.json` selects one active region and names one previous validated version for rollback. Activation, rollback and confirmed removal are audited, but no pack row or byte is canonical or portable.

MapLibre GL JS 6.2.0 is vendored under `app/static/vendor/` with its licence and exact X1 artifact identity. It reads only same-origin immutable tile, coverage and static-transit endpoints. The Gold Coast pack's fixed SQLite index is derived from visible OSM vector labels and static GTFS stops; it is not full geocoding, provider identity or canonical place storage. Pack search failure leaves canonical search available, renderer/tile failure leaves the N2 coordinate grid/DOM overlay available, and coordinates outside declared coverage remain renderable. This first lifecycle deliberately allows one active region; N5/N6 evidence must justify adjoining-region or routing-source generalisation.

### Reviewed provider features and Map lists

Installed search, rendered pack context and explicitly requested Nominatim results share one selection-details contract. **Save as Location** first revalidates the provider/active-pack boundary, then presents exact provider-reference, normalized name/address and 100-metre representative-point matches. Confirmation either creates one canonical Location with source-qualified assertions and a neutral provider reference or attaches only the reference to a reviewed existing Location. It never updates an existing canonical name, address or geometry.

`map_feature_lists` and `map_feature_list_memberships` are durable user-owned spatial state rather than entities or provider cache. A membership stores its list, provider key, feature identity and user-owned label; it deliberately omits provider version, coordinates and pack facts. `app/spatial_pack.py` may resolve current facts from the active replaceable index for display. Missing packs and changed/disappeared feature identities leave membership intact and visibly unavailable; they are never silently reassigned. Online membership revisit requires an explicit provider search. Named-list JSON export and whole-platform recovery carry membership independently of pack bytes.

### Derived platform services

Search, structured filters, timelines, maps, data quality and audit are projections over canonical data:

- `app/discovery_repository.py`, `app/query_engine.py` and `app/structured_filters.py` own retrieval.
- `app/timeline.py` derives real-world chronology; operational audit events do not become Timeline events.
- `app/geo.py` groups canonical Map places from each Location's preferred current representative point, qualifying Relationships and current Asset coordinates; it also owns deterministic canonical-first Map search, installed-pack result composition and the bounded local viewport read model. `app/static/map-workspace.js` composes the accessible canonical DOM overlay/text alternative with the optional vendored same-origin normal map. No page resource requires a CDN or automatic WAN request. Browsing owns no records; explicit reviewed promotion and list commands cross into `app/map_feature_service.py`.
- `app/data_quality.py` and `app/integrity.py` report deterministic findings.
- `app/audit.py` reads append-only operational history.

Registries are used where domains contribute rules or projections. They avoid route-specific branches while keeping each derived result traceable to its canonical source.

## Lifecycle and safety

Consequential writes pass through validated services and produce the applicable history, audit and provenance records. Entities and Relationships use timestamped soft deletion; ordinary repositories hide recycled records. Restore keeps canonical identity. Permanent entity deletion and duplicate merge are confirmed, previewed and preceded by a recovery bundle.

Deterministic recomputation may update derived state or create contracted operational history. It does not silently create user-owned Relationships: family inference produces review suggestions, and confirmation creates an ordinary editable Relationship. Rejected evidence is remembered; changed evidence invalidates pending suggestions without deleting confirmed facts.

Whole-platform portability is owned by `app/portability.py`. It validates a versioned SQLite-and-document bundle, including canonical place, journey configuration and portable Map-list state, requires an empty target and explicit confirmation, and creates recovery state before replacement. Disposable journey cache and replaceable spatial-pack data are excluded.

## Deployment and maturity boundary

The application currently has no authentication, multi-user model, external worker, queue or cloud dependency. Normal operation remains local and in-process. Optional network clients must fail without damaging or blocking canonical local data.

Phases 1 and 2 are complete development milestones. Phase 3 N1–N4 and N5A have added the canonical place foundation, offline-first Map 2.0 workspace, provider-independent journey/profile/policy/cache seam, one verified installed Gold Coast normal map/search/context pack, reviewed provider promotion and portable external Map lists. N5 coverage recommendations, a production routing provider, calculated journeys, Calendar materialisation and later spatial work remain separately gated. Mobile access, multi-user permissions, autonomous external effects and AI/agent layers require separate authorisation. Any future consumer—human interface, deterministic integration or bounded AI capability—must use the same canonical data, validation, audit, provenance and recovery boundaries.
