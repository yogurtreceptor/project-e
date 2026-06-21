# Architecture

Operation Eddy should use a simple local-first architecture for Stage 1.

## Shape

The system should be organised around three practical layers:

- Local UI for browsing, editing, searching and navigating information.
- Local application layer for validation, persistence rules and view logic.
- Embedded local database for durable storage.

SQLite or an equivalent embedded local database is the default persistence choice unless superseded by an ADR.

## Current Implementation

The initial application foundation is a Python standard library web app:

- `run.py` starts a local HTTP server.
- `app/web.py` handles HTTP routing and request/response concerns.
- `app/views.py` owns reusable page layouts, navigation, detail pages and forms.
- `app/db.py` owns SQLite connection, definition-driven schema creation and CRUD operations.
- `app/entities.py` defines the common entity model, metadata and supported entity types.
- `app/static/styles.css` provides the shared UI styling.

No external runtime dependencies are required for the initial foundation.

## Boundaries

Stage 1 should not introduce separate AI, automation, dispatcher, scheduling, authentication or cloud service layers.

The application should not depend on WAN access for normal operation. External access may be considered later only through explicit architecture decisions.

## Entity Architecture

Current domains inherit from a common entity architecture:

- `EntityDefinition` describes each domain type, route slug, table and domain-specific fields.
- `EntityRecord` is the shared runtime model for all entity instances.
- Shared fields are `display_name`, `summary`, `notes`, `created_at` and `updated_at`.
- Domain-specific data is exposed as metadata on the same record object.
- List, detail and form pages are generated from entity definitions.

This corrected an early architectural issue where raw SQLite rows were passed directly into route rendering. The shared model keeps database shape, UI rendering and future domain additions aligned.

## Data Model Direction

The architecture is entity-first and relationship-first.

- Core entity records provide shared identity, naming and lifecycle fields.
- Typed profile data extends entities into People, Organisations and Locations.
- Relationships will connect entities and be stored as records with their own metadata in a later milestone.
- Views should read from the same canonical records instead of creating duplicate data paths.

## Import and Export

Simple import and export tools are allowed when they support population, migration or backup of local data.

Imports should feed the same canonical entity and relationship model as manual entry. They should not become background automation or external integrations during Stage 1.

## Documentation Rule

Planning documents should be updated when architecture, scope, data model or domain boundaries change.

