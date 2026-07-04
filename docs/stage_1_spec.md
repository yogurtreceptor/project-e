# Stage 1 Specification

Stage 1 establishes Project E as a local-first structured information platform.

## Goals

- Create a durable foundation for People, Organisations, Locations, Projects, Documents and Assets.
- Treat relationships as first-class records.
- Support creation, editing, deletion, viewing and browsing of core entity records.
- Keep data local by default.
- Prefer simple, free and open-source technology.
- Produce a useful UI early without expanding scope into later stages.

## Non-Goals

Stage 1 does not include:

- AI
- chat interfaces
- dispatcher architecture
- decision support
- autonomous goal-directed workflows
- scheduling
- unreviewed consequential actions or autonomous external side effects
- login, accounts or trusted multi-user workflows
- mobile access, cloud dependencies or WAN-dependent core operation

Deterministic, local and explainable assistance and internal maintenance are permitted when they preserve user control. A consequential mutation requires explicit user confirmation. Optional network aids are permitted only when core records and workflows remain usable without them. Simple import and export tools are permitted when they support data entry, backup or migration.

## Domains

- Person: a canonical record for a real person.
- Organisation: a canonical record for a company, institution, group or other organisation.
- Location: a canonical record for a place, address or meaningful area.
- Project: a canonical record for ongoing work or an area of responsibility.
- Document: a canonical record for a document, optionally backed by a local uploaded file.
- Asset: a canonical record for a physical or digital item.
- Relationship: a first-class connection between two entities.

Projects, Documents and Assets are included to prove the entity architecture scales beyond the initial domains without special-case pages or relationship models.

## Delivery Status

Delivered foundations include architecture, the shared entity model, relationships, entity pages, search, maps, additional domains, schema governance, data-quality safeguards, entity-local and universal derived timelines, and deterministic family inference.

Import/export and further UI polish remain planned. See the [roadmap](../ROADMAP.md) for current ordering; this specification defines scope rather than task priority.

The current product serves one private user without authentication. This is a present scope choice, not a permanent prohibition on future trusted multi-user support.

## Acceptance Criteria

- Users can maintain one canonical record per real-world person, organisation, location, project, document or asset.
- Users can create, edit, soft-delete, restore, permanently delete, browse and view detail pages for People, Organisations, Locations, Projects, Documents and Assets.
- Soft-deleted entities are absent from normal lists, search, maps, discovery and relationship navigation. The Recycle Bin lists every deleted entity type and provides restore and confirmed permanent deletion.
- Restoring an entity exposes its preserved relationships only when their other endpoint is active; it never restores another deleted entity. Soft deletion never cascades to related entities.
- Archived means inactive content retained in its normal domain workflow; deleted means an entity is hidden platform-wide and recoverable from the Recycle Bin.
- Person detail pages provide chronological plain-text journal entries with create, edit, archive and delete actions. Active entries show their creation time and edited entries also show their last edit time; archive is the primary removal path.
- Person create and edit forms provide an Add field section for optional data. Alias, Nickname, Height, Weight, Languages, Nationalities and Ethnicities are available there and appear in the Person overview only when populated. Height and Weight use unit-aware canonical storage; Languages, Nationalities and Ethnicities select one or more shared reference records. Ethnicity uses the detailed ABS ASCCEG 2025 catalogue and is always an explicit, self-assessed value rather than an inferred attribute.
- The local reference-data catalogue provides a broad IANA-derived set of languages and countries/regions, plus reusable states/regions, currencies and measurement units, without runtime network access. Multi-value reference controls support type-to-filter search and independent selection/removal.
- Users can upload an individual file to a Document entity; replacement cleans up the superseded unreferenced file, soft deletion retains the current file for restoration, and permanent deletion cleans it up when unreferenced.
- Users can connect Documents and Assets to other entities through relationships.
- Users can browse one chronological Universal Timeline derived from dated fields and relationship dates across all supported entity types. Entries link to their canonical origin and can be filtered by entity type, date range, or a related Person, Organisation or Project.
- Safe deterministic family suggestions are reviewed before becoming normal editable relationships; automatic candidate recomputation does not bypass that confirmation boundary.
- Confirmed inference-created relationships retain provenance; rejected evidence is suppressed until it materially changes; completed review batches remain available in searchable history with undo.
- The platform remains usable without WAN access.
- Stage 1 features do not require AI, autonomous automation, login, scheduling or WAN access.

Relationship creation and navigation are implemented as reusable Stage 1 platform features.

Organisation classification and Relationship types are database-backed taxonomy paths containing Type, optional Subtype and optional Specific subtype. The local Taxonomies page creates and archives reusable entries. Archived branches remain visible on existing records but unavailable for new selection; archiving never rewrites canonical records. Relationship definitions retain one canonical stored direction and derive inverse display from metadata attached to their taxonomy entry.

Taxonomy-backed forms use one combined combobox for hierarchy browsing and full-path search, including direct selection of deep nodes. The Taxonomies manager separates Organisation and Relationship taxonomies, displays hierarchy and archive status, and retains confirmed create/archive workflows. Search, Data Quality, Taxonomies and Recycle Bin are available from the System Tools hub at their existing routes.

People browse pages show name and date of birth. Person journals are intentionally People-only in this milestone and do not include tags, sources, confidence, revision history or universal-timeline integration.

## Maps Acceptance

The Maps milestone adds a geographic view without changing the Stage 1 boundaries.

Implemented scope:

- interactive Leaflet/OpenStreetMap map page
- Location, Organisation, People and Asset layer controls
- markers generated from Location coordinates and `located_at` relationships
- Asset markers generated from direct coordinates or `located_at` relationships
- marker popups linking back to canonical entity pages
- address lookup for Location forms through a replaceable geocoding boundary
- manual address and coordinate editing
- graceful omission of records without valid coordinates

Out of scope remains routing, journey planning, traffic analysis, public transport, AI, decision support and autonomous automation.

Projects and Documents are never map markers.

## Platform-derived views

Stage 1 includes generic mutation audit events and lightweight provenance; registry-driven advanced query filters; deterministic data-quality findings with saved dispositions; and entity-local plus Universal Timeline views derived from canonical dates and relationships. The Universal Timeline de-duplicates relationship events, links every entry to its canonical entity or relationship, and supports simple entity/date/direct-relation filters. Audit and timeline histories remain separate.

### Family graph view

The relationships family-tree view renders the largest complete connected family component with fixed generation rows, adjacent partner units and independent exact-parent-set child connectors. It does not draw sibling links or centre layout around a selected person. Highlighting is visual only and cannot alter geometry. The reusable selector/layout boundary also supports a bounded person-centred subgraph for a future record-local view.
