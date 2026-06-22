# Technical Debt Register

Date: 2026-06-22

## 1. Oversized View Module

Severity: high

Affected area: `app/views.py`

Why it matters: One module renders layout, dashboard, entity lists/details/forms, relationship workflows, search, map HTML and inline JavaScript. This increases risk when changing any UI surface.

Recommended fix: Split into focused modules such as `views/layout.py`, `views/entities.py`, `views/relationships.py`, `views/search.py` and `views/map.py`, or a similarly small structure that fits the current no-framework architecture.

Fix before new features: yes.

## 2. Relationship Taxonomy Is Hard To Extend

Severity: high

Affected area: `app/relationships.py`

Why it matters: Relationship definitions, role labels, gender-aware labels and legacy behaviour are central to the product. As more domains are added, the current code-only catalogue will be difficult to audit and easy to break.

Recommended fix: Move taxonomy into a compact registry/data section and keep logic functions small. Add tests that assert valid selectable relationship choices for every entity pair.

Fix before new features: yes, before adding relationship-heavy domains.

## 3. Database Module Mixes Too Many Responsibilities

Severity: high

Affected area: `app/db.py`

Why it matters: Schema creation, compatibility migration, CRUD, validation, relationship persistence, discovery and search all live together. Future migrations/imports will make this harder to reason about.

Recommended fix: Split schema/migration helpers from entity repository, relationship repository and search/discovery queries while preserving the public behaviours.

Fix before new features: yes.

## 4. Route Handler Owns Form Parsing, Uploads And Workflow Orchestration

Severity: medium

Affected area: `app/web.py`

Why it matters: Route handling is currently simple but increasingly crowded. Multipart upload storage and inline relationship target creation are business logic hidden inside the HTTP handler.

Recommended fix: Extract upload storage helpers and relationship workflow service functions. Keep `EddyRequestHandler` focused on routing, request parsing and responses.

Fix before new features: yes, before imports or more document/file behaviour.

## 5. No Explicit Schema Version Or Migration Ledger

Severity: medium

Affected area: SQLite schema initialization in `app/db.py`, docs/database design

Why it matters: Startup performs useful additive migrations, but future agents have no durable record of which migrations ran against a local database.

Recommended fix: Add a small `schema_migrations` or `app_metadata` table with schema version and applied migration identifiers. Keep existing additive startup safety.

Fix before new features: yes, before import/export or larger domain additions.

## 6. Typed Fields Stored As Text

Severity: medium

Affected area: typed entity tables and relationship dates

Why it matters: Text storage simplifies Stage 1 but weakens sorting, validation and data export for dates, coordinates, booleans and money.

Recommended fix: Keep SQLite, but introduce field-level validation and formatting first. Consider typed columns only when a migration policy exists.

Fix before new features: no, but fix before analytics, robust export or larger imports.

## 7. No Canonical Duplicate Safeguards

Severity: medium

Affected area: entity creation/editing, search, domain model

Why it matters: "One canonical record per real-world object" is a core principle, but the app currently allows easy duplicates.

Recommended fix: Add duplicate warnings on create/edit using display name plus selected key fields per entity type. Do not block creation at first.

Fix before new features: yes, before import tools.

## 8. Search Is In-Memory And Linear

Severity: medium

Affected area: `search_entities`, `entity_matches_query`, relationship search

Why it matters: Works for small local data but may become slow after imports or many documents/assets.

Recommended fix: Keep current behaviour for now. Revisit with SQLite FTS or indexed query helpers when data volume justifies it.

Fix before new features: no, unless import work is next.

## 9. Document File Lifecycle Is Incomplete

Severity: medium

Affected area: Document uploads and deletion

Why it matters: Replacing or deleting Document entities can leave local files behind, and file metadata is treated as editable hidden fields.

Recommended fix: Define file lifecycle rules: retain old files intentionally, garbage collect unreferenced files, or delete on entity deletion. Then implement the smallest safe policy.

Fix before new features: yes, before expanding document handling.

## 10. Relationship Duplicate Handling Is Missing

Severity: medium

Affected area: relationship creation and validation

Why it matters: Users can create multiple active relationships of the same type between the same endpoints without warning.

Recommended fix: Add a warning or validation rule for exact duplicate active relationships. Allow deliberate historical duplicates when dates/status differ.

Fix before new features: no, but should precede bulk import.

## 11. Map View Depends On External Resources

Severity: low

Affected area: `app/geo.py`, map page in `app/views.py`

Why it matters: Stage 1 is local-first. Leaflet and map tiles load from WAN, and address lookup calls Nominatim.

Recommended fix: Keep map/address lookup optional. Document fallback behaviour and consider vendoring Leaflet assets later if map use becomes core.

Fix before new features: no.

## 12. Domain List Pages Are Too Generic

Severity: low

Affected area: entity list rendering

Why it matters: Every list uses name plus notes, which hides useful structured fields such as organisation type, project status, document type or asset status.

Recommended fix: Use `FieldDefinition.overview` or a new list-field flag to render useful columns per domain.

Fix before new features: no.

## 13. Build Log Is Long As Handoff Context

Severity: low

Affected area: `docs/build_log.md`

Why it matters: It is useful history but inefficient as context for future agents.

Recommended fix: Keep it as history. Use `docs/reviews/claude_handoff.md` and concise architecture docs as active handoff context.

Fix before new features: no.

## 14. Minimal Attribution Convention Not Yet Adopted

Severity: low

Affected area: mixed Codex + Claude workflow

Why it matters: Lightweight attribution could help diagnose future implementation differences without adding bureaucracy.

Recommended fix: Use commit message trailers only, such as `Agent: Codex` or `Agent: Claude`.

Fix before new features: no.
