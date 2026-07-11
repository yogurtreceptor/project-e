# Future Platform Direction

This document describes Project E's intended long-term evolution. It complements the current [architecture](architecture.md) and [Stage 1 specification](stage_1_spec.md); it does not authorise implementation or claim that future capabilities exist today.

## Platform before intelligence

Project E is a Personal Information Platform, not an AI application with a database attached. Its first obligation is to become genuinely useful to a human: trustworthy capture, clear navigation, durable relationships, strong retrieval and safe maintenance of private information.

AI is an important future capability, but it depends on foundations that are valuable in their own right:

- canonical entities and relationships
- deterministic rules and structured validation
- data-quality detection and repair workflows
- provenance and append-only audit history
- stable, machine-readable queries and commands
- safely machine-writable operations with confirmation, authorization and recovery boundaries

AI should build on these capabilities rather than replace or duplicate them.

## One capability surface

The long-term architecture should expose coherent platform capabilities to three kinds of consumer:

1. Human-facing interfaces.
2. Deterministic automation and integrations.
3. AI assistants and agents.

All three should read canonical data and use the same domain operations, validation and audit mechanisms. Presentation and authority may differ by consumer, but business rules should not. This avoids an “AI path” that can silently bypass constraints or create a parallel source of truth.

The present application is an in-process local web system, not yet a service-oriented or agent architecture. Near-term work should strengthen module boundaries and stable facades only where current platform needs justify them. A future machine interface can then be extracted from proven capabilities rather than predicted prematurely.

## Data and control

SQLite remains the canonical source of truth. Search indexes, derived timelines, summaries, embeddings or model context—if introduced—are disposable projections and must retain traceability to their canonical origins.

Machine-originated changes should carry provenance and pass through the same validation and integrity rules as human changes. The degree of confirmation, reversibility and authorization should reflect consequence. Local-first operation and private data ownership remain architectural constraints even when optional models or external integrations are considered.

Project E currently targets one private user. Future trusted multi-user support may introduce identity, permissions and attribution, but current documents and interfaces should avoid assumptions that permanently collapse “the user,” record ownership and action authorship into one concept.

## Odysseus

Odysseus is the leading candidate for Project E's future AI/agent layer. It is a future integration or fork target, not part of the current architecture and not a dependency around which Project E should now be reorganised.

Significant Odysseus work should wait until Project E is:

- independently useful to human users
- coherently machine-readable through stable platform capabilities
- safely machine-writable with validation, provenance, audit and review controls
- supported by strong domain, persistence and application boundaries

When those conditions hold, the integration should adapt Odysseus to Project E. Project E's canonical model, local-first constraints and safety boundaries should govern the design; the information platform should not be distorted to resemble Odysseus internals.

Questions to evaluate before integration include deployment and licensing fit, local/offline model support, tool and permission boundaries, durable task state, audit integration, context privacy, failure recovery and how a fork would be maintained. These are deliberate future decisions, not current architecture commitments.

## Decision gates

Movement toward advanced AI or agency should be driven by demonstrated platform readiness, not novelty. Useful gates include representative human use, stable domain operations, reliable import/export, explainable data-quality behavior, comprehensive mutation audit, recoverable writes and a clear authority model. The [roadmap](../ROADMAP.md) expresses the resulting capability phases.

## Deferred operational event coverage

The System Audit begins with mutations already recorded by the local platform. Its event vocabulary and filters are intentionally extensible. Future operational phases should add attributable events for automation execution, scheduled tasks, imports, AI suggestions, AI actions, synchronisation, background jobs, plugin activity and other operational platform work as those capabilities are deliberately introduced. Audit entries must accompany the capability that emits them; placeholder event streams should not be added in advance.

## Relationship knowledge evolution

Relationship confidence, source attribution, evidence, richer provenance and verification state require an explicit knowledge model rather than unrelated optional columns. Advanced graph traversal, indirect relationship discovery, querying and analytics likewise belong to later operational work. Both directions must preserve the canonical relationship record, explain where an assertion came from and keep derived conclusions distinguishable from user-confirmed facts.

Operational Intelligence should first use deterministic, explainable signals: duplicate or merge suggestions, missing fields or relationships, stale information, integrity analysis, rule-based recommendations, scheduled health checks and operational notifications. AI-assisted interpretation remains a later phase and must enter through the same platform capability and audit boundaries.
