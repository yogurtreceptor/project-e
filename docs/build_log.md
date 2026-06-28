# Build History

Historical summary only. Current behaviour is documented in the Stage 1 specification and reference docs; current priorities are in the roadmap and technical-debt register.

## 2026-06-28

Clarified the durable Stage 1 boundary between permitted deterministic assistance and prohibited autonomous automation, and aligned repository scope, architecture and terminology documentation.

Completed schema migration tracking, structured value validation, duplicate detection and preview-first entity merging with edit history. Added relationship integrity auditing and exact-duplicate prevention, structured discovery filters, robust Document file ownership/cleanup, and definition-driven inline entity creation in relationship workflows. Implemented deterministic family inference as reviewable suggestions with provenance, suppression, archived batches and undo. Expanded automated coverage for these behaviours.

## 2026-06-27

Refactored large modules without changing their public contracts: page rendering moved under `app/view_pages/`, persistence moved into schema and repository modules behind `app/db.py`, relationship metadata moved into a grouped catalogue, and document/relationship workflow services moved out of the HTTP handler. Added contract and regression coverage around the new boundaries.

## 2026-06-22

Standardised structured entity forms and controlled values. Redesigned relationship creation around the current entity and a named connected entity, added pair-aware canonical relationship types, perspective-correct labels, safe inline creation, date certainty and legacy-key compatibility. Added reusable family-tree graph extraction and deterministic layered SVG layout. Reviewed architecture and identified the maintainability and data-quality work subsequently completed on 27–28 June.

## 2026-06-21

Established the standard-library Python/SQLite local application, reusable entity definitions and CRUD, first-class relationships, entity profiles, search/favourites/recent discovery, and the geographic view. Added Projects, Documents and Assets through the shared architecture; introduced local Document uploads and optional Leaflet/OpenStreetMap/Nominatim map support. Recorded G-NAF as an optional future Australian address index. Early attachment and organisation-address concepts were superseded by first-class Document entities and Location relationships.

- 2026-06-28: Added registry-driven audit/provenance, advanced search, data-quality, and real-world timeline infrastructure.
