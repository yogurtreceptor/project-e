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

Status: Superseded by ADR-011

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

Status: Superseded by ADR-011

Date: 2026-07-05

Decision:
Use a versioned, checksummed ZIP containing a consistent SQLite backup plus referenced uploaded documents as the Stage 1 export and recovery format. Validate the manifest, every member checksum, current schema/migrations, SQLite integrity, foreign keys, canonical entity/relationship structure and document membership before preview or apply. Normal import applies only to an empty target after explicit confirmation; recovery replacement remains a separately confirmed maintenance command.

Reason:
The SQLite database already contains the canonical graph, custom taxonomies, normalized measurements/references, provenance and append-only audit history. Re-serializing a subset into a parallel interchange model would risk semantic loss and duplicate sources of truth. SQLite's standard-library backup API provides a consistent local snapshot without a new dependency.

Consequences:
Exports are complete local snapshots rather than partial CSV-style ingestion. Bundle format changes require a versioned migration policy. Imported identities, audit and provenance are preserved; a new import audit event records ownership transfer into the local installation. Import, merge and permanent deletion create Git-ignored recovery bundles first. Conflict-aware import into a populated database remains out of Stage 1 scope.

## ADR-011: Use locally hosted PostgreSQL as the canonical database

Status: Accepted

Date: 2026-07-05

Decision:
Use PostgreSQL 16 or later as Project E's sole database, accessed with psycopg 3 and raw parameterised SQL behind a small boundary. Run it on loopback and a private local socket. Keep Project E Bundles user-facing while using `pg_dump` and isolated validation restores internally.

Reason:
The pre-Phase-2 foundation benefits from explicit process and transaction boundaries. Early development permits a clean baseline without preserving SQLite data or maintaining two backends.

Consequences:
PostgreSQL and psycopg are local prerequisites. SQLite compatibility is removed. This adds no WAN access, authentication, accounts, multi-user behaviour, agents, scheduling, sync or cloud dependency.
