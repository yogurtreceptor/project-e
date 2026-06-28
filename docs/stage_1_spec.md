# Stage 1 Specification

Stage 1 establishes Operation Eddy as a local-first structured information platform.

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
- login or multi-user accounts
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

Delivered foundations include architecture, the shared entity model, relationships, entity pages, search, maps, additional domains, schema governance, data-quality safeguards, a derived timeline and deterministic family inference.

Import/export and further UI polish remain planned. See the [roadmap](../ROADMAP.md) for current ordering; this specification defines scope rather than task priority.

## Acceptance Criteria

- Users can maintain one canonical record per real-world person, organisation, location, project, document or asset.
- Users can create, edit, delete, browse and view detail pages for People, Organisations, Locations, Projects, Documents and Assets.
- Users can upload an individual file to a Document entity; replacement and Document deletion clean up unreferenced owned files.
- Users can connect Documents and Assets to other entities through relationships.
- Safe deterministic family suggestions are reviewed before becoming normal editable relationships; automatic candidate recomputation does not bypass that confirmation boundary.
- Confirmed inference-created relationships retain provenance; rejected evidence is suppressed until it materially changes; completed review batches remain available in searchable history with undo.
- The platform remains usable without WAN access.
- Stage 1 features do not require AI, autonomous automation, login, scheduling or WAN access.

Relationship creation and navigation are implemented as reusable Stage 1 platform features.

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
