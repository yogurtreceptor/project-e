# Stage 1 Specification

Stage 1 establishes Operation Eddy as a local-first structured information platform.

## Goals

- Create a durable foundation for People, Organisations and Locations.
- Treat relationships as first-class records.
- Support creation, editing, viewing, navigation and search of structured information.
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

## Initial Domains

- Person: a canonical record for a real person.
- Organisation: a canonical record for a company, institution, group or other organisation.
- Location: a canonical record for a place, address or meaningful area.
- Relationship: a first-class connection between two entities.

Additional domains should wait until the entity and relationship foundation is stable.

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

- Users can maintain one canonical record per real-world person, organisation or location.
- Users can create and navigate relationships between entities.
- Users can search across core entity records.
- The platform remains usable without WAN access.
- Stage 1 features do not require AI, automation, login or scheduling.

