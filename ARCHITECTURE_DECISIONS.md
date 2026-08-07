# Architecture Decisions

This file preserves long-term structural choices and their rationale. Search its headings by topic or ADR number rather than loading it for current implementation detail; current contracts live in the focused reference documents.

New decisions are appended with Status, Date, Decision, Reason and Consequences. Do not record small implementation choices. If replaced, retain the old entry as Superseded and append its replacement.

The current groups are foundational entity/persistence choices (ADR-001–010), Operational Time and automation (ADR-011–026), Task retirement (ADR-027), the shared temporal-occurrence boundary (ADR-028), canonical place assertions (ADR-029), the offline-first Map workspace seam (ADR-030) and the provider-independent journey seam (ADR-031).

## ADR-001: Map as an entity view

Status: Accepted

Date: 2026-06-21

Decision:
The map is a view over canonical entities and relationships. Location entities own address and coordinate data; People and Organisations connect to Locations with `located_at` relationships instead of duplicating address fields.

Reason:
Project E is entity-first and relationship-first. A separate map data store would create duplicate records, make address quality harder to maintain and make future layers harder to extend consistently.

Consequences:
The initial map can display Locations, Organisations and People through the same entity graph. Future geographic layers must derive markers from canonical records or relationships. Organisation address columns from earlier local schemas are ignored by the active model rather than extended.

## ADR-002: Treat G-NAF as an optional future address index

Status: Accepted

Date: 2026-06-21

Decision:
Project E will keep OpenStreetMap Nominatim as the current lightweight address lookup fallback and treat Australia's Geocoded National Address File (G-NAF) as an optional future local address index for higher-accuracy Australian house-level geocoding.

Reason:
Most expected addresses are Australian, and G-NAF is the strongest fit for house-level Australian address coordinates. However, the dataset is large and should not become a mandatory Phase 1 dependency or be imported directly into the main application database before the address-index workflow is deliberately designed.

Consequences:
Location creation can continue with Nominatim, manual coordinate editing and external lookup when needed. Future G-NAF support should be implemented as a separate local data pack or plugin-style index, with written setup instructions and a compact derived SQLite search database. The main entity database should store only selected Location entity data, not the full G-NAF dataset. The address lookup UI may later offer a fallback action such as "Can't find what you're looking for? Search with OpenStreetMap" when a local G-NAF index is installed but does not find a match.

## ADR-003: Add Projects, Documents and Assets as normal entity domains

Status: Accepted

Date: 2026-06-21

Decision:
Projects, Documents and Assets are implemented through the shared entity, relationship, search, dashboard and detail-page architecture. Documents are first-class entities with local file metadata and upload storage. Assets can participate in the map layer when they have valid direct coordinates or a `located_at` relationship to a coordinate-bearing Location. Projects and Documents do not appear as map markers.

Reason:
The milestone is intended to prove that Project E's entity architecture scales beyond People, Organisations and Locations. Reusing `EntityDefinition`, typed tables and central relationships avoids one-off page models and keeps the platform relationship-first.

Consequences:
Existing local databases need the central `entities.type` constraint to evolve when new domains are introduced, so startup now rebuilds that table constraint when required. The old attachment concept is no longer part of the active architecture; file-bearing records should be Document entities linked through relationships.


## ADR-004: Track schema migrations while retaining additive repair

Status: Accepted

Date: 2026-06-28

Decision:
Record ordered, append-only migration identifiers and application timestamps in a local `schema_migrations` table. Continue running the idempotent current-schema repair pass at startup.

Reason:
Local databases need an auditable history for future schema changes, but Project E also relies on definition-driven additive repair to adopt older databases and safely add fields or entity types. A ledger alone would not cover those evolving definitions.

Consequences:
Future explicit schema changes append a uniquely named migration. During active development, obsolete fields and identifiers may be deliberately removed when that produces the cleaner current model; migrate when practical and accept a development database reset when necessary. Compatibility layers become a priority after a stable release. Startup retains repeated schema inspection for safe additive evolution and recovery.


## ADR-005: Review deterministic relationship inference before creation

Status: Accepted

Date: 2026-06-28

Decision:
Implement family inference as a reusable deterministic rule engine over canonical Person relationships. Inferred candidates are review suggestions, not relationship records. Confirmation creates a normal editable relationship with provenance; rejection suppresses the unchanged evidence fingerprint. Completed batches archive automatically with searchable history and undo.

Reason:
Safe bloodline facts can be derived consistently from manual parent/child evidence, but derived data must remain explainable and under user control. Keeping suggestions outside the relationship table prevents silent graph mutation while provenance and suppression make reviews repeatable.

Consequences:
Initial rules are limited to grandparent/grandchild, full sibling, aunt/uncle with niece/nephew, and cousin. Half, step, adoptive, foster, guardian, in-law and partner inference remain excluded. Confirmed relationships are editable and are not deleted when original evidence changes; their evidence health is flagged instead. Rule, source relationship IDs, source batch, fingerprint and timestamps remain auditable.

## ADR-006: Distinguish deterministic assistance from autonomous automation

Status: Accepted

Date: 2026-06-28

Decision:
Phase 1 may use deterministic, local and explainable assistance or internal maintenance when it preserves user control. A capability is inside the Phase 1 boundary when its behaviour is rule-based and auditable, requires explicit confirmation before a consequential mutation, performs no scheduled or autonomous goal-directed workflow, creates no autonomous external side effect, and does not require WAN access for core operation. Capabilities that cross these tests require explicit scope approval.

Reason:
Useful information-management behaviour often performs work automatically without becoming autonomous automation. Treating every derived value, warning or housekeeping action as prohibited would conflict with the implemented platform and obscure the actual safety boundary: whether the system acts consequentially or externally without the user's informed control.

Consequences:
Deterministic relationship inference, duplicate warnings, derived views, automatic display-name maintenance and review-batch archival remain valid Phase 1 behaviour. Inference may recompute candidates automatically, but a candidate cannot become a canonical relationship until the user confirms it. AI, decision support, scheduling, autonomous goal-directed workflows, unreviewed consequential actions and autonomous external side effects remain outside Phase 1. Optional network aids remain acceptable only when core records and workflows work without them.

## ADR-007: Separate taxonomy hierarchy from domain behavior

Status: Accepted

Date: 2026-07-04

Decision:
Store reusable classifications in a shared database-backed hierarchy capped at Type, Subtype and Specific subtype. Domain records reference one terminal entry representing the complete path. Keep relationship endpoint constraints, direction and inverse labels in a relationship-specific definition table rather than expanding the generic hierarchy into an ontology engine.

Reason:
Organisation and relationship classifications need the same path, search, reuse and archive behavior, while only relationships require directional semantics. Separating these concerns keeps the taxonomy reusable and the relationship model explicit.

Consequences:
Organisation and relationship rows gain taxonomy foreign keys. Legacy Organisation text and relationship keys remain compatibility snapshots during migration. Archived branches remain readable but unavailable for new selection. Other Phase 1 type systems are unchanged until separately authorised.

## ADR-008: Keep document semantics relational and separate records from things

Status: Accepted

Date: 2026-07-05

Decision:
Document purpose describes the real-world record; stored MIME metadata describes file format. Issuer and creator are relationships to canonical People or Organisations, not Document text. Assets represent things and Documents represent records. Organisation alternate names use normalized repeatable alias rows.

Consequences:
The obsolete Document issuer column, format-like purpose choices and Document-like Asset choice are removed. Existing issuer text is not used to infer entities. Organisation aliases are searchable, merge-safe and participate in duplicate review.

## ADR-009: Separate operational audit from real-world timeline events

Status: Accepted

Date: 2026-07-05

Decision:
Use the append-only generic audit tables as the platform-wide operational event source. New entity, relationship and taxonomy mutations use normalized action types and typed record references. System Tools → Audit filters that source without creating a reporting store. Real-world dates continue to derive into timelines from canonical entity and relationship data.

Reason:
Operational changes and facts about the outside world have different meaning, retention and filtering needs. A second audit store or timeline-shaped mutation model would duplicate the database source of truth.

Consequences:
Legacy `relationship_change` rows remain readable through a small presentation normalization layer. Deleted relationships retain their canonical row and audit references, disappear from active timeline derivation, and reappear with their original real-world dates after restoration. Future operational capabilities extend the audit vocabulary and record references rather than redesigning the page.


## ADR-010: Use validated snapshot bundles for Phase 1 portability and recovery

Status: Accepted

Date: 2026-07-05

Decision:
Use a versioned, checksummed ZIP containing a consistent SQLite backup plus referenced uploaded documents as the Phase 1 export and recovery format. Validate the manifest, every member checksum, current schema/migrations, SQLite integrity, foreign keys, canonical entity/relationship structure and document membership before preview or apply. Normal import applies only to an empty target after explicit confirmation; recovery replacement remains a separately confirmed maintenance command.

Reason:
The SQLite database already contains the canonical graph, custom taxonomies, normalized measurements/references, provenance and append-only audit history. Re-serializing a subset into a parallel interchange model would risk semantic loss and duplicate sources of truth. SQLite's standard-library backup API provides a consistent local snapshot without a new dependency.

Consequences:
Exports are complete local snapshots rather than partial CSV-style ingestion. Bundle format changes require a versioned migration policy. Imported identities, audit and provenance are preserved; a new import audit event records ownership transfer into the local installation. Import, merge and permanent deletion create Git-ignored recovery bundles first. Conflict-aware import into a populated database remains out of Phase 1 scope.

## ADR-011: Treat Events and Tasks as first-class peer entities

Status: Superseded by ADR-027

Date: 2026-07-11

Decision:
Phase 2 will add Events and Tasks as canonical peer entities using the shared entity lifecycle and relationship system. Projects coordinate them but do not own them.

Reason:
Time occurrences and work require stable identity, history, search and cross-domain relationships without creating special nested models.

Consequences:
Event and Task links to Projects, each other and other domains use normal relationships; neither an event-task type nor per-domain link columns are the default model.

## ADR-012: Keep the Calendar a projection over canonical time information

Status: Accepted; Task-specific consequences superseded by ADR-027

Date: 2026-07-11

Decision:
Calendar views derive from canonical records and traceable derived occurrences; they do not maintain a duplicate event store.

Reason:
One source of truth preserves lifecycle, audit and relationship semantics across Events, Tasks and other dated records.

Consequences:
Displaying a deadline, birthday or scheduled run does not change its source type. Shared temporal semantics precede calendar implementation.

## ADR-013: Model reminders as policies and deliveries, not standalone domain entities

Status: Accepted; Task-specific consequences superseded by ADR-027

Date: 2026-07-11

Decision:
Reminders are attached policies, with global defaults and entity-level overrides. Deterministically derived occurrences remain traceable to source facts; delivery, acknowledgement and snooze history are separate notification records.

Reason:
This avoids annual duplicate reminder definitions while allowing meaningful user control and delivery audit.

Consequences:
An Event or Task is not a Reminder. Birthdays and expiries can use policy-driven occurrences without becoming independent canonical reminder records.

## ADR-014: Separate actionable notifications from persistent issues

Status: Accepted separation; Persistent System Health implementation deferred

Date: 2026-07-11

Decision:
The Inbox holds actionable notifications. If Persistent System Health is separately authorised later, its conditions must use durable current issue records rather than masquerading as Inbox reminders; issue deduplication and escalation behaviour are not delivered Phase 2 contracts.

Reason:
An unchanged condition is not a new event every day, and repeated noise obscures useful attention.

Consequences:
Notifications, audit events, Job Runs and Automation Runs remain distinct delivered record types and audit trails. Persistent issues remain a deferred, separately designed record type.

## ADR-015: Separate scheduled jobs from calendar events and restrict handlers

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Scheduled jobs use database-backed schedules, registered handlers and persistent run history. Calendar display of a run is optional projection only; database-stored executable code is prohibited.

Reason:
Background execution has recovery, retry, concurrency and failure semantics that Events do not have, while registered capabilities preserve safety and maintainability.

Consequences:
The initial local scheduler avoids distributed queues, Redis, Celery and Temporal unless later evidence requires them.

## ADR-016: Establish deterministic automation before AI automation

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Phase 2 automation uses explicit trigger-condition-action rules and calls ordinary application services with normal validation, provenance and audit. AI automation is deferred.

Reason:
Deterministic rules establish useful, explainable operational behaviour before introducing model uncertainty or agency.

Consequences:
The delivered registered action is non-consequential and cannot mutate canonical Events. Any future consequential action requires separately authorised review infrastructure; no AI agents or autonomous AI-generated actions are introduced in Phase 2.

## ADR-017: Define Phase 2 completion as integrated operational behaviour

Status: Accepted

Date: 2026-07-11

Decision:
Phase 2 completes only after the delivered Event, Calendar, reminder, Inbox, scheduler, registered deterministic automation, audit, provenance and portability workflow works coherently and passes an end-to-end completion review. The retired Task subsystem remains historical evidence, and Persistent System Health is not a completion requirement.

Reason:
Isolated tables and pages do not prove an operational platform.

Consequences:
The current completion scenario and closeout gate in `docs/phase_2_workspace.md` govern closure review. Superseded delivery records do not restore retired or deferred capabilities to the completion boundary.

## ADR-018: Use a Brisbane platform timezone and deterministic calendar-grade recurrence

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Initial Phase 2 calendars default to `Australia/Brisbane` as their IANA timezone, and individual timed Events may select another IANA timezone. Precise instants use backend-safe UTC storage. Recurrence supports calendar-grade daily, weekly, monthly and yearly intervals, selected weekdays, ordinal weekdays and bounded date ranges; monthly and yearly rules use the selected calendar day and shift backward to the last valid day when that day is unavailable.

Reason:
The current product has one private user in Brisbane, so a single explicit IANA zone supplies clear temporal meaning without premature multi-zone configuration. Deterministic calendar-grade recurrence gives users familiar flexibility while preserving traceable derived occurrences.

Consequences:
Selecting the 29th–31st requires a warning about shorter-period shifting. Derived occurrences remain traceable and do not create duplicate canonical Event records. A later multi-zone design can extend the temporal boundary without changing existing record semantics.

## ADR-019: Deliver initial notifications locally and keep the scheduler separable

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Initial notification delivery creates local actionable inbox items only. Items persist until acted upon; startup creates one deduplicated recovered item for a due reminder or job-triggered notice missed while the application was unavailable. The scheduler runs in-process while the application is running, with schedules, handlers, locking and run history exposed through an application-runtime boundary suitable for a later local worker.

Reason:
This provides reliable local attention management without external delivery dependencies or a second process, while preserving a direct evolution path for continuous local operation.

Consequences:
No email, SMS, push, operating-system notification, service manager or external queue is introduced initially. Recovery preserves the original due time and prevents duplicate delivery; a later worker reuses registered handlers and schedule definitions rather than creating a second scheduling model.

## ADR-020: Keep automatic operations non-consequential

Status: Accepted; current boundary clarified after ADR-027

Date: 2026-07-19

Decision:
Phase 2 automatic operations may evaluate derived state and create or update reminder deliveries, audit records, Job Runs and Automation Runs through registered application handlers. Database rules store registered trigger, action and condition data only, never executable user-authored code. The delivered action cannot create, edit, archive or delete a canonical Event.

Reason:
Operational assistance should be useful and reliable without silently changing the user's canonical commitments.

Consequences:
Automation uses normal application services and retains separate, idempotent run and audit history. General proposal/approval infrastructure is not delivered. Any future consequential automation action requires separately authorised product design and a review boundary before implementation.

## ADR-021: Recover scheduled work serially with per-job catch-up policy

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-19

Decision:
Record clean shutdown and startup when possible, retain a durable scheduler checkpoint, and recover work due during unavailability in scheduled order, one completed run at a time. Each registered job declares whether recovery runs every missed occurrence, coalesces missed work into one current run, or skips stale work.

Reason:
Serial recovery prevents overlapping work, while a declared policy prevents a high-frequency job from replaying days of obsolete checks after downtime.

Consequences:
Recovery remains deterministic and auditable after clean or unclean stops. Job registration, not ad hoc scheduler guessing, owns stale-work behaviour.

## ADR-022: Require bounded timed Events and calendar defaults

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-19

Decision:
A timed Event always has start and end instants; an all-day Event has date boundaries only. Intervals are start-inclusive and end-exclusive. Calendar settings provide overridable defaults for Event duration and reminder preferences.

Reason:
Every timed calendar commitment needs an unambiguous occupied interval, while different calendar contexts have legitimately different typical duration and reminder needs.

Consequences:
The Event form uses its selected calendar's defaults but lets the user override them. Point-in-time timed Events are not part of the initial model.

## ADR-023: Enforce logical idempotency in the database

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-19

Decision:
Stable identities deduplicate logical occurrences, reminder deliveries, recovered notifications, Job Runs and Automation Runs. Database uniqueness constraints and atomic claims protect the corresponding action from concurrent duplicate execution. Each record contract defines material changes that create a new logical item rather than updating the existing one. Deferred persistent issues, escalations and external side effects require their own separately authorised identity contracts if introduced later.

Reason:
In-process execution is not a sufficient duplicate guarantee once recovery, crashes, restarts or later workers are involved.

Consequences:
The scheduler and notification services must claim work transactionally. A recurrence version change is one delivered example of a material change that legitimately produces a new logical record.

## ADR-024: Model calendars as local Event configurations

Status: Superseded by ADR-025

Date: 2026-07-19

Decision:
Calendars are first-class local Event grouping/configuration records, comparable to Google Calendar calendars. Every Event belongs to one calendar, which supplies name, colour, IANA timezone, default Event duration and reminder preferences. Events may override the calendar timezone. Initial Events and Tasks store planned time only; actual start/end tracking is deferred.

Reason:
Calendar-specific defaults support useful personal, work and other contexts without creating a second Event store. Deferring actual time preserves a simple initial temporal model.

Consequences:
The calendar is the source of Event presentation preferences, while Events remain canonical records. Actual-time tracking remains a documented future extension for shifts, travel, maintenance or time-tracking workflows.

## ADR-025: Use Calendars as the sole Event grouping and configuration model

Status: Accepted

Date: 2026-07-19

Decision:
Every canonical Event belongs to exactly one Calendar. Calendars alone provide Event grouping, name, colour, default IANA timezone, default duration, ordering, archive state, filtering and future default reminder policy. A fresh installation has one default General Calendar. There is no separate Event classification or colour-override layer.

Reason:
This matches the intended basic Google Calendar structure and avoids two competing grouping/configuration systems whose colour, defaults, filtering and management semantics would overlap.

Consequences:
Event colour always derives from its Calendar. The category-bearing development schema is removed through a forward-only corrective migration while its historical migration identifiers remain append-only. Archiving a Calendar retains its Event assignments and prevents new selection; it cannot be the active default, and deletion is limited to empty non-default Calendars so no Event is silently reassigned. Future broad reminder precedence is occurrence override, Event override, Calendar policy, then global policy; reminder storage remains deferred to Phase 2C.

## ADR-026: Use semantic Event lifecycle operations

Status: Accepted

Date: 2026-07-19

Decision:
Retain persisted Event status while routing cancellation, reinstatement and rescheduling through dedicated `cancel_event`, `reinstate_event` and `reschedule_event` service operations. Keep Event archive state independent from platform Recycle Bin deletion; restoring a deleted Event preserves its archive and cancellation state.

Reason:
These transitions have distinct temporal and historical meaning and will later affect recurrence and reminder identity. Dedicated operations preserve clear validation, audit and provenance without introducing a separate lifecycle record model.

Consequences:
General Event detail edits do not change schedule or status. Calendar projections can distinguish cancelled, archived and deleted records deterministically. Recycle Bin restoration clears only `entities.deleted_at`.

## ADR-027: Retire the experimental Task subsystem

Status: Accepted

Date: 2026-08-01

Decision:
Remove the unused Task entity type, Task-list/deadline/session tables, Task services and pages, Task relationship taxonomy, Task reminder contexts, Task-only automation actions and proposal storage. Preserve the append-only historical migration ledger, and make the retirement migration refuse to proceed if it finds any Task entity, Task row, Task proposal or Task relationship.

Reason:
The delivered Task model had no canonical user records and did not prove useful. Keeping dormant runtime code, skipped tests and schema created a continuing maintenance burden and repeatedly misrepresented current product scope to contributors and coding agents.

Consequences:
Project E has no current Task or to-do capability. Fresh databases apply the historical migrations and then remove their artifacts, while upgrades with real Task data stop without deleting it. Any future work-management capability begins with a newly authorised product model and forward migration; it is not required to preserve the retired design.

## ADR-028: Route record-derived reminders through one temporal occurrence pipeline

Status: Accepted

Date: 2026-08-01

Decision:
Canonical record dates that need Calendar, reminder or Inbox behaviour must enter one shared temporal-occurrence pipeline. Each source domain adapts its canonical fact into a traceable occurrence contract consumed by shared Calendar projection, reminder-policy resolution, delivery, reconciliation and Inbox services. A Person, Document, Relationship or other source continues to own its date; adapting that date does not require copying it into a canonical Event. Materialising an Event remains a deliberate domain decision for a time record that needs Event identity and lifecycle, as with the protected birthday Event workflow, rather than the default way to gain reminder behaviour.

Reason:
Record-derived reminders are common platform behaviour. Implementing a separate scanner, timing model, delivery path and lifecycle reconciliation for each new dated field would duplicate logic and make Calendar, reminder and Inbox behaviour diverge. Keeping the source fact canonical while sharing its temporal projection provides reuse without creating competing sources of truth.

Consequences:
New record-derived reminder sources must register or adapt to the shared occurrence boundary instead of adding standalone source loops or delivery implementations. Event schedules, recurring Event instances, cached external occurrences and eligible record-derived dates may therefore use the same downstream reminder and Inbox machinery while retaining source-specific resolution rules; for example, an ordinary Event reminder may cease after the Event ends while a Document-expiry condition may remain actionable. Reminders without a meaningful temporal occurrence, such as a process approval or system failure, retain their own operational semantics and are not forced through this pipeline. The current hardcoded reminder-source enumeration is an implementation limitation to remove during the next authorised reminder/Inbox refactor; this decision does not claim that refactor is already complete.

## ADR-029: Store canonical place facts as independent assertions

Status: Accepted

Date: 2026-08-05

Decision:
Keep a Location's address history, geometry history and provider identities in separate normalized records rather than typed Location columns or a provider-owned feature. Address assertions carry purpose, current/preferred state, confidence and source snapshots. Geometry assertions carry a constrained point/line/area type, role, current/preferred state, confidence, optional supplied accuracy and source snapshots. Geometry coordinates use compact canonical JSON arrays in WGS84 longitude/latitude order and are validated without a spatial extension. A `contains_location` Relationship gives a child at most one active parent and forbids cycles. Provider feature references are neutral removable links and never own accepted geometry.

Reason:
Fictional address-history, station/entrance, building/area and two-provider-version cases showed that address applicability, geometry role and provider lifecycle change independently. Normalized metadata needs ordinary SQLite uniqueness and projection indexes, while compact coordinate JSON preserves Point, LineString, MultiLineString, Polygon and MultiPolygon nesting portably under the standard-library-only runtime. Keeping type and role outside the JSON makes the current representative-point projection deterministic without selecting a renderer, provider or spatial engine.

Consequences:
The editable Location form remains a narrow projection over the preferred current physical address and representative point; replacement retains prior assertions as history. The Map reads only the preferred current representative point, and a child may display but never copy an ancestor address. Migration `20260805_33_canonical_place_foundation` removes flattened Location place columns only after preserving valid values and provenance, and refuses incomplete or invalid legacy coordinates. Whole-platform validation covers geometry and containment independently of SQLite triggers. Reconsider coordinate encoding only when an authorised spatial engine demonstrates query/index requirements JSON cannot reasonably meet, single active parent only for a concrete ambiguous real-place workflow, and provider reconciliation only with reviewed save/refresh evidence; this decision chooses no provider or N2 renderer architecture.

## ADR-030: Keep the first Map workspace browser-native and provider-neutral

Status: Accepted

Date: 2026-08-05

Decision:
Render Map 2.0A with a browser-native coordinate canvas over grouped canonical place payloads and a bounded same-origin viewport endpoint. Server-render and rank canonical search separately from viewport loading. Store last viewport, canonical layer visibility and sidebar state only in failure-tolerant browser-local storage; keep selection in the URL. Remove Leaflet CDN and automatic OSM tile requests. Expose unavailable base/provider layers with explanations, and permit the existing Nominatim boundary only through an off-by-default, explicit per-search control that sends the entered query without adding canonical metadata.

Reason:
Dense N1 evidence showed that grouping 864 flat record markers into 96 canonical place payloads reduced compact JSON from 339 KB to 86 KB, while local viewport filtering remained below 0.9 ms. A temporary-port browser review proved constrained reflow, keyboard operation, non-colour selection, stable search through pan/zoom and zero cross-origin page resources. This gives N2 a useful offline workspace and an honest degraded state without prematurely fixing N4's tile/pack/search provider or a routing architecture.

Consequences:
Map browsing, selection, clustering, text alternatives and canonical layer controls work without WAN access or installed packs. Stale viewport fetches are aborted and out-of-order responses are ignored; panning never reruns ranked search. Records sharing a Location use one pin and records related to several Locations state that multiplicity. Normal/satellite/terrain and provider/workflow overlays remain visible but unavailable until their own evidence gates. Reconsider the renderer only when a selected local basemap cannot integrate safely, representative data exceeds the bounded seam, or a reviewed provider has a materially different rendering/attribution lifecycle. This decision selects no pack format, tile source, routing engine, current-location mechanism or later provider architecture, and it supersedes ADR-003's statement that Projects and Documents categorically cannot participate in Map projection when they have a qualifying Location Relationship.

## ADR-031: Own journey meaning before selecting a routing provider

Status: Accepted

Date: 2026-08-05

Decision:
Keep journey endpoint resolution, capability preflight, request/fingerprint semantics, normalized stages/results, typed failures, profile/policy identity and cache status in Project E-owned standard-library contracts. Resolve only deliberate current canonical Location route anchors, entrances or representative points; refuse ambiguity and unsupported requirements before calling an adapter. Require every adapter result to retain requested profile/policy disposition, separate distance/time meanings, source versions, coverage, freshness, warnings and a textual itinerary. Store audited revisioned profile/policy configuration in the canonical database, but keep bounded route results in a clearable ignored SQLite cache that is excluded from recovery.

Reason:
Deterministic fictional adapters proved ambiguous endpoints, unsupported requirements, partial coverage, no-route versus provider failure, contiguous profile limits, policy conflicts/no-compliant-route and fresh/stale/miss/corrupt cache outcomes without engine-specific types. Every semantic request/configuration/adapter/source variation changed the fingerprint. The contract, two small additive configuration tables and disposable cache could be delivered together without choosing an engine, provider mappings, preset values or Calendar persistence; splitting them would leave either the adapter or durability boundary incomplete.

Consequences:
Routing providers remain replaceable calculators and cannot silently weaken a request, own personal configuration or turn failure into no-route. Migration `20260805_34_journey_contract_foundation` adds only mobility profiles and routing policies; calculated results create no Event or journey group. X1 compared real candidates against this seam without requiring a contract change; ADR-032 records the resulting capability-specific direction. Reconsider contract shapes only for a measured provider semantic that cannot be represented honestly, profile/policy specialization only from N6/N7/N9 evidence, and cache storage/bounds only after representative size, latency and retention measurements.

## ADR-032: Select spatial providers per capability after X1

Status: Accepted

Date: 2026-08-07

Decision:
Use capability-specific, replaceable front-runners for the next authorised spatial slices rather than selecting one global provider. Begin N4 evidence with tilemaker-derived vector MBTiles rendered by vendored MapLibre GL JS and MOTIS local geocoding; begin N6 street-adapter evidence with Valhalla; and begin N7 static-transit evidence with MOTIS. Treat all regional source inputs and derived provider artifacts as verified ignored resources outside canonical storage, prefer prebuilt verified derivatives on the measured host, and keep every native engine behind Project E's standard-library subprocess/loopback and provider-independent contracts. This decision authorises no production installation or adapter by itself.

Reason:
The fixed Gold Coast spike carried one official boundary, dated Queensland OSM snapshot and current SEQ GTFS through tilemaker 2.4, MapLibre GL JS 6.2.0, Valhalla 3.8.3 and MOTIS 2.11.0. Valhalla produced the smaller street graph and lower runtime footprint while MOTIS alone proved direct current-GTFS import, depart/arrive multimodal transit, local typed search and native Windows startup. tilemaker produced a compact independently served vector archive, avoiding MOTIS tile/search/routing/timetable coupling for the first visible slice. Reference-complete OSM extraction and MOTIS import each peaked around 3.2 GiB on the 3.7 GiB host, making an ordinary in-app local build unsafe without further evidence. The observed default-route bounds, distant snapping, absent Wait legs and missing admin/timezone data all fit ADR-031's existing explicit capability/failure seam.

Consequences:
N4 subsequently completed the tilemaker/MBTiles and MapLibre adoption plus the archive, staged-validation, disk-budget, browser/accessibility and atomic last-known-good obligations in ADR-033. It invoked this ADR's explicit capability-separation trigger and selected the derived SQLite challenger instead of MOTIS geocoding for ordinary installed Map search; MOTIS remains the N7 static-transit front-runner. MapLibre/tilemaker/MBTiles is reconsidered for MOTIS tiles or PMTiles only on a measured rendering/serving/lifecycle problem. Valhalla street routing is reconsidered for MOTIS if native Windows, bounded snapping, admin/timezone or policy mapping fails. MOTIS transit is reconsidered for OpenTripPlanner only if N7 cannot normalize waits, service-day/update or typed empty/coverage/no-route semantics. No provider fact becomes canonical, no unproven policy/accessibility/safety claim is mapped, and each production capability retains independent source, coverage, freshness, attribution and rollback state.

## ADR-033: Install bounded regional resources outside canonical recovery

Status: Accepted

Date: 2026-08-07

Decision:
Adopt `project-e-spatial-pack` schema version 1 as an exact bounded ZIP containing a declarative manifest, tilemaker vector MBTiles, a fixed read-only Project E search SQLite database and coverage GeoJSON. Inspect and stage under ignored runtime storage; verify path/membership, declared size and SHA-256, disk reserve, SQLite identity/integrity/schema, zoom/bounds and geometry before activation. Store immutable validated versions outside the canonical database and atomically select one active region with a small JSON pointer that retains one previous version for rollback. Audit activation, rollback and confirmed removal while excluding pack bytes from portability and canonical recovery.

Render an active pack through vendored MapLibre GL JS 6.2.0 and allowlisted same-origin tile/coverage/static-transit endpoints under N2's canonical DOM overlay and complete textual alternative. Build installed search from visible vector labels and static GTFS stops into the fixed SQLite index. Keep Nominatim separately explicit/off-by-default. Permit no provider feature, stop, road, label or pack identity to become a canonical Location or Relationship through browsing.

Reason:
The verified Gold Coast archive is 18.3 MB compressed and about 24 MB installed, with 1,431 tiles and 38,180 search features. It rendered a useful normal map with visible source/coverage/freshness/attribution and repeated representative search averaged about 11.6 ms on the measured host. A native MOTIS process would couple basic search to a 231.4 MB build and approximately 3.2 GiB import despite N4 needing neither routing nor timetable calculation. The X1 decision explicitly named capability separation/import cost as the trigger for the SQLite challenger. Strict pre-activation fixtures proved checksum/path/disk/different-region refusal; a simulated atomic-pointer failure left the old version active; update, two-way rollback and removal left canonical data unchanged. A temporary-port Edge run loaded only same-origin tiles/coverage/transit, retained keyboard/text operation and inspected a rendered provider feature without mutation.

Consequences:
The first production slice deliberately supports one active region and a small indexed `LIKE` search rather than a general pack federation, FTS platform or native geocoder service. Coordinates and canonical pins remain visible outside pack coverage or when the renderer/search fails. Map source inputs, derived indexes and versions must be reacquired/reinstalled independently of personal recovery. Reconsider multi-region composition when N5 coverage recommendations or N6 route-source compatibility supplies concrete adjoining-region cases; reconsider FTS or MOTIS search only when representative search semantics/latency exceed the fixed index; reconsider PMTiles only on a measured MBTiles serving or lifecycle problem. N5 remains responsible for reviewed duplicate-aware provider promotion, portable lists and provider-version disappearance/reconciliation.
