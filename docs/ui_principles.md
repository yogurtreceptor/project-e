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

People, Organisations and Assets show geographic context through linked Location entities where appropriate. Assets may also show direct coordinate metadata. Location pages show their own address, coordinates, source and map jump.

Document pages show file metadata and a download link when a file has been uploaded. Other entity pages link to Documents through the relationship system.

## Forms

Forms should keep manual entry available. Helpful lookup tools may prefill fields, but users must be able to override structured fields, addresses and coordinates.

Entity forms should avoid generic `summary` fields. Notes are the flexible free-text area; important categories and statuses should be captured through controlled inputs.

Controlled fields use dropdowns when the value must be one of the known statuses, and preset-backed custom inputs when Stage 1 needs a sensible list without blocking local user vocabulary. Current controlled fields are organisation type, project type, project status, document type, asset type and asset status.

Possible duplicate entities should appear as a warning with links to existing records and an explicit Save anyway action. Warnings must not silently block legitimate records or become database uniqueness constraints.

People and Organisations keep phone/email as simple direct fields for now. People may record optional Sex for relationship label display, but it must never be required. Sex uses controlled values: Male, Female, Other and Unknown. Contact methods may later become first-class related records, but Stage 1 should not introduce a complex Communications domain.

Relationship creation should be entity-first and perspective-based:

- Start from the known entity page.
- Choose either Existing entity or New entity.
- Show only the selected workflow so users do not scroll through irrelevant fields.
- Existing entity workflow shows entity selection, relationship selection, dates, notes and save. A searchable selector can be added later without changing the workflow split.
- New entity workflow reuses the standard entity creation fields (including Birthday for People), followed by relationship selection, dates, notes and save. Definition changes therefore apply to both creation paths.
- Ask what the named connected entity is in relation to the named current entity; avoid ambiguous wording such as "this entity" once an entity name is available.
- Show only relationship roles valid for the selected entity pair.
- Save back to the original entity page so context is not lost.

The relationship selector should use short plain role labels from the user's perspective, such as Daughter, Father, Employee or Employer. Family choices should use neutral relationship definitions underneath; sex-specific labels are display output, not separate required relationship types. When creating a new entity, the relationship question should update live as the new entity name changes.

Location forms include address lookup as an aid, not as a requirement. Records can be saved without coordinates.

Location address lookup should fill suburb, city, state, post code, country, coordinates and source when the provider returns those parts, while leaving all fields manually editable.

Document forms include a file upload control, while stored file path, MIME type and size remain system-managed metadata. Document descriptive fields and relationships remain editable.

Asset value entry should accept whole numbers only. Users should not type a dollar sign into the field; read/detail pages display the value with a dollar sign.

## Map View

The map should behave like a view, not a separate workspace. Markers link back to canonical entity pages, and layer controls filter visible entity-derived markers without changing stored data.

The app should remain useful when map tiles or address lookup are unavailable.

Projects and Documents should not be shown as map layers or markers.
