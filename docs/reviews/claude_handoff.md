# Implementation And Refactor Handoff

Date: 2026-06-22

Originally prepared for Claude Code. Retained as historical/reference guidance for any future implementation agent. Codex is the current primary implementation and review tool; verify this document against current code before acting on it.

## Project Purpose

Operation Eddy is a local-first Personal Information Platform / Personal Operational Intelligence Platform. Stage 1 exists to store, organise, search, display and navigate structured information about real-world entities and relationships.

## Current Stage

Stage 1 only.

Active entity domains are People, Organisations, Locations, Projects, Documents and Assets. Relationships are first-class records connecting any two canonical entities.

## Hard Exclusions

Do not build AI, chat, dispatcher architecture, automation, scheduling, decision support, login, multi-user accounts, WAN/mobile access or complex integrations during Stage 1.

## Architecture Principles

- Entity-first: one canonical record per real-world object.
- Relationship-first: relationships are stored, edited and navigated directly.
- Local-first: SQLite and local files are the source of truth.
- Multiple views over the same data: dashboard, search, maps and entity pages should derive from canonical entities/relationships.
- Prefer maintainable, lightweight, free/open-source solutions.
- Keep documentation current when architecture changes.

## Current Known Issues

- View rendering has been split into focused `app/view_pages/` modules, with `app/views.py` retained as a compatibility facade.
- Database responsibilities are split behind the stable `app/db.py` facade; `app/db_schema.py` includes an append-only migration ledger plus additive startup repair.
- Upload persistence and inline relationship-target creation are separated from `app/web.py` into focused services.
- Relationship taxonomy now lives in grouped `app/relationship_catalog.py` metadata with pair-coverage contract tests.
- All typed fields are stored as text; fine for now, but weak for dates, coordinates, numeric values and future querying.
- No duplicate/canonical-record warning exists yet.
- Optional map/address lookup uses network resources; normal app operation should remain useful without them.

## Recommended Next Refactor Task

Refactor for maintainability without changing behaviour:

Add field-level validation and normalization for structured text-backed values, beginning with dates and coordinates. Preserve incomplete optional fields, return useful form errors, and avoid physical SQLite type migrations until a concrete querying need justifies them.

## Inspect First

- `AGENTS.md`
- `README.md`
- `docs/vision.md`
- `docs/stage_1_spec.md`
- `docs/architecture.md`
- `docs/ontology.md`
- `docs/database_design.md`
- `docs/ui_principles.md`
- `app/entities.py`
- `app/relationship_catalog.py`
- `app/relationships.py`
- `app/db.py`
- `app/db_schema.py`
- `app/entity_repository.py`
- `app/relationship_repository.py`
- `app/discovery_repository.py`
- `app/web.py`
- `app/document_storage.py`
- `app/relationship_workflow.py`
- `app/views.py`
- `tests/test_entities.py`
- `docs/reviews/final_codex_review.md`
- `docs/reviews/technical_debt_register.md`

## Avoid Over-Editing Unless Necessary

- `docs/build_log.md`: useful history, but too large to polish during feature/refactor work.
- `PROJECT_GOAL.md` and `ROADMAP.md`: currently modified before this review session; inspect before editing.
- Existing migration compatibility paths in `app/db.py`: preserve old local database compatibility.
- Legacy relationship keys in `app/relationships.py`: keep loadable unless a deliberate migration is designed.

## Implementation Style Preferences

- Keep changes small and behaviour-preserving unless the task explicitly asks for a feature.
- Prefer standard library and SQLite.
- Do not introduce an ORM or frontend framework just to tidy code.
- Use existing entity definitions and relationship primitives rather than one-off domain code.
- Add meaningful regression tests for architecture changes that could break existing data, relationship direction, forms or navigation.
- Keep docs concise; update planning docs only when architecture, scope or domain boundaries change.

## Attribution Recommendation

Use commit message trailers only when commits are made. For the current workflow:

```text
Agent: Codex
```

If Claude Code is used later:

```text
Agent: Claude
```

Do not add per-file signatures or attribution tooling unless the workflow later proves it needs more.
