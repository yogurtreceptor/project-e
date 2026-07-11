# Architecture Decisions

This file records important architecture decisions for Project E.

Use it when a decision affects the long-term structure, direction or maintainability of the project.

Examples of decisions worth recording:

* choosing a backend framework
* choosing a database
* changing the entity model
* changing the relationship model
* adding a new major domain
* changing the Stage 1 scope
* introducing authentication
* introducing external integrations
* postponing AI, automation or decision support

Do not record tiny implementation details.

Each decision should use this format:

```text
## ADR-000: Short decision title

Status: Proposed / Accepted / Superseded

Date: YYYY-MM-DD

Decision:
Briefly state the decision.

Reason:
Explain why this decision was made.

Consequences:
Explain what this enables, limits or changes.
```

New decisions should be added to the bottom of this file.

If a decision is replaced later, do not delete the old decision. Mark it as superseded and add a new decision below it.

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
Most expected addresses are Australian, and G-NAF is the strongest fit for house-level Australian address coordinates. However, the dataset is large and should not become a mandatory Stage 1 dependency or be imported directly into the main application database before the address-index workflow is deliberately designed.

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
Stage 1 may use deterministic, local and explainable assistance or internal maintenance when it preserves user control. A capability is inside the Stage 1 boundary when its behaviour is rule-based and auditable, requires explicit confirmation before a consequential mutation, performs no scheduled or autonomous goal-directed workflow, creates no autonomous external side effect, and does not require WAN access for core operation. Capabilities that cross these tests require explicit scope approval.

Reason:
Useful information-management behaviour often performs work automatically without becoming autonomous automation. Treating every derived value, warning or housekeeping action as prohibited would conflict with the implemented platform and obscure the actual safety boundary: whether the system acts consequentially or externally without the user's informed control.

Consequences:
Deterministic relationship inference, duplicate warnings, derived views, automatic display-name maintenance and review-batch archival remain valid Stage 1 behaviour. Inference may recompute candidates automatically, but a candidate cannot become a canonical relationship until the user confirms it. AI, decision support, scheduling, autonomous goal-directed workflows, unreviewed consequential actions and autonomous external side effects remain outside Stage 1. Optional network aids remain acceptable only when core records and workflows work without them.

## ADR-007: Separate taxonomy hierarchy from domain behavior

Status: Accepted

Date: 2026-07-04

Decision:
Store reusable classifications in a shared database-backed hierarchy capped at Type, Subtype and Specific subtype. Domain records reference one terminal entry representing the complete path. Keep relationship endpoint constraints, direction and inverse labels in a relationship-specific definition table rather than expanding the generic hierarchy into an ontology engine.

Reason:
Organisation and relationship classifications need the same path, search, reuse and archive behavior, while only relationships require directional semantics. Separating these concerns keeps the taxonomy reusable and the relationship model explicit.

Consequences:
Organisation and relationship rows gain taxonomy foreign keys. Legacy Organisation text and relationship keys remain compatibility snapshots during migration. Archived branches remain readable but unavailable for new selection. Other Stage 1 type systems are unchanged until separately authorised.

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


## ADR-010: Use validated snapshot bundles for Stage 1 portability and recovery

Status: Accepted

Date: 2026-07-05

Decision:
Use a versioned, checksummed ZIP containing a consistent SQLite backup plus referenced uploaded documents as the Stage 1 export and recovery format. Validate the manifest, every member checksum, current schema/migrations, SQLite integrity, foreign keys, canonical entity/relationship structure and document membership before preview or apply. Normal import applies only to an empty target after explicit confirmation; recovery replacement remains a separately confirmed maintenance command.

Reason:
The SQLite database already contains the canonical graph, custom taxonomies, normalized measurements/references, provenance and append-only audit history. Re-serializing a subset into a parallel interchange model would risk semantic loss and duplicate sources of truth. SQLite's standard-library backup API provides a consistent local snapshot without a new dependency.

Consequences:
Exports are complete local snapshots rather than partial CSV-style ingestion. Bundle format changes require a versioned migration policy. Imported identities, audit and provenance are preserved; a new import audit event records ownership transfer into the local installation. Import, merge and permanent deletion create Git-ignored recovery bundles first. Conflict-aware import into a populated database remains out of Stage 1 scope.

## ADR-011: Treat Events and Tasks as first-class peer entities

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Phase 2 will add Events and Tasks as canonical peer entities using the shared entity lifecycle and relationship system. Projects coordinate them but do not own them.

Reason:
Time occurrences and work require stable identity, history, search and cross-domain relationships without creating special nested models.

Consequences:
Event and Task links to Projects, each other and other domains use normal relationships; neither an event-task type nor per-domain link columns are the default model.

## ADR-012: Keep the Calendar a projection over canonical time information

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Calendar views derive from canonical records and traceable derived occurrences; they do not maintain a duplicate event store.

Reason:
One source of truth preserves lifecycle, audit and relationship semantics across Events, Tasks and other dated records.

Consequences:
Displaying a deadline, birthday or scheduled run does not change its source type. Shared temporal semantics precede calendar implementation.

## ADR-013: Model reminders as policies and deliveries, not standalone domain entities

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
Reminders are attached policies, with global defaults and entity-level overrides. Deterministically derived occurrences remain traceable to source facts; delivery, acknowledgement and snooze history are separate notification records.

Reason:
This avoids annual duplicate reminder definitions while allowing meaningful user control and delivery audit.

Consequences:
An Event or Task is not a Reminder. Birthdays and expiries can use policy-driven occurrences without becoming independent canonical reminder records.

## ADR-014: Separate actionable notifications from persistent issues

Status: Accepted (Phase 2 target architecture)

Date: 2026-07-11

Decision:
The inbox holds actionable notifications; system-health conditions use durable current issue records. Persistent issues are deduplicated and escalated only on meaningful state or severity changes.

Reason:
An unchanged condition is not a new event every day, and repeated noise obscures useful attention.

Consequences:
Notifications, persistent issues, audit events and job runs remain distinct record types and audit trails.

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
Consequential actions may require approval states; no AI agents or autonomous AI-generated actions are introduced in initial Phase 2.

## ADR-017: Define Phase 2 completion as integrated operational behaviour

Status: Accepted

Date: 2026-07-11

Decision:
Phase 2 completes only after the agreed Event, Task, calendar, reminder, inbox, health, scheduler, automation, audit and provenance workflow works coherently and passes an end-to-end completion review.

Reason:
Isolated tables and pages do not prove an operational platform.

Consequences:
The implementation sequence and completion scenario in `docs/phase_2_plan.md` govern closure review; starting Phase 2 does not imply completion.
