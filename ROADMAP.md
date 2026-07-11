# Roadmap

This roadmap is directional guidance, not implementation authority or a rigid release checklist. Current behaviour belongs in the [Stage 1 specification](docs/stage_1_spec.md); unresolved engineering risks belong in the [technical-debt register](docs/reviews/technical_debt_register.md).

## Phase 1 — Information Platform

Phase 1 establishes canonical People, Organisations, Locations, Projects, Documents, Assets and Relationships; local SQLite persistence; reusable profiles and retrieval; maps and local documents; journals and timelines; taxonomies and reference data; audit history and provenance; duplicate merging; explainable data-quality checks and reviewed deterministic inference; and recoverable entity and relationship lifecycles.

### Status: Complete

Pull request #1 is closed and Phase 1 is complete enough to close as a development milestone. Its closure is based on representative verification, not exhaustive manual testing of every capability. Residual defects may still be found and are handled through normal maintenance without reopening Phase 1 as a whole. The closure record is the [Phase 1 review](docs/reviews/phase_1_exit_review.md).

## Phase 2 — Operational Time and Deterministic Automation

### Status: Planned

Phase 2 establishes the platform's operational time and automation foundation. The direction is:

```text
structured information → relationships → temporal information → events → calendar projections → tasks → reminders and attention management → scheduling → deterministic automation → later AI-assisted operations
```

The work is human-first, database-first, local-first and AI-independent. AI is explicitly excluded from initial Phase 2 implementation. Phase 2 is not in progress merely because it is planned; it becomes in progress only when authorised build work starts. It is complete only after its agreed capabilities work together coherently and pass the end-to-end completion review. The canonical scope, architecture, sequence, exclusions and completion criteria are in [the Phase 2 plan](docs/phase_2_plan.md).

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
