# Roadmap

This roadmap is directional guidance, not implementation authority or a rigid release checklist. Current behaviour belongs in the [Stage 1 specification](docs/stage_1_spec.md); unresolved engineering risks belong in the [technical-debt register](docs/reviews/technical_debt_register.md).

## Platform Maturity / Pre-Operational Intelligence (current)

Project E's foundational information platform is largely established. The current transition stage is about completing and proving platform-wide lifecycle, audit, recovery, portability and usability behaviour—not adding more CRUD domains or beginning Operational Intelligence early.

Current priorities are:

- validate the newly implemented portable import/export and recovery workflow against representative everyday workflows and data
- complete maintainer review of the explicit recycled-dependent relationship policy
- record the Phase 1 exit decision after final verification
- keep architecture, migrations and documentation coherent while the foundation settles

Scale-driven work such as SQLite-backed filtering, FTS5, physical analytics columns and fully offline map assets remains trigger-based rather than mandatory for Phase 1 exit.

## Phase 1 — Information Platform

Phase 1 establishes canonical People, Organisations, Locations, Projects, Documents, Assets and Relationships; local SQLite persistence; reusable profiles and retrieval; maps and local documents; journals and timelines; taxonomies and reference data; audit history and provenance; duplicate merging; explainable data-quality checks and reviewed deterministic inference; and recoverable entity and relationship lifecycles.

### Phase 1 Exit Criteria

These criteria describe readiness to shift the project's primary focus; they are a judgement framework, not a promise that every possible CRUD refinement is finished.

- Canonical entities and relationships support coherent create, view, edit, soft-delete, restore and auditable lifecycle behaviour.
- Core navigation, search, filtering, documents, timelines, maps and maintenance tools are useful without WAN access, apart from clearly optional replaceable map resources.
- Schema evolution is migration-safe for supported local databases, with privacy-safe handling of runtime data and files.
- Important mutations are validated and visible through record-level or system-wide audit history; derived timeline and audit concerns remain separate.
- Deterministic maintenance features are explainable and preserve explicit user confirmation for consequential writes.
- Backup-conscious import and export can move canonical records and relationships without bypassing validation, provenance or user ownership.
- Representative human workflows have been exercised sufficiently to show that the platform is dependable, understandable and independently useful before intelligence is layered on top.
- Remaining limitations are documented with a trigger and direction rather than allowed to expand Phase 1 indefinitely.

The implementation now includes versioned checksummed import/export, recovery backups and an explicit recycled-relationship policy for merge and permanent deletion. Phase 1 remains in exit review until representative workflows, migration/round-trip evidence, offline behavior and maintainer confirmation are recorded. Broader journal domains, scale optimisations and UI refinements are not automatic blockers; they remain evidence-driven.

## Phase 2 — Operational Intelligence

Turn trustworthy information into explainable, reviewable operational insight while retaining human control. Candidate capabilities include duplicate and merge suggestions, missing important fields or relationships, stale-information detection, deterministic data-integrity analysis, rule-based recommendations, scheduled platform health checks, operational notifications and platform recommendations.

Phase 2 may establish carefully designed scheduling and reusable operational actions. Consequential mutations still require explicit confirmation, and every operation must use the same validation, provenance and audit paths as human edits. Advanced relationship work—graph traversal, indirect discovery, advanced querying and relationship analytics—belongs here only when driven by concrete operational workflows.

## Phase 3 — AI-assisted Platform

Add bounded, attributable assistance such as natural-language retrieval, summarisation, classification, extraction, drafting and proposed actions. AI suggestions and actions must be reviewable, grounded in canonical records and visible in system audit. AI must not become a competing source of truth or bypass confirmation and validation.

## Phase 4 — AI/Agent Platform

Explore goal-directed assistance only after the platform is independently useful, coherently machine-readable, safely machine-writable and supported by explicit authority and recovery boundaries. [Odysseus](docs/future_direction.md#odysseus) remains a possible future integration or fork target, not a present dependency.

## Deferred relationship evolution

Do not treat richer relationship evidence as an incidental field addition. Confidence scores, confidence/source attribution, evidence/provenance, richer provenance and verification workflows require a deliberate model that distinguishes asserted facts, supporting material and review state. They are planned after the Phase 1 foundation unless a concrete foundational need changes that priority.

## Across every phase

- SQLite and the local database remain the canonical source of truth.
- Core operation remains local-first; optional services must be replaceable.
- Human users, deterministic operations and future AI converge on shared platform capabilities.
- Validation, relationships, audit history, provenance, recovery and user control remain strategic infrastructure.
- Roadmap entries never authorise implementation on their own.
