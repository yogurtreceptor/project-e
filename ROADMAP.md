# Roadmap and Future Direction

This document combines phased direction and longer-term possibilities. It is context, not implementation authority or a release checklist. An implementation prompt must explicitly authorise work.

Delivered behaviour belongs in the [Phase 1 specification](docs/phase_1_spec.md), [Phase 2 record](docs/phase_2_workspace.md) and completed entries in the [Phase 3 delivery and planning workspace](docs/phase_3_spatial_intelligence_planning.md). Unresolved engineering risks belong in the [technical-debt register](docs/reviews/technical_debt_register.md).

## Phase status

| Phase | Status | Outcome |
| --- | --- | --- |
| 1 · Information Platform | Complete | Canonical entities and Relationships; local documents; Search, Map and Timeline; taxonomies/reference data; audit/provenance; data quality, reviewed inference, merge and recovery. |
| 2 · Operational Time | Complete | Canonical Events and Calendars; recurrence; reminder policies and durable Inbox attention; registered scheduling and deterministic automation; Calendar interchange and portability. |
| 3 · Spatial Intelligence | In progress · N1–N2 complete | Canonical place foundations and the offline-first Map 2.0A canonical workspace are delivered; installed regional map/search data, journey planning, mobility/routing policy, travel-time and reachability tools remain planned. |

Phase closure means a representative development milestone is complete. It does not claim exhaustive verification, a stable public release or absence of ordinary maintenance defects.

The experimental Task subsystem was retired during Phase 2 after it produced no useful user data. Future work management requires a fresh authorised design and is not constrained by that model.

## Current direction: Spatial Intelligence

Phase 3 aims to make place, geometry, distance, movement, travel time and reachability useful across existing canonical records without turning maps or routing data into a rival source of truth.

Candidate outcomes include:

- stronger canonical Location and address semantics;
- optional regional spatial data packs;
- richer map layers and spatial record views;
- journey planning linked to Events and destinations;
- personal mobility profiles and explainable routing policies;
- travel-time matrices, nearby exploration, reachability and location comparison.

The desired end state can change as authorised work and real use expose better priorities. The Phase 3 workspace records decisions and open questions; it does not grant permission to implement its candidates.

## Platform before intelligence

Project E is a Personal Information Platform, not an AI application with a database attached. Its first obligation is dependable human use: trustworthy capture, clear navigation, durable relationships, strong retrieval and safe maintenance of private information.

AI and agent workflows are postponed indefinitely as a primary focus and are not assigned to a numbered phase. A small bounded capability may be considered only when it solves a demonstrated need and is explicitly authorised.

Any future human interface, deterministic integration or AI capability should use one shared capability surface:

- canonical entities and Relationships;
- validated domain operations;
- provenance and append-only audit;
- data-quality and review workflows;
- consequence-appropriate confirmation and authority;
- recoverable writes and local data ownership.

There must be no privileged “AI path” that bypasses business rules or creates a parallel source of truth. Search indexes, summaries, embeddings or model context—if ever introduced—are disposable traceable projections.

## Decision gates for bounded AI or agency

Before authorising an AI/agent capability, require:

1. a concrete problem that deterministic or ordinary UI work cannot reasonably solve;
2. representative human use of the affected domain;
3. stable machine-readable queries and validated write operations;
4. complete provenance, mutation audit and recovery for the proposed action;
5. a clear authority, review and failure model;
6. an acceptable local/offline and private-data boundary;
7. no autonomous external effect unless separately and explicitly authorised.

Read-only interpretation may justify a lighter gate than canonical mutation. Consequential changes always remain attributable, reviewable and reversible where practical.

## Odysseus

Odysseus is a possible future integration or fork target, not a current dependency or promise. Project E should not be reorganised around it in advance.

Serious evaluation waits until Project E is independently useful, coherently machine-readable and safely machine-writable through stable platform capabilities. If that point arrives, Project E's canonical model, local-first constraints and safety rules govern the integration—not Odysseus internals.

Questions for a future evaluation include licensing/deployment fit, local model support, tool and permission boundaries, durable task state, audit integration, context privacy, failure recovery and long-term fork maintenance.

## Other unnumbered directions

### Relationship knowledge

Confidence, source attribution, supporting evidence, richer provenance and verification state require a deliberate knowledge model. They should distinguish user assertions, evidence and derived conclusions rather than add unrelated optional columns to Relationships.

Advanced graph traversal and indirect discovery should remain explainable and preserve canonical Relationship identity. They are future work unless a concrete foundational need receives explicit authorisation.

### Contact methods and journals

Phone, email and website remain simple direct fields. A reusable Contact Method record becomes worthwhile only when multiple values, validity periods or communication history justify its lifecycle. It must not silently create a Communications domain.

Journal storage is entity-capable, but the current product exposes Person journals only. Generalisation should follow demonstrated workflows rather than a desire for symmetry.

### Operational coverage

Audit vocabulary grows with real capabilities. Future imports, synchronisation, plugins, model suggestions or external actions must add attributable audit records when those capabilities are implemented; placeholder event streams are not useful in advance.

Persistent System Health, external notification channels, mobile workflows, multi-user permissions, distributed workers/queues and cloud dependencies remain separately authorised directions, not implied next steps.

## Principles across every horizon

- SQLite and local files remain the canonical private store.
- Core operation remains local-first; optional network services are replaceable.
- One real object has one canonical record; views and caches remain traceable projections.
- Human users and any authorised machine consumers share validation, audit, provenance and recovery boundaries.
- Consequential canonical mutation requires explicit user control.
- Plans, roadmap entries and prototypes never authorise implementation by themselves.
