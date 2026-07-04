# Roadmap

This file tracks delivery direction. Current behaviour belongs in the specification and reference docs; unresolved engineering risks belong in the technical-debt register.

## Stage 1: Information Platform

Delivered:

- local SQLite application foundation and schema migration ledger
- shared entity model for People, Organisations, Locations, Projects, Documents and Assets
- first-class relationship catalogue, CRUD and entity-centred workflows
- reusable entity profiles, dashboard, search, favourites and recent records
- structured filters and local-data privacy boundary
- map view over Locations and location relationships
- local Document upload lifecycle
- duplicate warnings, preview-first entity merge and edit history
- relationship integrity checks and exact-duplicate prevention
- deterministic family inference with review, provenance, history and undo
- responsibility-focused database, view and workflow modules behind stable facades
- People journals with independent chronological entries and lifecycle actions

Active:

- documentation accuracy and concise repository-first context
- dashboard, navigation, forms and relationship polish
- relationship integrity and data-quality polish

Next:

- import/export tools that protect local data quality
- richer derived timeline views
- additional domain-specific list columns beyond People DOB

Reassess when representative data justifies it:

- SQLite-backed filtering or FTS5 search
- physical typed columns for analytics and complex sorting
- vendored map assets for a fully offline map UI

Deferred beyond Stage 1:

- decision support, autonomous goal-directed workflows, scheduling, consequential unattended actions and artificial intelligence
- login, multi-user accounts, WAN-dependent core operation, mobile access and complex integrations
