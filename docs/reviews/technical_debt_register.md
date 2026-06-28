# Technical Debt Register

This is the live list of unresolved engineering debt. Completed work is recorded in the build history and should not remain here as an active warning.

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

## Domain list pages are generic

Severity: low

Browse tables do not yet expose the most useful structured fields for every domain.

Direction: derive list columns from entity metadata so, for example, project status and document or asset type can be scanned without opening each record.

## Timeline is derived and limited

Severity: low

Entity timelines currently combine timestamps, relationships and edit history rather than a general event model.

Trigger: users need richer event types, ordering or provenance.

Direction: extend derived events first. Introduce persisted event records only when concrete workflows require them.

## Contact details are single-value fields

Severity: low

Person and Organisation phone, email and website values are direct fields. This is intentionally simple but cannot express multiple labelled methods, verification or validity periods.

Trigger: a real workflow requires multiple contact points or lifecycle metadata.

Direction: consider a lightweight Contact Method entity or related record; do not introduce a broad Communications domain in Stage 1.
