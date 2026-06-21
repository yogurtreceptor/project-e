# UI Principles

Operation Eddy's Stage 1 UI should stay quiet, structured and useful for repeated information work.

## Navigation

- Entity types are first-class navigation items.
- Relationships, Search and Map are global views over the same entity system.
- Entity detail pages are the primary place to inspect and expand knowledge about a real-world object.

## Entity Pages

Entity pages should expose reusable sections rather than one-off layouts:

- Overview
- Geography where relevant
- Relationships
- Related Entities
- Notes
- Attachments
- Timeline
- Metadata

People and Organisations show geographic context through linked Location entities. Location pages show their own address, coordinates, geocoding source and map jump.

## Forms

Forms should keep manual entry available. Helpful lookup tools may prefill fields, but users must be able to override structured fields, addresses and coordinates.

Location forms include address lookup as an aid, not as a requirement. Records can be saved without coordinates.

## Map View

The map should behave like a view, not a separate workspace. Markers link back to canonical entity pages, and layer controls filter visible entity-derived markers without changing stored data.

The app should remain useful when map tiles or address lookup are unavailable.
