# Technical Debt Register

This is the live list of unresolved engineering debt. Completed work is recorded in the build history and should not remain here as an active warning.

## Dirty-form warning does not return focus to its invoker

Severity: medium

After cancelling the dirty-form warning, `app/static/dirty-form.js` focuses the first control in the form rather than the link or Cancel control that opened the dialog. This breaks predictable focus return for keyboard users.

Trigger: any unsaved entity, relationship or journal form where navigation is cancelled from the discard warning.

Direction: retain the invoking element when opening the dialog and restore focus to it on non-discard close, with a safe fallback only when it no longer exists. Add browser-level regression coverage for Cancel, Escape and focus return.

## Views and overflow menus have no explicit Escape or focus-return contract

Severity: medium

The entity Views and More actions use native `<details>` controls without menu-specific Escape handling or focus return. Their current interaction therefore depends on browser defaults and does not meet the documented predictable close/focus behaviour.

Trigger: keyboard use of the Person Views control or entity overflow menu.

Direction: define and implement one accessible disclosure/menu pattern that closes on Escape, returns focus to its summary/invoker, and preserves ordinary Enter/Space/Tab behaviour. Cover both controls with browser-level tests.

## Collapsed sidebar exposes nested destinations as unexplained icons

Severity: low

In the 56px collapsed sidebar state, nested navigation labels are visually hidden and no labelled flyout or temporary expanded panel is supplied. The HTML titles and accessible names remain, but the visual interface does not satisfy the shell standard for discoverable nested destinations.

Trigger: using Browse after collapsing the desktop sidebar.

Direction: provide a labelled nested-destination flyout or temporary expansion on keyboard and pointer interaction, then verify it at both required desktop resolutions.


## Search is in-memory and linear

Severity: medium

Entity and relationship search loads local records and filters in Python. This is appropriate for the current small-data Stage 1 application but may become slow after large imports.

Trigger: representative data shows noticeable latency or memory use, or a large import is planned.

Direction: move basic filtering into SQLite first; consider FTS5 only if indexed queries are insufficient. Preserve relationship-context matching and avoid an external search service.

## Map UI uses optional external resources

Severity: low

Leaflet assets, map tiles and Nominatim address lookup require WAN access. Core entity data, manual coordinates and non-map workflows remain local and usable without them.

Trigger: the map becomes a core offline workflow.

Direction: vendor client assets and support a deliberate local/offline tile strategy. Keep geocoding behind the existing replaceable provider boundary.

## Timeline is derived and limited

Severity: low

Entity timelines currently combine timestamps, relationships and edit history rather than a general event model.

Trigger: users need richer event types, ordering or provenance.

Direction: extend derived events first. Introduce persisted event records only when concrete workflows require them.

## Journals are People-only

Severity: low

Journal storage already links entries generically, but the UI remains intentionally unchanged and People-only. Journals and Documents are distinct: journals are internal observations and progress; Documents are real-world artefacts.

Trigger: a concrete Organisation, Project, Asset, Document or Location workflow needs dated internal observations.

Direction: make journal entries platform-wide first-class records linked to entities; do not embed journal streams in typed entity data.

## Contact details are single-value fields

Severity: low

Person and Organisation phone, email and website values are direct fields. This is intentionally simple but cannot express multiple labelled methods, verification or validity periods.

Trigger: a real workflow requires multiple contact points or lifecycle metadata.

Direction: consider a lightweight Contact Method entity or related record; do not introduce a broad Communications domain in Stage 1.

## Soft-deletable record consistency review

Severity: low

Entities and relationships use the Recycle Bin. Journal entries instead use domain-specific archive plus hard delete, while taxonomy entries are archived and data-quality dispositions are state transitions. These are deliberate semantic differences, not currently interchangeable deletion mechanisms.

Trigger: a requirement to recover deleted journals, taxonomy nodes or finding state.

Direction: evaluate that record type's lifecycle and user expectations before applying the generic Recycle Bin pattern; do not equate archive, dismissal and deletion automatically.
