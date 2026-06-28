# ARCHITECTURE_DECISIONS.md

# Architecture Decisions

This file records important architecture decisions for Operation Eddy.

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
Operation Eddy is entity-first and relationship-first. A separate map data store would create duplicate records, make address quality harder to maintain and make future layers harder to extend consistently.

Consequences:
The initial map can display Locations, Organisations and People through the same entity graph. Future geographic layers must derive markers from canonical records or relationships. Organisation address columns from earlier local schemas are ignored by the active model rather than extended.

## ADR-002: Treat G-NAF as an optional future address index

Status: Accepted

Date: 2026-06-21

Decision:
Operation Eddy will keep OpenStreetMap Nominatim as the current lightweight address lookup fallback and treat Australia's Geocoded National Address File (G-NAF) as an optional future local address index for higher-accuracy Australian house-level geocoding.

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
The milestone is intended to prove that Operation Eddy's entity architecture scales beyond People, Organisations and Locations. Reusing `EntityDefinition`, typed tables and central relationships avoids one-off page models and keeps the platform relationship-first.

Consequences:
Existing local databases need the central `entities.type` constraint to evolve when new domains are introduced, so startup now rebuilds that table constraint when required. The old attachment concept is no longer part of the active architecture; file-bearing records should be Document entities linked through relationships.


## ADR-004: Track schema migrations while retaining additive repair

Status: Accepted

Date: 2026-06-28

Decision:
Record ordered, append-only migration identifiers and application timestamps in a local `schema_migrations` table. Continue running the idempotent current-schema repair pass at startup.

Reason:
Local databases need an auditable history for future schema changes, but Operation Eddy also relies on definition-driven additive repair to adopt older databases and safely add fields or entity types. A ledger alone would not cover those evolving definitions.

Consequences:
Future explicit schema changes must append a uniquely named migration and must not rename or remove identifiers already in use. Existing databases can adopt the ledger without losing data. Startup retains a small amount of repeated schema inspection in exchange for compatibility and recovery safety.


## ADR-005: Review deterministic relationship inference before creation

Status: Accepted

Date: 2026-06-28

Decision:
Implement family inference as a reusable deterministic rule engine over canonical Person relationships. Inferred candidates are review suggestions, not relationship records. Confirmation creates a normal editable relationship with provenance; rejection suppresses the unchanged evidence fingerprint. Completed batches archive automatically with searchable history and undo.

Reason:
Safe bloodline facts can be derived consistently from manual parent/child evidence, but derived data must remain explainable and under user control. Keeping suggestions outside the relationship table prevents silent graph mutation while provenance and suppression make reviews repeatable.

Consequences:
Initial rules are limited to grandparent/grandchild, full sibling, aunt/uncle with niece/nephew, and cousin. Half, step, adoptive, foster, guardian, in-law and partner inference remain excluded. Confirmed relationships are editable and are not deleted when original evidence changes; their evidence health is flagged instead. Rule, source relationship IDs, source batch, fingerprint and timestamps remain auditable.
