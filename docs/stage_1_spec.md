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
- complex automation
- scheduling
- login or multi-user accounts
- WAN or cloud-dependent features

Simple import and export tools are permitted when they support data entry, backup or migration.

## Domains

- Person: a canonical record for a real person.
- Organisation: a canonical record for a company, institution, group or other organisation.
- Location: a canonical record for a place, address or meaningful area.
- Project: a canonical record for ongoing work or an area of responsibility.
- Document: a canonical record for a document, optionally backed by a local uploaded file.
- Asset: a canonical record for a physical or digital item.
- Relationship: a first-class connection between two entities.

Projects, Documents and Assets are included to prove the entity architecture scales beyond the initial domains without special-case pages or relationship models.

## Milestones

1. Architecture
2. Foundation
3. Entity Model
4. Relationships
5. Entity Pages
6. Search
7. Maps
8. Import
9. Timeline
10. Additional Domains
11. Polish

Maps are a later Stage 1 view over Location data. Search and relationship navigation come first.

## Acceptance Criteria

- Users can maintain one canonical record per real-world person, organisation, location, project, document or asset.
- Users can create, edit, delete, browse and view detail pages for People, Organisations, Locations, Projects, Documents and Assets.
- Users can upload an individual file to a Document entity.
- Users can connect Documents and Assets to other entities through relationships.
- The platform remains usable without WAN access.
- Stage 1 features do not require AI, automation, login or scheduling.

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

Out of scope remains routing, journey planning, traffic analysis, public transport, AI, decision support and automation.

Projects and Documents are never map markers.
