# Technical Debt Register

This is the live list of unresolved engineering debt. Completed work is recorded in the build history and should not remain here as an active warning.

## Collapsed sidebar exposes nested destinations as unexplained icons

Severity: low

In the 56px collapsed sidebar state, nested navigation labels are visually hidden and no labelled flyout or temporary expanded panel is supplied. The HTML titles and accessible names remain, but the visual interface does not satisfy the shell standard for discoverable nested destinations.

Trigger: using Browse after collapsing the desktop sidebar.

Direction: provide a labelled nested-destination flyout or temporary expansion on keyboard and pointer interaction, then verify it at both required desktop resolutions.


## Search is in-memory and linear

Severity: medium

Entity and relationship search loads local records and filters in Python. This is appropriate for the current small-data Phase 1 application but may become slow after large imports.

Trigger: representative data shows noticeable latency or memory use, or a large import is planned.

Direction: move basic filtering into SQLite first; consider FTS5 only if indexed queries are insufficient. Preserve relationship-context matching and avoid an external search service.

## Map UI uses optional external resources

Severity: low

Leaflet assets, map tiles and Nominatim address lookup require WAN access. Core entity data, manual coordinates and non-map workflows remain local and usable without them.

Trigger: the map becomes a core offline workflow.

Direction: vendor client assets and support a deliberate local/offline tile strategy. Keep geocoding behind the existing replaceable provider boundary.

## Local static-asset cache policy

Severity: low

Application icons, stylesheets and scripts are same-origin local HTTP resources; they are not WAN/HTTPS traffic. The local static handler currently sends no explicit browser cache policy, so repeated page loads may request each small asset again. This is acceptable for the current small asset set and makes local development immediately reflect changes.

Trigger: the local asset set becomes materially larger, page-load traces show avoidable repeat transfers, or packaging the application for routine use needs a predictable offline performance policy.

Direction: add conservative cache headers for versioned or fingerprinted static assets, with a deliberate invalidation strategy on application update. Do not implement session-only cache clearing: normal browser cache management and asset versioning are safer and avoid stale UI after an update.

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

Direction: consider a lightweight Contact Method entity or related record; do not introduce a broad Communications domain merely to extend the Phase 1 direct-field model.

## Soft-deletable record consistency review

Severity: low

Entities and relationships use the Recycle Bin. Journal entries instead use domain-specific archive plus hard delete, while taxonomy entries are archived and data-quality dispositions are state transitions. These are deliberate semantic differences, not currently interchangeable deletion mechanisms.

Trigger: a requirement to recover deleted journals, taxonomy nodes or finding state.

Direction: evaluate that record type's lifecycle and user expectations before applying the generic Recycle Bin pattern; do not equate archive, dismissal and deletion automatically.
