# Build History

Historical summary only. Current behaviour is documented in the Stage 1 specification and reference docs; current priorities are in the roadmap and technical-debt register.

## 2026-07-05

Added versioned, checksummed portable bundles containing consistent SQLite snapshots and referenced uploaded documents; staged import preview and confirmation; clean-target enforcement; automatic recovery backups for import, merge and permanent deletion; a deliberate recovery command; and focused round-trip, checksum, rollback, recovery and offline-operation coverage. Entity merge now preserves and repoints recycled relationships, while merge and permanent-delete previews distinguish their exact active/recycled effects.

## 2026-07-11

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
