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

