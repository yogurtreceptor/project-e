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
- Documents
- Timeline
- Metadata

People, Organisations and Assets show geographic context through linked Location entities where appropriate. Assets may also show direct coordinate metadata. Location pages show their own address, coordinates, geocoding source and map jump.

Document pages show file metadata and a download link when a file has been uploaded. Other entity pages link to Documents through the relationship system.

## Forms

Forms should keep manual entry available. Helpful lookup tools may prefill fields, but users must be able to override structured fields, addresses and coordinates.

Location forms include address lookup as an aid, not as a requirement. Records can be saved without coordinates.

Document forms include a file upload control, but Document records remain normal entities with editable metadata and relationships.

## Map View

The map should behave like a view, not a separate workspace. Markers link back to canonical entity pages, and layer controls filter visible entity-derived markers without changing stored data.

The app should remain useful when map tiles or address lookup are unavailable.

Projects and Documents should not be shown as map layers or markers.
