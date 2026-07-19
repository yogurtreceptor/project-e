# Build History

Historical summary only. The Stage 1 specification and reference documents define current behaviour; the roadmap defines direction; the technical-debt register contains unresolved work.

## 2026-07-19 — Phase 2A canonical Event lifecycle

- Added Event as a stable canonical entity type with migration-safe typed storage referencing Calendars and Event categories.
- Implemented validated timed and all-day creation, editing, cancellation state, archive/unarchive, default resolution, audit, provenance and entity history through a dedicated Event service.
- Kept Event creation out of generic entity routes so the next UI milestone can implement the approved Calendar-originated workflow.
- Extended portable-database validation and System Audit vocabulary for the new Event contract and archive lifecycle.

## 2026-07-19 — Phase 2A temporal foundation

- Began authorised Phase 2 implementation with shared, standard-library temporal normalization for IANA timezones, UTC instants, bounded timed intervals and end-exclusive all-day intervals.
- Added migration-safe Calendar and Event-category reference storage with deterministic fresh-install defaults, archive state and database-enforced default uniqueness.
- Covered UTC conversion, invalid/ambiguous daylight-saving times, interval validation, fresh schema creation and existing-database adoption with focused tests.
- Kept canonical Events, Calendar projections, recurrence and reminder precedence for later Phase 2A milestones.

## 2026-07-19 — Phase 2 plan consolidation

- Restructured the canonical Phase 2 plan around Phases 2A–2F, consolidating approved behaviour, architecture, sequencing, completion criteria and exclusions without starting implementation.
- Aligned supporting Calendar and reminder terminology: Calendars are local Event configuration records, while calendar views remain derived projections.

## 2026-07-12 — Phase 2 operational-planning decisions

- Aligned the architecture and design-document status language with the completed desktop shell, theme foundation and representative domain-page conversion; preserved the remaining external human visual and assistive-technology QA as an open verification item.

- Recorded the initial user-centred Event, Calendar, Task, reminder, Inbox, System Health and local archive decisions in the canonical Phase 2 plan.
- Kept Phase 2 implementation unstarted: this session defines authorised future design direction, not delivered product behaviour.

## 2026-07-12 — Design-system route conversion and verification

Completed the authorised design catch-up across the implemented Stage 1 interface.

- Delivered a shared entity frame: breadcrumbs, clear identity and action hierarchy, grouped Views, restrained overflow actions, quiet integrity warnings, and accessible icon-only relationship creation.
- Added deliberate form safeguards: entity edit Cancel returns to the canonical record, dirty entity/relationship/journal forms warn before discard, validation summaries link to invalid described controls, and successful saves show a non-disruptive **Changes saved** toast.
- Built domain-specific Person, Document and Project Overviews. Person addresses derive from Location relationships; Document pages lead with safe open/download actions; Project pages foreground status and milestones.
- Converted indexes, Search, Timeline, Map, Family Tree, relationship workflows and System Tools to shared collection, state, confirmation and semantic-token patterns. Map failure guidance and Family Tree keyboard/text alternatives are included.
- Completed locally executable verification: 182 tests, compilation, temporary-server smoke workflows with fictional data, contrast/token/icon/confirmation audits, and focused structural keyboard checks passed.
- Reconciled the repository documentation: restored chronological build history, aligned design audits with delivered shared feedback and domain compositions, and made known keyboard/sidebar gaps explicit rather than implying acceptance.

Human visual and interactive keyboard review at both target resolutions and themes remains outstanding. The known dirty-form, Views/overflow and collapsed-sidebar accessibility follow-ups are recorded in the technical-debt register.

## 2026-07-11 — Shared design foundation, shell and navigation

- Established the semantic design-token foundation in `foundation.css`: dark fallback with system-selected light theme, one `#66ccff` accent primitive, local/system Roboto fallback, keyboard focus treatment and reduced-motion protection.
- Added shared actions, controls, panels, badges, notices, busy/empty/loading/failure states, linked validation and accessible recoverable-delete confirmation.
- Created the Project E tilted E mark and local 24px SVG icon set, with safe local serving and accessible decorative/meaningful-icon conventions.
- Replaced the prototype header with the persistent desktop shell: Browse sidebar, session-only collapsed state, Search, skip navigation and current-route hierarchy. Added deterministic Super Key Go aliases (`map`, `bin`, and Person-context `tree`) with an explicit Search fallback.
- Recorded the experience philosophy, design-system standards, page catalogue and authorised implementation plan that guided this work.

## 2026-07-05 — Portability, recovery and Phase 1 closure

- Added versioned, checksummed export bundles containing a consistent SQLite snapshot and referenced documents; staged import preview/confirmation; clean-target protection; and recovery backups for import, merge and permanent deletion.
- Added the deliberate command-line recovery workflow, including preview and confirmed replacement modes.
- Preserved and repointed recycled relationships during merge, with previews that distinguish active and recycled effects.
- Closed Phase 1 as a development milestone after representative verification and recorded the planned Phase 2 temporal and deterministic-automation architecture, including the `Australia/Brisbane` platform timezone and a separable in-process scheduler.
- Added contributor, security and copyright documentation.

## 2026-07-04 — Taxonomies, discovery and domain refinement

- Replaced legacy gendered family relationship records through a dry-run-first, backup-protected converter with direction-safe neutral mappings.
- Added a reusable local three-level taxonomy framework and migrated Organisation classification and Relationship types to it, including hierarchy search, direction metadata and audit history.
- Consolidated Search, Data Quality, Taxonomies and Recycle Bin under System Tools while retaining global Search access.
- Cleaned up domain semantics: Documents use relational issuer/creator facts and MIME-backed format; Assets no longer duplicate Document types; Projects gained target dates/timeline events; Organisations gained repeatable aliases.
- Expanded definition-driven progressive disclosure and added targeted typed fields, duplicate matching and timeline/search participation.

## 2026-06-28 — Integrity, provenance and platform services

- Added schema migration tracking, structured-value validation, duplicate detection and preview-first entity merging with edit history.
- Added relationship integrity auditing, exact-duplicate prevention, structured discovery filters, robust Document ownership/cleanup and definition-driven inline entity creation.
- Delivered deterministic, explainable family-relationship inference as reviewable suggestions with provenance, suppression, archived batches and undo.
- Added registry-driven audit/provenance, advanced search, data quality and the Universal Timeline; restored separate entity change history and backfilled legacy audit history.
- Added soft deletion for every entity type, a Recycle Bin, dependency-aware permanent deletion, reference data/unit normalisation, multi-value People reference fields and People journals.

## 2026-06-27 — Maintainable module boundaries

Refactored without changing public contracts: page rendering moved to `app/view_pages/`; persistence was split into schema and repository modules behind `app/db.py`; relationship metadata moved to a grouped catalogue; and document/relationship workflows moved out of the HTTP handler. Added boundary-focused regression coverage.

## 2026-06-22 — Structured forms and relationship workflows

Standardised entity forms and controlled values. Redesigned relationship creation around a named current entity and connected entity, pair-aware canonical relationship types, perspective-correct labels, safe inline creation and date certainty. Added reusable Family Tree graph extraction and deterministic layered SVG layout.

## 2026-06-21 — Initial local information platform

Established the standard-library Python/SQLite application with reusable CRUD definitions, first-class relationships, entity profiles, discovery, favourites, recent records and geography. Added Projects, Documents and Assets through the shared architecture, local Document uploads, and optional Leaflet/OpenStreetMap/Nominatim map support. Early attachment and organisation-address concepts were superseded by first-class Documents and Location relationships.
