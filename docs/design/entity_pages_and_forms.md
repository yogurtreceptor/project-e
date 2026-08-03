# Entity Pages and Forms

Status: Current contract for canonical record pages and data entry. Exact domain fields live in `app/entities.py`; route families live in the [page catalogue](page_and_view_catalogue.md).

## Entity page model

Each canonical record has one page family over the same identity:

```text
Overview
├─ applicable Relationships / Family Tree
├─ Timeline / Documents / Map
└─ Audit and administrative history
```

Overview is read-only and answers: “What is this record, what matters now, and where should I go next?” It shows important current domain facts, omits empty/no-action groups, summarises expansive content and leaves raw IDs, storage metadata and routine history to Audit.

## Shared frame

The shared frame provides breadcrumbs, entity type, display identity, one or two useful disambiguating facts, direct **Edit** and recoverable **Delete**, a labelled **Views** control and restrained overflow actions such as Favourite, Add relationship and Merge.

One-line warnings appear beneath identity only when they affect interpretation or safe action. Provenance appears beside a fact when its source changes trust or meaning. The same related records are not repeated through generic cards and Relationship tables.

Specialised views repeat enough identity for orientation, retain explicit stable routes, explain qualifying data when empty and provide a textual alternative for complex visualisations.

## Domain composition

| Domain | Overview priorities |
| --- | --- |
| Person | Identity, birthday, direct contact, related Locations and concise Relationships; Journal remains Person-specific. |
| Organisation | Identity, aliases, classification, contact, key roles and Location Relationships. |
| Location | Place identity, address, coordinates/source and relevant occupants/assets. |
| Project | Identity, status, type and start/target/end milestones; related records remain peers. |
| Document | Safe file actions, purpose, identifier, dates/expiry, issuer/creator/subject Relationships and relevant provenance. |
| Asset | Identity, type/status, manufacturer/model/serial, value meaning and Location context. |
| Event | Read-only identity, Calendar, schedule/lifecycle and Relationships; creation and editing originate in Calendar workflows. |

Indexes are browse surfaces rather than generic CRUD tables. Identity comes first; subsequent columns use scannable domain facts instead of generic Notes. Filters retain state and distinguish an empty domain from no matches. Destructive row actions stay out of the primary scan path.

## Form contract

Create and edit use complete pages with one readable column, explicit context and a coherent server-side transaction. Field order normally follows identity/classification, status, domain facts, dates, contact/location/Relationships, optional detail, notes and any primary file payload.

Required fields are the minimum valid identity and are marked in text and markup. Optionality does not mean low importance: populated optional facts appear normally on edit and relevant Overviews.

### Progressive details and repeated values

**Add details** reveals definition-driven optional controls at their canonical position. Populated details are open on edit; hiding a control does not clear its submitted or saved value. Compound facts such as coordinates are revealed and validated together. This is presentation metadata, not user-defined schema.

Use repeated rows when values need labels, validation, ordering or individual lifecycle. Newline-backed input is acceptable only for simple same-kind values such as aliases. Taxonomy selectors browse/search complete paths; archived choices remain readable but unavailable for new selection. Reference selectors support search and independent multi-value selection where allowed.

Lookup assists entry but never becomes an invisible mutation or WAN requirement. Manual address/coordinate entry remains authoritative. Uploaded-file paths, MIME type and size are system-managed even when the Document form owns file selection.

### Validation and navigation

Server validation is authoritative. On failure:

- retain entered values and expanded details;
- show a concise linked error summary;
- associate each invalid control with corrective guidance;
- identify every field involved in a cross-field rule;
- keep duplicate warnings non-blocking only through explicit **Save anyway**.

Save returns to the canonical record in the originating context and may show a brief non-disruptive confirmation. Cancel returns without mutation. Leaving a dirty form through Cancel, navigation or browser history uses one **Keep editing / Discard changes** warning and restores focus correctly. No draft persistence exists without a separately authorised lifecycle.

## Relationships and consequential actions

Relationship creation starts from a named current entity, chooses an existing or new connected entity, shows only valid pair-aware roles from the current perspective and returns to context. Canonical direction remains an implementation detail; user-facing labels describe the connected entity naturally.

Soft delete, archive, Relationship removal, merge, import and permanent delete use language specific to their consequences. The final confirmation names the affected object, dependants, reversibility and recovery. Merge and import include previews; permanent deletion uses a dedicated recovery-protected page. A proposed or inferred change remains separate from canonical data until confirmed through normal validation, provenance and audit.

## State and accessibility rules

- Empty index: explain the domain and offer Create; empty filtered result: offer Clear filters.
- Empty specialised view: explain qualifying data and the relevant next action.
- Lookup/loading: identify the affected region, prevent duplicate submission and preserve manual entry.
- Save failure: retain values where safe and never imply a partial commit.
- Missing/recycled records: distinguish not found from recoverable deletion where known.
- Labels, error associations, progressive controls, Relationship selectors and confirmations remain keyboard and assistive-technology usable.
