# Build Log

## 2026-06-21

Architecture foundation documentation created for Operation Eddy.

Decisions captured:

- Stage 1 is a local-first structured information platform.
- Initial domains are People, Organisations and Locations.
- Entities are canonical records for real-world objects.
- Relationships are first-class records.
- Search and relationship navigation come before maps.
- Maps are a later Stage 1 view over Location data.
- AI, chat, dispatcher behaviour, scheduling, login, WAN features and automation are excluded from Stage 1.
- Simple import and export tools are allowed when they help populate, migrate or protect local data.
- SQLite or an equivalent embedded local database is the default persistence direction.

Initial application foundation implemented.

What changed:

- Added a no-dependency Python local web application.
- Added SQLite schema creation for `entities`, `people`, `organisations` and `locations`.
- Added reusable entity definitions to keep future entity types extensible.
- Added dashboard, browse pages, create/edit forms, detail pages and delete actions.
- Added shared layout and CSS.
- Added focused database CRUD tests.

Relationship features were intentionally not added in this pass.

Reusable entity architecture milestone completed.

What changed:

- Added a shared `EntityRecord` model for all domains.
- Moved reusable page layout, navigation, list, detail and form rendering into `app/views.py`.
- Changed schema creation to derive entity types and typed tables from `EntityDefinition`.
- Kept People, Organisations and Locations on the same CRUD flow.
- Added graceful server shutdown handling for `Ctrl+C`.

Architectural correction:

- Raw SQLite rows are no longer passed through route rendering as the domain model. This was corrected so future entity types can share behaviour, metadata and UI without copying route code.
