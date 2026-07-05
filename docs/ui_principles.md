# UI Principles

Project E's Stage 1 UI should stay quiet, structured and useful for repeated information work.

## Navigation

- Entity types are first-class navigation items.
- Relationships, Timeline and Map are global views over the same entity system. Search, Data Quality, Taxonomies and Recycle Bin are grouped under System Tools, while compact global search remains available in the header.
- Entity detail pages are the primary place to inspect and expand knowledge about a real-world object.

## Entity Pages

Entity pages should expose reusable sections rather than one-off layouts:

- Overview
- Geography where relevant
- Relationships
- Related Entities
- Notes, except that People use a chronological Journal
- Documents
- Timeline
- Metadata

The Universal Timeline is a chronological global view derived from those same canonical records. Each entry links to its originating entity or relationship. Filtering stays intentionally simple: entity type, date range, and directly related Person, Organisation or Project.

People, Organisations and Assets show geographic context through linked Location entities where appropriate. Assets may also show direct coordinate metadata. Location pages show their own address, coordinates, source and map jump.

Document pages show file metadata and a download link when a file has been uploaded. Other entity pages link to Documents through the relationship system.

## Forms

Forms should keep manual entry available. Helpful lookup tools may prefill fields, but users must be able to override structured fields, addresses and coordinates.

Entity forms should avoid generic `summary` fields. Notes are the flexible free-text area; important categories and statuses should be captured through controlled inputs.

Forms use definition-driven progressive disclosure to stay intentionally minimal without weakening the information model. **Add details** reveals optional controls inline at their canonical position; populated details are visible on edit and record pages and remain normal searchable, mergeable domain data. The small × control hides a detail without clearing its submitted value. Compound facts that are not meaningful independently, currently coordinate pairs, are added and hidden together. This is presentation metadata, not a user-defined custom-field system.

Person detail pages use short, separate journal entries instead of presenting the Person Notes field. Entries appear oldest first as message-style bubbles, show their creation time, and show an edited marker with the last edit time when changed. Archive is the prominent removal action; permanent delete remains available with quieter visual treatment.

Entity Delete actions move records to the Recycle Bin after a concise confirmation. Deleted entities must not appear in ordinary views. The Recycle Bin clearly separates recoverable deletion from archival, offers Restore, and places permanent deletion behind a dedicated confirmation page. That page states the action is irreversible and calls out relationships or dependent records that will also be removed.

Controlled fields use dropdowns for known statuses, preset-backed custom inputs where local vocabulary remains appropriate, and taxonomy comboboxes for reusable hierarchical classifications. A taxonomy combobox is one combined browse/search control: opening it shows the hierarchy, typing searches complete paths, and selecting any deep result stores its terminal entry while displaying the full path. Relationship choices add the perspective-specific role without hiding path context. Organisation classification and relationship types use this control; Project, Document and Asset type controls remain unchanged.

Possible duplicate entities should appear as a warning with links to existing records and an explicit Save anyway action. Warnings must not silently block legitimate records or become database uniqueness constraints.

People and Organisations keep phone/email as simple direct fields for now. People may record optional Sex for relationship label display, but it must never be required. Sex uses controlled values: Male, Female, Other and Unknown. Contact methods may later become first-class related records, but Stage 1 should not introduce a complex Communications domain.

Sensitive identity fields such as Ethnicities are optional and self-assessed. The interface may provide a searchable classification and allow multiple selections, but it must not infer ethnicity from nationality, language, family relationships or other stored data.

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

Detailed address fields and coordinates use progressive disclosure. Latitude and longitude are one compound detail and must be supplied together. Existing lookup and manual-address behaviour is otherwise unchanged.

Location address lookup should fill suburb, city, state, post code, country, coordinates and source when the provider returns those parts, while leaving all fields manually editable.

Document forms include a file upload control, while stored file path, MIME type and size remain system-managed metadata. Document descriptive fields and relationships remain editable.

Legacy issuer/creator text remains readable as an optional detail. New issuer and creator facts should use the existing Document-to-Person or Document-to-Organisation relationship types; integrating that relationship selection into Document create/edit is deferred until it can preserve transactional clarity without auto-creating entities from legacy text.

Asset value entry should accept whole numbers only. Users should not type a dollar sign into the field; read/detail pages display the value with a dollar sign.

## Inference Review

The deterministic engine may recompute suggestions automatically, but creating a canonical relationship is a consequential mutation and requires explicit user confirmation.

- Keep pending suggestions separate from real relationship records.
- Present one suggestion card at a time with clear Confirm and Reject actions, the people involved, rule/reason, source chain and any inferred date.
- Advance through the active stack after each decision and archive a batch automatically after its final review.
- Hide archived batches behind one explicit button; once shown, render every batch expanded so browser Find can search the complete history.
- Provide Undo for confirmed and rejected decisions. Undoing confirmation removes the relationship created by that decision and reopens the suggestion.
- Confirmed relationships use the normal edit/delete workflow; inference origin and evidence health belong in details/history, not in access restrictions.

## Map View

The map should behave like a view, not a separate workspace. Markers link back to canonical entity pages, and layer controls filter visible entity-derived markers without changing stored data.

The app should remain useful when map tiles or address lookup are unavailable.

Projects and Documents should not be shown as map layers or markers.
