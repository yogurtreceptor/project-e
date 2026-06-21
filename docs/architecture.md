# Architecture

Operation Eddy should use a simple local-first architecture for Stage 1.

## Shape

The system should be organised around three practical layers:

- Local UI for browsing, editing, searching and navigating information.
- Local application layer for validation, persistence rules and view logic.
- Embedded local database for durable storage.

SQLite or an equivalent embedded local database is the default persistence choice unless superseded by an ADR.

## Boundaries

Stage 1 should not introduce separate AI, automation, dispatcher, scheduling, authentication or cloud service layers.

The application should not depend on WAN access for normal operation. External access may be considered later only through explicit architecture decisions.

## Data Model Direction

The architecture is entity-first and relationship-first.

- Core entity records provide shared identity, naming and lifecycle fields.
- Typed profile data extends entities into People, Organisations and Locations.
- Relationships connect entities and are stored as records with their own metadata.
- Views should read from the same canonical records instead of creating duplicate data paths.

## Import and Export

Simple import and export tools are allowed when they support population, migration or backup of local data.

Imports should feed the same canonical entity and relationship model as manual entry. They should not become background automation or external integrations during Stage 1.

## Documentation Rule

Planning documents should be updated when architecture, scope, data model or domain boundaries change.

