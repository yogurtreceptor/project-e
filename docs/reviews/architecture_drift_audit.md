# Architecture Drift Audit

Date: 2026-06-22

Current direction: entity-first, relationship-first, local-first, dashboard/navigation-first, no AI in Stage 1, no dispatcher-first architecture, no command-first UX.

## 1. Active Domains Exceed Some Short Summaries

Location: `PROJECT_GOAL.md`, `AGENTS.md`, some top-level framing

Issue: Some summaries emphasise People, Organisations, Locations and Relationships, while active code/docs include Projects, Documents and Assets.

Why it conflicts: Future agents may think Projects, Documents and Assets are experimental or out of scope, even though they are implemented as Stage 1 entity domains.

Recommended correction: Clarify that People/Organisations/Locations/Relationships are core foundations, and Projects/Documents/Assets are current Stage 1 domains implemented to prove extensibility.

## 2. Relationship Taxonomy Is Becoming Code-First Rather Than Model-First

Location: `app/relationships.py`

Issue: Relationship definitions, labels, pair support, display semantics and legacy behaviour are hard-coded in one Python module.

Why it conflicts: A relationship-first platform needs the relationship model to be easy to inspect and evolve. Code-heavy taxonomy makes domain modelling harder for future agents.

Recommended correction: Refactor into a compact relationship registry/data structure with tests for pair availability and label direction. Keep runtime behaviour unchanged.

## 3. View Layer Has Become A Central UI Monolith

Location: `app/views.py`

Issue: The module contains layout, dashboard, entity pages, forms, relationship workflow, search, map rendering and inline scripts.

Why it conflicts: Dashboard/navigation-first and multiple-view architecture require UI surfaces to evolve independently. A monolithic view module makes future UI work risky.

Recommended correction: Split by UI surface while preserving current simple server-rendered HTML architecture.

## 4. Storage Layer Mixes Persistence With Application Queries

Location: `app/db.py`

Issue: Schema management, migration compatibility, CRUD, validation, discovery, search and relationship persistence are all colocated.

Why it conflicts: Local-first storage quality is a core priority. Mixed responsibilities increase migration and data-quality risk.

Recommended correction: Separate schema/migration, entity repository, relationship repository and search/discovery concerns.

## 5. Local-First Has Optional WAN Dependencies In Map And Geocoding

Location: `app/views.py` map page, `app/geo.py`

Issue: Map page loads Leaflet and tiles from external URLs, and address lookup calls Nominatim.

Why it conflicts: Stage 1 should not depend on WAN for normal operation.

Recommended correction: Keep these features optional and document fallback behaviour. Consider vendoring Leaflet assets later if maps become core. Do not make lookup mandatory.

## 6. One Canonical Record Principle Has No Product Support Yet

Location: entity create/edit flows in `app/web.py`, validation in `app/db.py`

Issue: Users can create duplicate entities without warnings.

Why it conflicts: The project principle says one canonical record per real-world object.

Recommended correction: Add duplicate warnings based on display name and key structured fields. Start as non-blocking warnings before enforcing uniqueness.

## 7. Forms Still Have Weak Free-Text Areas

Location: `app/entities.py`, `app/views.py`

Issue: Phone, email, website, issuer, state, country and relationship notes are free text. Some of this is acceptable now, but it may accumulate structured facts in notes.

Why it conflicts: Stage 1 prioritises structured information.

Recommended correction: Keep simple contact fields for now. Add validation/normalisation where cheap. Consider Contact Method entities later only when multiple contact points or validity metadata become necessary.

## 8. Timeline Exists As A Placeholder More Than A Model

Location: `app/views.py` timeline section

Issue: Timeline displays created/modified and recent relationship-added items but has no event model.

Why it conflicts: A placeholder can be mistaken for a committed architecture.

Recommended correction: Keep it as a read-only derived section for now, or explicitly document it as derived metadata until an event model is justified.

## 9. Import Appears On Roadmap Before Duplicate And Schema Governance

Location: `ROADMAP.md`, `docs/stage_1_spec.md`

Issue: Import is a listed milestone, but duplicate handling and schema versioning are not yet in place.

Why it conflicts: Import can damage canonical-record quality if introduced before data-quality safeguards.

Recommended correction: Make duplicate warnings and migration/schema ledger prerequisites for substantial import work.

## 10. Build Log Is Too Detailed For Low-Context Handoff

Location: `docs/build_log.md`

Issue: It is useful history but long and implementation-heavy.

Why it conflicts: Future AI agents need concise, current context.

Recommended correction: Keep the build log as history. Use `docs/reviews/claude_handoff.md` for low-context handoff.

## 11. Command-First UX Has Not Drifted Into The Product

Location: active UI

Issue: None found.

Why it conflicts: Not applicable. The app is dashboard/navigation/entity-page driven.

Recommended correction: Continue avoiding command palettes, chat prompts or dispatcher-style interaction in Stage 1.

## 12. AI Dispatcher Remnants Are Guardrails, Not Active Drift

Location: docs search results in `AGENTS.md`, `docs/*`, `PROJECT_GOAL.md`, `ARCHITECTURE_DECISIONS.md`

Issue: AI, chat and dispatcher are mentioned as exclusions or future-stage notes.

Why it conflicts: They do not currently conflict; they clarify scope.

Recommended correction: Do not remove these references wholesale. Keep them concise as Stage 1 guardrails.
