# UI Principles

The Stage 1 UI should make structured information easy to enter, inspect and navigate.

## Core Experience

- Start with useful entity pages for People, Organisations and Locations.
- Make relationships visible and navigable from entity pages.
- Provide search before map-based exploration.
- Keep forms practical and understandable.
- Prefer dense, clear information layouts over decorative screens.

## Entity Pages

Each entity page should show:

- canonical name and type
- important typed profile fields
- aliases or alternate names
- relationship list or relationship panel
- notes
- timestamps or provenance where useful

Entity pages should help users notice likely duplicates and related records.

## Relationship Views

Relationships should not be hidden as secondary metadata.

The UI should allow users to:

- create relationships from entity pages
- inspect relationship details
- navigate to either connected entity
- understand direction or role semantics where they matter

## Search First

Search should be a primary navigation path for Stage 1.

Search should cover core entity names and enough profile data to find records quickly. Relationship-aware search can be added after the relationship model is stable.

## Maps Later

Maps are a later Stage 1 view over Location data.

Map UI should wait until Locations, relationships and search are useful without it. The map should reveal existing data; it should not drive the base architecture.

## Exclusions

The Stage 1 UI should not include chat, AI prompts, dispatcher controls, scheduling surfaces, login flows or automation dashboards.

