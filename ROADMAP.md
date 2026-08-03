# Roadmap

This roadmap is directional guidance, not implementation authority or a rigid release checklist. Delivered Phase 1 behaviour belongs in the [Phase 1 specification](docs/phase_1_spec.md); completed Phase 2 scope and evidence belong in [the Phase 2 workspace](docs/phase_2_workspace.md); evolving Phase 3 direction belongs in [the Spatial Intelligence planning workspace](docs/phase_3_spatial_intelligence_planning.md); unresolved engineering risks belong in the [technical-debt register](docs/reviews/technical_debt_register.md).

## Phase 1 — Information Platform

Phase 1 establishes canonical People, Organisations, Locations, Projects, Documents, Assets and Relationships; local SQLite persistence; reusable profiles and retrieval; maps and local documents; journals and timelines; taxonomies and reference data; audit history and provenance; duplicate merging; explainable data-quality checks and reviewed deterministic inference; and recoverable entity and relationship lifecycles.

### Status: Complete

Pull request #1 is closed and Phase 1 is complete enough to close as a development milestone. Its closure is based on representative verification, not exhaustive manual testing of every capability. Residual defects may still be found and are handled through normal maintenance without reopening Phase 1 as a whole. The closure record is the [Phase 1 review](docs/reviews/phase_1_exit_review.md).

## Phase 2 — Operational Time and Deterministic Automation

### Status: Complete

Phase 2 establishes the platform's operational time and automation foundation. The direction is:

```text
structured information → relationships → temporal information → events → calendar projections → reminders and attention management → scheduling → deterministic automation
```

The work is human-first, database-first, local-first and AI-independent. Phases 2A–2F and the authorised Event, Calendar and operational refinements closed after integrated review of Calendar/Event, reminder/Inbox, scheduler, deterministic automation, portability and recovery behaviour. The unsuccessful experimental Task subsystem was retired on 2026-08-01; future work management is neither promised nor constrained by that design. Persistent System Health, AI and external side effects remain outside the completed milestone. The canonical scope, delivery record, exclusions and closure evidence are in [the Phase 2 workspace](docs/phase_2_workspace.md) and [Phase 2 closure review](docs/reviews/phase_2_exit_review.md).

## Phase 3 — Spatial Intelligence

### Status: Planning in progress

Make location, geometry, distance, movement, travel time and reachability useful operational concepts across Project E. The intended direction includes stronger Location semantics, rich local spatial data, Map 2.0, journey planning, personal mobility profiles, explainable routing policies, travel-time and reachability tools, and integration with Events and other canonical records.

The phase is framed by a desired end state rather than a fixed implementation sequence. Capabilities may be revised, dropped or added as authorised work and real use establish what is practical. The [Phase 3 Spatial Intelligence planning workspace](docs/phase_3_spatial_intelligence_planning.md) records accepted direction, candidate capabilities and open questions; it is not implementation authority.

## Unnumbered future directions

AI assistance and agent workflows are postponed indefinitely as a primary focus rather than promised for Phase 4 or another numbered milestone. Small, bounded and attributable capabilities may still be considered through explicit authorisation when they solve a demonstrated need and remain grounded in canonical records, validation, privacy, audit, recovery and user control. [Odysseus](docs/future_direction.md#odysseus) remains a possible future integration or fork target, not a present dependency.

## Deferred relationship evolution

Do not treat richer relationship evidence as an incidental field addition. Confidence scores, confidence/source attribution, evidence/provenance, richer provenance and verification workflows require a deliberate model that distinguishes asserted facts, supporting material and review state. They are planned after the Phase 1 foundation unless a concrete foundational need changes that priority.

## Across every phase

- SQLite and the local database remain the canonical source of truth.
- Core operation remains local-first; optional services must be replaceable.
- Human users, deterministic operations and any future explicitly authorised assistance converge on shared platform capabilities.
- Validation, relationships, audit history, provenance, recovery and user control remain strategic infrastructure.
- Roadmap entries never authorise implementation on their own.
