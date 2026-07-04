# Roadmap

This roadmap is directional guidance, not a release schedule or rigid sequence. Phases describe capability maturity; they may overlap, and priorities may change when foundational work becomes strategically important. Roadmap entries provide context, not authority to implement work.

Current behavior belongs in the [Stage 1 specification](docs/stage_1_spec.md) and reference documentation. Unresolved engineering risks belong in the [technical-debt register](docs/reviews/technical_debt_register.md).

## Phase 1 — Information Platform (current)

Make Project E a dependable, useful home for private, connected information.

Established foundations include canonical entities and relationships; local SQLite persistence and migrations; reusable profiles, search and filters; maps and local documents; journals and timelines; taxonomies and reference data; audit history and provenance; duplicate merging, data-quality checks and reviewed deterministic inference; and platform-wide soft deletion.

Current priorities:

- improve repeated human workflows, navigation, forms and relationship handling
- strengthen validation, provenance, auditability and data quality
- add import/export that protects canonical records and local ownership
- keep architecture and documentation coherent as domains expand
- improve machine-readable access without creating a second data model

Scale-driven work such as SQLite-backed filtering, FTS5, physical analytics columns and fully offline map assets should be introduced when representative data or real workflows justify it.

## Phase 2 — Operational Platform

Turn trustworthy information into reliable workflows while retaining human control.

Likely themes include richer lifecycle and event models, reusable actions, reminders or scheduling where explicitly designed, stronger import/export and integration boundaries, and deterministic workflow automation. Machine-writable operations should use the same validation, confirmation, provenance and audit paths as human edits.

This phase should establish the safe capability surface that later AI can consume. It should not be designed as a disposable prelude to an agent system.

## Phase 3 — AI-assisted Platform

Add bounded intelligence to help people understand and maintain the platform.

Potential capabilities include natural-language retrieval, summarisation, classification, extraction, drafting and proposed actions. AI output should remain attributable, reviewable and grounded in canonical records. Consequential writes require explicit safeguards appropriate to their risk; AI must not bypass platform validation or become a competing source of truth.

## Phase 4 — AI/Agent Platform

Support goal-directed assistance only after the underlying platform is useful to humans, machine-readable, safely machine-writable and architecturally strong.

[Odysseus](docs/future_direction.md#odysseus) is the leading candidate for this future AI/agent layer and a possible integration or fork target. Project E should not be restructured around it in advance. Any future work should adapt Odysseus to Project E's capabilities, data ownership and safety model.

This phase may explore delegated workflows, planning and controlled external actions. Authority, review, reversibility, provenance, privacy and failure containment must be explicit before autonomy expands.

## Across every phase

- SQLite and the local database remain the canonical source of truth.
- Core operation remains local-first; optional services must be replaceable.
- Human users, automation and AI converge on shared platform capabilities.
- Deterministic rules, validation, relationships, audit history, provenance and data quality remain strategic infrastructure.
- Trusted multi-user support may be considered later, but the current private single-user experience must stay simple.
