# Documentation Audit

Date: 2026-06-22

## Overall Assessment

The documentation is mostly current and useful. It now frames Operation Eddy as a local-first Personal Operational Intelligence Platform rather than an AI Dispatcher. The main docs are concise enough for future AI coding sessions, while deeper docs capture architecture, ontology, database and UI principles.

No broad documentation rewrite is recommended during this review session.

## AGENTS.md

Status: good.

Findings:

- Clear project purpose, Stage 1 exclusions and implementation preferences.
- Useful workspace-specific tool notes.
- Concise enough for future Codex/Claude sessions.

Recommended changes:

- No immediate change required.
- Later, add a short pointer to `docs/reviews/claude_handoff.md` if that file becomes the standard mixed-agent onboarding document.

## README.md

Status: good but minimal.

Findings:

- Gives run/test instructions and database location.
- Does not mention Stage 1 exclusions or active domains.

Recommended changes:

- Add one short "Stage 1" paragraph listing active domains and exclusions.
- Keep it short; do not duplicate `docs/stage_1_spec.md`.

## PROJECT_GOAL.md

Status: aligned, but currently modified before this review session.

Findings:

- Strong current framing: AI may eventually consume data, but should not become the platform.
- Mentions first core areas as People, Organisations, Locations and Relationships, while active Stage 1 docs/code also include Projects, Documents and Assets.

Recommended changes:

- Clarify that People, Organisations, Locations and Relationships are core foundations, and Projects/Documents/Assets are current Stage 1 domains proving the shared architecture.
- Do not edit until the pre-existing modifications are understood.

## ROADMAP.md

Status: too terse.

Findings:

- Lists milestones but does not show status.
- Does not explain that Projects, Documents, Assets and Maps are already active.
- Currently modified before this review session.

Recommended changes:

- Add milestone statuses: done, active, next, deferred.
- Keep to one page.
- Do not edit until pre-existing modifications are understood.

## docs/vision.md

Status: good.

Findings:

- Clear current identity and exclusions.
- Concise and useful.

Recommended changes:

- No immediate change required.

## docs/stage_1_spec.md

Status: good.

Findings:

- Accurately lists People, Organisations, Locations, Projects, Documents, Assets and Relationships.
- Clearly states non-goals.
- Maps acceptance criteria are useful.

Recommended changes:

- When Import becomes active, add acceptance criteria before implementation.
- Consider marking Maps as implemented if milestone tracking is introduced.

## docs/architecture.md

Status: useful and mostly current.

Findings:

- Accurately describes entity, relationship, discovery, document and geographic architecture.
- Contains several "Architectural correction" notes that are useful history but may become noisy over time.

Recommended changes:

- Later, move correction history into ADR/build log and keep `docs/architecture.md` focused on current architecture.
- Do not rewrite now.

## docs/ontology.md

Status: useful but detailed.

Findings:

- Good explanation of entities, controlled values, relationship types and geography.
- Relationship type section is long, but that reflects current complexity.

Recommended changes:

- If relationship taxonomy is refactored, update this doc to summarise principles and link to the registry rather than restating every type.

## docs/database_design.md

Status: good.

Findings:

- Accurately documents SQLite, typed tables, legacy columns, controlled fields, relationship storage and map storage.
- Does not yet mention a schema version/migration ledger because none exists.

Recommended changes:

- After migration ledger work, add a short "Schema Versioning" section.
- Add file lifecycle policy when Document deletion/replacement behaviour is decided.

## docs/ui_principles.md

Status: good.

Findings:

- Accurately captures dashboard/navigation-first and entity-page-first UI direction.
- Relationship workflow guidance matches current implementation.

Recommended changes:

- Add guidance for domain list columns if list pages are improved.
- Keep form guidance concise.

## ARCHITECTURE_DECISIONS.md

Status: useful.

Findings:

- ADR format is documented.
- Current ADRs cover map, G-NAF and added domains.

Recommended changes:

- Add future ADRs for schema versioning, relationship taxonomy registry and any import/export architecture.
- Avoid recording small refactors.

## docs/build_log.md

Status: useful history, poor handoff context.

Findings:

- Detailed and chronological.
- Too long for low-context future agent onboarding.

Recommended changes:

- Keep as history.
- Do not rewrite.
- Use `docs/reviews/claude_handoff.md` as the compact future-agent briefing.

## Outdated AI Dispatcher Framing

Findings:

- No active code or docs frame the project as an AI Dispatcher.
- References to AI, chat and dispatcher are exclusion/history statements.

Recommended changes:

- No removal required. These exclusions are useful guardrails.

## Repeated Information

Findings:

- Stage 1 exclusions appear in several docs. This repetition is acceptable because it prevents scope drift.
- Architecture details are repeated across architecture, ontology and database docs.

Recommended changes:

- Keep the exclusions repeated.
- Avoid adding new long-form docs unless they replace or summarise existing material.

## Future Agent Clarity

Findings:

- `AGENTS.md` is the best session instruction file.
- `docs/reviews/claude_handoff.md` should become the practical mixed-agent briefing.

Recommended changes:

- In a future small doc update, link `docs/reviews/claude_handoff.md` from `README.md` or `AGENTS.md` if the user wants it treated as canonical handoff context.
