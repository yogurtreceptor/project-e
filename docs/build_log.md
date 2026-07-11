# Build History

## 2026-07-11 - Entity frame and deliberate forms

Added shared entity breadcrumbs, identity/action hierarchy, grouped Views, restrained overflow actions, quiet integrity warnings and accessible icon-only relationship creation. Edit forms now Cancel to the canonical record and all entity forms use a consistent Keep editing/Discard changes warning for dirty navigation, while retaining existing linked validation, progressive disclosure, save feedback and recoverable-delete confirmation.

## 2026-07-11 - Super Key Go

Replaced the reserved shell placeholder with a deterministic, keyboard-operable Super Key dialog. Exact `map` and `bin` aliases navigate to ordinary routes, Person-context `tree` opens Family Tree with the current Person selected, and unknown terms offer an explicit canonical Search link. Added focused shell, static-serving and alias-boundary coverage without dependencies, schema changes or fuzzy/entity lookup.

Historical summary only. Current behaviour is documented in the Stage 1 specification and reference docs; current priorities are in the roadmap and technical-debt register.

## 2026-07-05

Added versioned, checksummed portable bundles containing consistent SQLite snapshots and referenced uploaded documents; staged import preview and confirmation; clean-target enforcement; automatic recovery backups for import, merge and permanent deletion; a deliberate recovery command; and focused round-trip, checksum, rollback, recovery and offline-operation coverage. Entity merge now preserves and repoints recycled relationships, while merge and permanent-delete previews distinguish their exact active/recycled effects.

## 2026-07-11

Completed the brand and local-asset foundation with a bold tilted Project E mark and a coherent 24px SVG set for shell groups, current domains/views, Search, Super Key and shared actions/status. The transitional shell now uses Project E identity and consistent labelled navigation icons while preserving its existing composition for the dedicated sidebar step; focused checks cover accessible icon semantics, asset geometry and safe local serving.

Completed the shared-component and interaction-state foundation. Entity and relationship validation now links top summaries to visibly invalid, programmatically described controls with adjacent messages while retaining submitted values. Added the quiet warning status row with a **Details** link and verified the complete Step 3 action, form, feedback, toast and modal contract through focused tests, the full suite, compilation and running-app smoke checks.

Replaced native entity soft-delete confirmation prompts with a shared accessible modal that names the record and recoverable consequence. The native dialog contains focus while open, supports Escape/cancel, returns focus to its invoker, and deliberately leaves permanent delete, merge and import on their dedicated review pages.

Added the shared passive **Changes saved** toast to successful entity and relationship create/edit redirects. It uses a polite status region without moving focus, fades from the top of the screen, removes its one-request URL marker from browser history, and does not render on ordinary or failed form responses.

Extended the shared-component foundation with accessible error-summary alert markup, semantic success notices and warnings, compact status badges, busy panels, and reusable empty/loading/failure states. Field-level validation association and confirmation modal remain pending within Step 3.

Started the shared-component catch-up with a bounded action/form-state slice. Primary, secondary, quiet and final-danger actions now share semantic hover, active and disabled treatments; inputs use semantic rest, disabled, read-only and invalid states; and the existing error summary uses the shared danger roles. Toast, modal and the remaining Step 3 interaction-state work are still pending.

Implemented the global design token and accessibility base: one `#66ccff` primitive feeds semantic actions, selection and focus; charcoal dark is the fallback with an operating-system-selected light companion; shared roles now cover surfaces, text, borders, statuses, graph/map series, typography, spacing, dimensions, radii and elevation. Applied a local-first Roboto fallback stack, a keyboard-only 2px focus ring and reduced-motion protection, with focused token-integrity and representative WCAG contrast tests. Page-specific component conversion remains incremental.

Added the visual-neutral design-foundation stylesheet seam while preserving the existing shell and route composition. The global stylesheet now imports one incremental foundation entry point, the local static handler serves it, focused checks cover the seam and shared CSS integrity, and the Family Tree no longer references an undefined text token.

Added a design implementation-readiness register that separates remaining product-owner answers from prototype evidence, defines the foundation catch-up sequence and gives explicit completion evidence for the current prototype-to-design implementation gap. No application UI or domain behaviour changed.

Refined the implementation-readiness register after product-owner review: chose system-theme selection with dark fallback, `#66ccff` as the single base accent primitive, charcoal dark surfaces, original corporate/industrial E-mark direction, local SVG sizing, direct unique Super Key aliases, grouped Views, document/project priorities, visible Edit/Delete, and active Inbox counts. Reduced the immediate decision set to plain-language questions that genuinely need an answer before prototyping. No application UI or domain behaviour changed.

Recorded further design decisions for Super Key shortcuts, Person contact-card priorities and relationship-derived addresses, one-column forms, top-screen fading save toasts, confirmation modals, icon-only relationship addition, and top-summary/error-treated validation. Deferred long-list navigation and Family Tree node-click behaviour until implementation. No application UI or domain behaviour changed.

Chose quiet one-line warning statuses with **Details** links beneath entity identity instead of prominent warning callouts. No application UI or domain behaviour changed.

Added an authorised, step-sized design catch-up implementation plan for hand-off to implementation agents. It covers the foundation through verification, specifies scope and acceptance checks for each step, and makes deferred decisions and stop conditions explicit. No application UI or domain behaviour changed.

Recorded product-owner design decisions for a dark-first, system-preference theme model; restrained light-blue/black/white palette direction; local SVG icons; entity-context Super Key placement and behaviour; desktop-only viewport scope; session-only sidebar collapse; restrained Home/Inbox relationship; and density, page-composition and visual-layer guidance. Specialised entity views now sit behind a labelled secondary Views control, and keyboard navigation uses a consistent 2px focus ring. Provenance presentation remains deferred. No application UI or domain behaviour changed.

Added the version-controlled Project E Experience Philosophy and a post-prototype design-documentation layer covering design-system foundations, the application shell and navigation, entity pages and forms, data presentation, operational attention and a route-level interface audit. Recorded which current patterns should be formalised, which remain prototype debt, the product-owner decisions still required and the dependency path to later implementation. No application UI or domain behaviour changed.

Closed PR #1 and recorded Phase 1 as complete enough to close as a development milestone after representative rather than exhaustive verification. Documented the planned Phase 2 operational time and deterministic-automation foundation, its architectural boundaries, implementation sequence, exclusions and end-to-end completion review. No application features were implemented by this documentation alignment.

Clarified the planned Phase 2 temporal and operational defaults: `Australia/Brisbane` as the initial platform timezone, deterministic short-period recurrence shifting, local-inbox-only notification delivery with startup recovery, and an in-process scheduler designed for later separation into a local worker. No application features were implemented.


Added the repository's initial community health documentation: contributor guidance, structured bug and feature issue forms, and a pull request checklist. Added a security policy using GitHub private vulnerability reporting and clarified the project's current source-available, all-rights-reserved copyright status pending any future explicit software licence.

Cleaned the Phase 1 domain model: removed free-text Document issuer in favour of existing creator/issuer relationships; separated Document purpose from MIME-backed format; removed the overlapping Document-like Asset type; added Project target dates and timeline events; and introduced normalized repeatable Organisation aliases used by forms, search, merges and duplicate review. Recorded the active-development preference for clean architecture over compatibility layers and documented the deferred platform-wide Journal direction.

Extended definition-driven progressive disclosure across Organisations, Locations, Projects, Documents and Assets. Optional details now appear inline in canonical order, use **Add details**, can be hidden without clearing values, and support compound coordinate pairs. Added Project ended/completed date, Document identifier and expiry date, and Asset manufacturer/model through additive typed columns, including chronology validation, identifier duplicate matching, search participation and timeline events.

## 2026-07-04

Added a dry-run-first, backup-protected converter for pre-taxonomy gendered family relationship records, including direction-safe canonical mappings and duplicate detection.

Refreshed the repository documentation around the Project E name and long-term Personal Information Platform direction. Added a phased capability roadmap, future architecture and Odysseus guidance, and a concise GitHub landing page with philosophy, status, architecture and documentation navigation.

Unified Organisation and Relationship taxonomy selection into one full-path searchable, hierarchy-browsable combobox; clarified taxonomy management hierarchy, status and creation controls; and consolidated Search, Data Quality, Taxonomies and Recycle Bin under a System Tools hub while retaining existing routes and global header search.

Added a reusable local three-level taxonomy framework and management page. Migrated Organisation classification and Relationship types to taxonomy assignments with legacy-safe archived mappings, searchable hierarchical selection, database-backed direction/inverse metadata, audit events and regression coverage.

Added a Universal Timeline derived from canonical dated entity fields and relationship dates across every supported entity type, with direct origin links, chronological de-duplication, entity/date/related-record filters and an extensible date-field registry.

Added platform-wide soft deletion for every entity type, default exclusion from discovery and relationship-derived views, a Recycle Bin with selective restore, dependency-aware confirmed permanent deletion, preserved audit history and restore-safe Document file ownership.

Added People journals as separate chronological plain-text records with create, edit, archive and secondary delete actions, message-style Person detail rendering, created/edited timestamps and migration-safe storage. Updated the People browse table to show DOB instead of Notes.

Added reusable local reference-data catalogues and unit normalization with canonical length, mass and temperature storage. Integrated optional Person Height, Weight, Languages and Nationalities through shared measurement/reference field strategies, including multi-value references, display-unit conversion and merge-safe persistence.

Expanded Languages and Nationalities from demonstrative seeds to a reproducible, pinned IANA-derived local catalogue. Added searchable checkbox pickers so large reference lists filter as the user types while retaining multiple independent selections.

Added optional multi-value Person Ethnicities using the same searchable reference picker and a reproducible 276-group catalogue generated from ABS ASCCEG 2025. Documented ethnicity as explicit self-identification that must never be inferred from other records.

Added reusable on-demand optional field presentation for entity forms, with Alias and Nickname as the first Person optional fields, additive typed-column migration and populated-only detail display.

## 2026-06-28

Refactored the family tree into reusable full-component and person-centred graph selection feeding one deterministic family-specific layout engine. Added birth-date-stable ordering, geometry-neutral selection highlighting, and complex blended-family stress coverage.

Clarified the durable Stage 1 boundary between permitted deterministic assistance and prohibited autonomous automation, and aligned repository scope, architecture and terminology documentation.

Completed schema migration tracking, structured value validation, duplicate detection and preview-first entity merging with edit history. Added relationship integrity auditing and exact-duplicate prevention, structured discovery filters, robust Document file ownership/cleanup, and definition-driven inline entity creation in relationship workflows. Implemented deterministic family inference as reviewable suggestions with provenance, suppression, archived batches and undo. Expanded automated coverage for these behaviours.

Added registry-driven audit/provenance, advanced search, data-quality, and real-world timeline infrastructure.

Restored entity change history as a separate audit section alongside real-world timelines, including legacy edit-history visibility, and backfilled generic audit history for existing canonical records while linking relationship changes to both endpoint entities.

## 2026-06-27

Refactored large modules without changing their public contracts: page rendering moved under `app/view_pages/`, persistence moved into schema and repository modules behind `app/db.py`, relationship metadata moved into a grouped catalogue, and document/relationship workflow services moved out of the HTTP handler. Added contract and regression coverage around the new boundaries.

## 2026-06-22

Standardised structured entity forms and controlled values. Redesigned relationship creation around the current entity and a named connected entity, added pair-aware canonical relationship types, perspective-correct labels, safe inline creation, date certainty and legacy-key compatibility. Added reusable family-tree graph extraction and deterministic layered SVG layout. Reviewed architecture and identified the maintainability and data-quality work subsequently completed on 27–28 June.

## 2026-06-21

Established the standard-library Python/SQLite local application, reusable entity definitions and CRUD, first-class relationships, entity profiles, search/favourites/recent discovery, and the geographic view. Added Projects, Documents and Assets through the shared architecture; introduced local Document uploads and optional Leaflet/OpenStreetMap/Nominatim map support. Recorded G-NAF as an optional future Australian address index. Early attachment and organisation-address concepts were superseded by first-class Document entities and Location relationships.

Completed the Platform Maturity / Pre-Operational Intelligence milestone: relationships now use migration-safe soft deletion, appear in the Recycle Bin, restore with stable identity and provenance, and remain aligned with audit and derived timeline behaviour. Added a filterable System Tools Audit over normalized action and record-kind projections while retaining legacy events. Defined Phase 1 exit criteria, separated foundational gaps from Operational Intelligence and later AI work, and recorded deferred relationship knowledge, graph and future operational audit evolution.

## 2026-07-11 — Desktop shell and Browse navigation

- Replaced the horizontal prototype header with the persistent Project E shell and 240px/56px Browse sidebar states.
- Added session-only collapse persistence, complete current-route hierarchy, distinct Search access, skip navigation and accessible current/parent state.
- Reserved the documented Super Key location for the separately scoped Step 6 interaction.
