# Entity Pages and Forms

Status: Working standard. This document defines the shared grammar for entity pages and deliberate data entry while preserving domain-specific layouts.

## Why these standards are combined

Entity viewing and editing are separate experiences, but they operate on one domain definition, canonical field order and context-return contract. Keeping their standards together prevents field importance, grouping and provenance placement from drifting between read and edit pages. Implementation should still use separate read-only pages and complete-page forms.

## Current implementation audit

### Established patterns worth retaining

- Every entity has a canonical route, list, read-only detail page, dedicated create/edit form and recoverable lifecycle.
- Entity identity, ordinary actions and definition-driven structured fields are rendered consistently.
- Progressive disclosure uses **Add details**, restores populated fields on edit and groups compound coordinates.
- Relationship creation starts from the known entity, distinguishes existing/new connected entities, uses perspective-specific labels and returns to context.
- Duplicate warnings link to candidates and require an explicit **Save anyway** choice.
- Location lookup assists but does not replace manual entry.
- Document uploads remain part of a Document record while file metadata is system-managed.
- Permanent deletion and import use review pages with explicit consequences; this is a stronger precedent than native confirmation dialogs.

### Prototype patterns that must not become standards

- All six domains share substantially the same long Overview page and section order.
- Every relationship group is rendered, including six empty groups, producing noise.
- `Related Entities` repeats information already presented in Relationships without a distinct task.
- Change History and raw Metadata are always visible beside ordinary domain information.
- Entity ID, timestamps, last viewed and relationship totals are default page content, conflicting with the philosophy's administrative-lens rule.
- Most domains use Notes as the second browse-table column, so indexes do not expose their most useful structured fields.
- The entity header exposes Back, Favourite, Create Relationship, Merge, Edit and Delete at once, with weak action hierarchy.
- Delete uses a browser confirmation from indexes and profiles; relationship and journal deletion can occur without an equivalent review step.
- Edit-form Cancel always returns to the domain index, even when editing began on an entity page.
- No unsaved-change warning or draft behaviour exists.
- Provenance is either absent near facts or buried in broad metadata/audit output.

These gaps are documented directions, not permission for a broad redesign in this branch.

## Entity-page model

Each entity owns a family of page-first views over the same canonical record:

```text
Entity identity
  ├─ Overview (default, concise, domain information)
  ├─ Relationships
  ├─ Timeline
  ├─ Documents
  ├─ Map / Family Tree / other domain-relevant view
  └─ Audit (administrative lens)
```

Not every entity exposes every view. A view exists only when it has meaningful content or a clear empty-state workflow. Adding a specialised view never creates duplicate persistence.

## Shared entity header

The header establishes identity and orientation before actions.

### Required content

- Entity type eyebrow or compact domain label.
- Primary display name as the page `h1`.
- One or two high-value identity facts when they materially disambiguate the record, such as Person birth date, Project status, Document purpose or Asset status.
- A labelled secondary **Views** control for specialised representations.
- One primary action, normally **Edit**, plus a restrained overflow for secondary and administrative actions.

### Action hierarchy

- **Edit** is the ordinary primary action.
- **Add relationship**, **Favourite** and comparable frequent actions are secondary or contextual.
- **Delete** is directly visible but uses danger styling only at final confirmation; **Merge**, record IDs and developer actions belong in an overflow or administrative view.
- Destructive action styling appears on the final confirmation action, not on a constantly prominent profile-header button.
- Back navigation uses breadcrumbs or a clear contextual return label; a generic `Back` button should not depend on presumed history.

Relationship views always expose an icon-only **Add relationship** control, whether the set is empty or populated. It uses the local SVG add symbol with an accessible name and tooltip.

### Warnings and provenance

- A warning that affects interpretation or safe action appears as a quiet one-line status beneath identity. It names the affected fact or operation and provides a **Details** link rather than a prominent callout.
- Data-quality findings do not become a permanent generic warning block when dismissed, irrelevant or purely administrative.
- Provenance appears next to a fact when source affects trust, freshness or meaning. A compact source label links to detail in Audit.
- Raw audit fields, storage paths, internal IDs and routine timestamps remain in the Audit/Developer lens.

## Overview purpose

Overview answers: “What is this entity, what matters most now, and where should I go next?” It is not a dump of every field or every available shared section.

- Show the most important, current domain facts.
- Prefer meaningful groups with concise labels over one undifferentiated definition list.
- Omit empty groups unless the empty state offers a useful action.
- Summarise expansive content and link to its specialised view.
- Do not repeat the same related records in both a relationship table and generic related-card grid without different purpose.
- Keep administrative and operational information out of Overview unless it changes an immediate decision.

## Shared grammar, domain-specific composition

The following compositions are initial standards to prototype. They deliberately differ while reusing identity, section, definition-list, compact-list, status, relationship-summary and provenance components.

| Domain | Overview priorities | Specialised views / projections | Avoid on default Overview |
| --- | --- | --- | --- |
| Person | Identity, birthday, phone numbers, email addresses, locations and relationship-derived addresses | Relationships, Family Tree, Timeline, Journal, Documents, Map, Audit | Raw metadata, six empty relationship groups, full audit stream |
| Organisation | Identity and aliases, classification, contact, key people/roles, locations, active projects | Relationships, Timeline, Documents, Map, Audit | Generic Notes as primary browse/profile content when structured facts exist |
| Location | Place identity, human-readable address, coordinate/source confidence, related occupants/assets | Map, Relationships, Timeline, Documents, Audit | Duplicate raw/formatted address fields without clear purpose |
| Project | Identity, status, immediate milestones, type, start/target/end | Timeline; future Tasks, Events and activity; Relationships, Documents, Audit | Treating related records as owned children or exposing empty generic sections |
| Document | Preview/open/download, name, purpose, identifier, date/expiry, issuer/creator/subject relationships, provenance | Relationships, Timeline, Audit; preview where safe | File path, raw MIME/size as dominant content, generic relationship dump ahead of the document |
| Asset | Identity, status, type, manufacturer/model/serial, value semantics, current location | Relationships, Timeline, Documents, Map, Audit | Ambiguous coordinate/location duplication or administrative metadata |

Phase 2 Event and Task layouts require their own domain composition work when implementation is authorised. They should inherit the page grammar, not be added speculatively here.

## Specialised views

- A specialised view has one primary representation or task: relationship exploration, family tree, timeline, documents, map or audit.
- It repeats enough entity identity to preserve orientation without reproducing the whole Overview.
- Links between equivalent specialised views preserve context where useful, as defined in [application shell and navigation](application_shell_and_navigation.md#context-preservation).
- A complex view provides a textual record list or equivalent accessible alternative.
- Empty views explain what qualifies for the view and provide an appropriate next action; they do not imply data loss.
- View routes should be explicit and stable enough to embed in future workspaces.

## Entity indexes

Domain indexes are browsing surfaces, not generic CRUD tables.

- Index title, concise purpose, primary create action and filter state are consistent.
- Columns are chosen per domain from stable entity metadata.
- Name/identity is always the first column and links to Overview.
- The next columns expose scannable domain facts, for example Person birth date, Organisation classification, Location city/state, Project status/target, Document purpose/expiry and Asset type/status.
- Notes are not a generic second column.
- Destructive actions do not sit in every row by default; use an overflow or record-level lifecycle workflow.
- Narrow layouts retain identity and one or two priority facts; less important columns may move to a disclosure region with headers preserved.

## Forms: experience contract

Forms optimise complete, deliberate entry. They remain manual-first, local-first and explainable. Lookup or reference tools assist entry without becoming required WAN dependencies or hidden mutation paths.

### Complete-page forms

- Create and edit use dedicated pages with an explicit form title and entity context.
- Edit begins from the canonical record and returns to the same entity/view context after Save or Cancel.
- The form uses the domain's canonical field order, shared with Overview grouping where practical.
- A long form may use in-page section navigation, but Save applies one coherent record transaction.
- Inline editing on Overview is not the default.

### Field grouping and order

Use this sequence, omitting irrelevant groups:

1. Identity and classification.
2. Current status or core operational facts.
3. Primary domain details.
4. Dates and lifecycle facts.
5. Contact, location or relationship-assisted facts.
6. Optional supporting detail.
7. Notes.
8. File input or other domain-specific payload where it is a primary workflow.

Groups need plain headings when more than visual spacing is required. Do not place every field in a separate panel.

### Required and optional fields

- Required fields are the minimum needed for a valid canonical record and are marked in text and markup.
- Optionality is not the same as low importance. A populated optional field appears normally on edit and where meaningful on Overview.
- Do not label every optional field “Optional”. Use **Add details** to keep initial creation focused.
- Sensitive fields are explicitly optional and never inferred from other records.

### Optional-detail controls

The current definition-driven **Add details** pattern is established and should be formalised:

- Choices appear at their canonical location rather than in a detached custom-fields section.
- Adding focuses the first control.
- Hiding an optional detail does not clear its submitted or saved value.
- The hide control states that behaviour through accessible name/help.
- Populated details are visible by default on edit.
- Compound facts such as coordinate pairs are added, validated and hidden together.
- This is presentation metadata, not a user-configurable schema.

### Repeatable fields

- Use repeatable row controls when values need individual labels, validation, ordering or lifecycle.
- A newline-backed input is acceptable only for simple same-kind values such as current Organisation aliases, with one value per line and clear help.
- Comma-delimited prose is not a repeatable-field model.
- Add/remove controls preserve keyboard focus and identify the affected value.
- Do not create a new entity type merely to support a visual repeatable control.

### Taxonomies and reference selectors

- Taxonomy selection combines hierarchy browsing and complete-path search, then displays the full selected path.
- Archived taxonomy entries remain visible on existing records but unavailable for new selection.
- Reference selectors support search and multiple independent values where the domain allows it.
- Large option sets must not render as an unmanageable unfiltered wall.
- Canonical unit entry stores through the existing measurement boundary while showing the chosen display unit.
- Reference data and taxonomies remain distinct concepts even if controls share styling.

### Validation

- Validate on the server for every submission; client validation improves immediacy but is not authoritative.
- Preserve entered values and expanded optional groups after validation failure.
- Show a concise error summary at the top. Invalid controls use the shared error treatment until corrected and remain associated with their field-level error for assistive technology.
- Explain the correction, not merely “invalid”.
- Cross-field rules such as coordinate pairs or start/end chronology identify all relevant fields.
- Warnings such as possible duplicates remain non-blocking only through a deliberate override action.

The current error summary is a useful baseline, but it is not associated with individual fields and therefore needs a later accessibility pass.

### Save, cancel and unsaved changes

- Use **Create [Entity]** for a create commit when extra clarity is useful; use **Save changes** for edit.
- Prevent accidental duplicate submission while a save is in progress.
- After save, show the canonical record in the originating context and a brief **Changes saved** toast at the top of the screen. The toast fades away without moving focus.
- Cancel returns to the originating entity/view without mutation.
- If the form is dirty, leaving through Cancel, breadcrumbs, sidebar or browser navigation requires one consistent unsaved-change warning.
- The warning offers **Keep editing** and **Discard changes**. It does not auto-save.
- No draft persistence exists in Phase 1. Future drafts require explicit lifecycle, ownership, audit and approval semantics.

### Destructive changes

- Soft delete, archive, relationship removal, merge, import and permanent delete use language specific to their different consequences.
- Consequential changes require explicit confirmation with the affected object, dependent records, reversibility and recovery behaviour.
- Permanent delete remains a dedicated page. Merge and import preview pages are established strong patterns.
- Reversible but important actions such as relationship removal use an accessible confirmation modal over the current page. Native browser confirmation may remain temporarily for low-complexity recoverable deletion but is not the long-term component standard.
- Do not place permanent delete beside ordinary Save.

### Future draft and approval support

Forms should be able to evolve into reviewable proposals without treating proposed data as canonical:

- Keep submitted values, proposal provenance and approval state distinct from the canonical entity.
- Review pages show proposed changes, current values, evidence and consequence before apply.
- Approval applies through the same validation, audit and recovery boundaries as direct editing.
- Do not implement draft or approval infrastructure until an authorised workflow needs it.

## Empty, loading, validation and error states

- Empty entity index: explain that no records exist and offer Create.
- Empty filtered index: state that no records match and offer Clear filters; do not imply the domain is empty.
- Empty specialised view: explain qualifying data and offer the relevant relationship/data action.
- Loading lookup: identify the affected lookup, disable repeat submission and keep manual fields usable.
- Lookup failure: state that lookup is unavailable and manual entry remains authoritative.
- Validation failure: retain values, focus or announce the summary and link to fields.
- Save failure: retain values where safe, explain recovery and never imply a partial commit.
- Not found/deleted: distinguish missing, recycled and inaccessible states when the repository can know the difference.

## Implementation acceptance checks

- Person, Document and Project prototypes are visibly domain-specific while sharing the same page grammar.
- Overview does not expose routine administrative metadata by default.
- Empty relationship groups and duplicated related-entity presentations are removed or given distinct purpose.
- Edit and Cancel return to the originating entity/view.
- Dirty forms have one consistent unsaved-change flow.
- Errors are associated with fields and preserve progressive-disclosure state.
- Consequential actions identify reversibility, dependencies and recovery.
- Reference, taxonomy and optional-detail controls pass keyboard and assistive-technology checks.
- No schema changes are made merely to force visual consistency.
