# Final Codex Architecture Review

Date: 2026-06-22

## Executive Summary

Operation Eddy mostly matches the current local-first Personal Operational Intelligence Platform direction. The active code is entity-first, relationship-first, SQLite-backed and free of Stage 1 AI, chat, dispatcher, automation, scheduling, login and WAN-first architecture.

The strongest foundation is the shared `EntityDefinition` model: People, Organisations, Locations, Projects, Documents and Assets all flow through common CRUD, forms, dashboard, search, detail pages and relationship panels. Relationships are first-class records, not embedded fields or duplicated inverse rows.

The highest architectural risk is maintainability. `app/views.py`, `app/db.py`, `app/web.py` and `app/relationships.py` have become large central modules. They are still understandable, but future domains, relationship types, imports and UI polish will make them harder to change safely unless the next work splits responsibilities along stable boundaries.

## Current Repository Strengths

- Clear Stage 1 identity in `AGENTS.md`, `PROJECT_GOAL.md`, `docs/vision.md` and `docs/stage_1_spec.md`.
- No active AI Dispatcher implementation remains in code.
- Local-first foundation uses Python standard library HTTP plus SQLite with lightweight dependencies.
- Entity definitions centralise domain fields, controlled options, display metadata, defaults and safe field rename aliases.
- Documents and Assets are implemented as normal entity domains, proving the entity architecture can extend beyond People, Organisations and Locations.
- Relationships are first-class, navigable from both sides, validated against endpoint entity types and normalised to canonical direction.
- Existing tests cover shared CRUD, relationship validation, context-aware relationship UI, schema evolution, maps, discovery and new domains.
- Documentation explains current entity, relationship, database and UI principles in enough detail for future agents.

## Highest-Risk Weaknesses

1. Relationship taxonomy is hard-coded and already large. More domains will turn `RELATIONSHIP_TYPES` and label helpers into a brittle catalogue unless it is made easier to review, test and extend.
2. View generation is concentrated in one 1,318-line `app/views.py` module containing layout, entity pages, relationship forms, search, map HTML and inline JavaScript.
3. Storage code mixes schema creation, migrations, CRUD, validation, search, relationship persistence and discovery in one 758-line `app/db.py` module.
4. Current schema stores every typed field as `TEXT`, including dates, coordinates, booleans and numeric asset value. This is acceptable for Stage 1 but will constrain validation, sorting, export and future query quality.
5. No explicit duplicate/canonical-record support exists yet, despite "one canonical record per real-world object" being a core principle.
6. Relationship UI supports inline creation only for Person, Organisation and Location. That choice is sensible now, but it should be documented as a deliberate Stage 1 constraint before more domains are added.
7. The map and address lookup introduce network-dependent optional behaviour through OpenStreetMap/Leaflet CDNs. The app degrades, but this should stay clearly optional because Stage 1 is local-first.

## Architecture Assessment

The repository architecture matches the current project vision in broad shape. The platform is organised around canonical entities, first-class relationships, local SQLite storage, dashboard/navigation, search and maps as views over the same data.

The architecture is simple and practical, but the implementation has reached the point where module boundaries matter. The next architecture work should not add features first; it should split existing responsibilities without changing behaviour:

- database schema/migration helpers separate from CRUD/query helpers
- relationship taxonomy separate from relationship label/rendering logic
- entity page/view helpers separate from relationship form and map rendering
- route handler helpers separate from multipart upload and relationship workflow support

This should be done incrementally with existing tests green after each move.

## Relationship System Assessment

The relationship model is strong enough for the current Stage 1 domains, but it needs a maintainability pass before many more domains are added.

Strengths:

- One row per relationship with derived inverse navigation.
- Pair-aware relationship definitions prevent irrelevant types from being offered.
- Perspective-based creation reduces source/target confusion.
- Legacy generic and gendered keys are preserved as loadable but non-selectable.
- Date precision metadata supports uncertainty without losing structure.

Risks:

- Relationship definitions, role labels and gender-aware family labels are spread through several functions in `app/relationships.py`.
- Relationship definitions are code-only, so taxonomy review requires reading Python rather than a compact data structure.
- The current model does not support relationship attributes beyond status, dates and notes. Some future relationships may need role/title, confidence/source, privacy, importance or duplicate-resolution metadata.
- No uniqueness or duplicate-warning model exists for repeated relationships between the same two entities.

Recommendation: keep the current table for now, but refactor taxonomy into a clearer data section or small structured registry before adding new domains or relationship-heavy features.

## Schema / Storage Assessment

SQLite is the right Stage 1 storage choice. The shared `entities` table plus typed one-to-one tables is coherent and easy to inspect.

Good decisions:

- Definition-driven schema creation.
- Additive column migration.
- `entities.type` constraint rebuild when new entity types are introduced.
- Field rename aliases that preserve older local data.
- Documents as entities with local file metadata instead of attachments hidden inside other entities.

Risks:

- All typed values are stored as text. This keeps migrations easy but weakens validation and future querying.
- There is no schema version table or migration ledger. Startup performs implicit migrations, which is fine now but may become hard to audit.
- Search is in-memory over all loaded entities and relationships. This is fine for a small local database but should be revisited before large imports.
- File upload lifecycle is not fully modelled: replacing or deleting Document entities may leave old files in `instance/documents/`.
- `summary` remains in storage as legacy fallback; docs explain this, but future code should avoid bringing it back into forms.

## UI / Forms Assessment

The UI direction is aligned with dashboard/navigation-first and entity-page-first principles. Entity detail pages expose reusable sections, and relationship creation starts from a known entity context.

Forms are mostly structured enough for Stage 1:

- Controlled fields exist for sex, organisation type, project type/status, document type and asset type/status.
- Location has structured address fields plus optional lookup.
- Asset value is validated as whole-number text.
- Relationship type/status/date precision are controlled.

Weak spots:

- Phone, email, website and issuer remain free text. That is acceptable for Stage 1, but contact methods should become first-class records if multiple values, labels, validity dates or verification matter.
- Location address quality depends on manual entry and optional lookup; country/state/post code are free text.
- Dates are HTML date inputs but stored as text and only lightly validated.
- Relationship notes can become a dumping ground for structured facts if the taxonomy does not grow carefully.
- Entity list pages show notes as the second column for all domains; several domains would benefit from definition-driven overview columns.

## Documentation Assessment

The docs are generally current and useful for future AI coding sessions. `AGENTS.md` is concise and aligned. `README.md` is short and practical. The detailed planning docs are mostly accurate.

Main documentation risks:

- `docs/build_log.md` is useful history but long and not ideal as handoff context.
- `ROADMAP.md` is terse and does not show which milestones are done, active or deferred.
- The active scope includes Projects, Documents, Assets and Maps, while some top-level summaries still emphasise the earlier People/Organisations/Locations/Relationships framing.
- There is no compact "start here for future agents" document outside this review handoff.

## Recommended Next 5 Implementation Priorities

1. Stabilise module boundaries without behaviour change. Split `app/views.py`, `app/db.py`, `app/web.py` and relationship taxonomy into smaller responsibility-focused modules.
2. Make relationship taxonomy easier to maintain. Keep the current behaviour, but move definitions and role labels into a compact registry with tests for every selectable pair.
3. Improve schema governance. Add a lightweight schema version/migration ledger and document the additive migration policy.
4. Add canonical-record safeguards. Start with duplicate detection or warnings on create/edit for same display name plus key fields.
5. Improve form structure where free text is doing category work. Prioritise date validation, location field consistency and domain-specific list/table overview columns.

## What Not To Build Yet

- AI, chat, dispatcher, decision support or agent workflows.
- Automation, reminders, scheduling or task management.
- Login, multi-user accounts, WAN/mobile sync or cloud dependencies.
- Complex integrations.
- Full communications domain.
- Heavy graph database or ORM rewrite.
- Large import pipeline before schema governance and duplicate handling are ready.
- Attribution tooling beyond a simple commit-message convention.

## Review Commands Run

- `pwd && rg --files`: succeeded after escalation.
- `git status --short`: showed pre-existing modified `PROJECT_GOAL.md` and `ROADMAP.md`.
- `rg -n "AI|Dispatcher|dispatcher|chat|automation|scheduling|decision support|WAN|mobile|command" .`: found only exclusion/history references, not active dispatcher code.
- `wc -l app/*.py docs/*.md *.md tests/*.py`: used to assess module/document size.
- `rg -n "^    def test_" tests/test_entities.py`: identified 24 existing tests.
- `python3 -m compileall app run.py tests`: passed.
- `python3 -m unittest discover -s tests`: passed, 24 tests.

Sandbox note: ordinary shell startup failed with `No such file or directory`, so inspection and verification commands were rerun with `sandbox_permissions="require_escalated"` as instructed by `AGENTS.md`.
