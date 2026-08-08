# Database Design

SQLite is Project E's canonical store. `app/db.py` is the public persistence facade; `app/db_schema.py` owns connections, current-schema creation, the append-only migration ledger and repair. This document describes the current database, not the chronological implementation diary.

## Core rules

- Keep one canonical row identity for each real-world object and Relationship.
- Use foreign keys and database uniqueness for referential integrity and logical idempotency; do not rely only on in-process coordination.
- Store canonical facts once. Search, maps, timelines, Calendar views and data-quality findings are projections.
- Separate canonical, configuration, derived/operational and historical records because their lifecycles differ.
- Keep uploaded files outside SQLite under ignored local storage; store only safe relative metadata in Document rows.
- Evolve forward. Remove obsolete current models rather than maintain duplicate truth.

## Schema evolution

`schema_migrations(migration_id, applied_at)` records every applied step. `SCHEMA_MIGRATIONS` in `app/db_schema.py` is ordered and append-only: an identifier that may have run must never be renamed, reordered or removed.

Startup performs three actions in one database connection:

1. Create the migration ledger if absent.
2. Apply each missing migration and record it only after success.
3. Run idempotent current-schema repair for definition-driven tables, columns, constraints and seed catalogues.

Fresh and upgraded databases therefore converge on the same current schema. Historical Task migrations remain in the ledger, but retirement migration `20260801_31_retire_task_subsystem` removes the obsolete Task schema and refuses to proceed if Task data or Relationships exist. The current schema has no Task tables or Task entity type.

For a schema change, update the current-schema creator/repair path, add a forward migration, preserve existing identifiers, and test both a fresh database and a representative upgrade. A development reset is preferable to a permanent compatibility layer when no user data needs preservation.

## Current table groups

| Group | Tables | Purpose |
| --- | --- | --- |
| Migration | `schema_migrations` | Applied migration identifiers. |
| Canonical identity | `entities`; `people`, `organisations`, `locations`, `projects`, `documents`, `assets`, `events` | Shared identity plus one typed row for each entity. |
| Canonical place facts | `location_addresses`, `location_geometries`, `location_provider_references` | Address and geometry assertion history plus replaceable provider identity references. |
| User-owned Map state | `map_feature_lists`, `map_feature_list_memberships` | Portable favourites/named-list identity and external provider-feature membership; not provider facts or canonical Locations. |
| Journey configuration | `mobility_profiles`, `routing_policies` | Stable user-owned identity, revision and provider-independent definitions; not routes or provider settings. |
| Relationships and journals | `relationships`, `journal_entries`, `entity_aliases` | First-class links, timestamped observations and alternate names. |
| Controlled/reference data | `reference_data_types`, `reference_data_items`, `entity_reference_values`, `measurement_units`, `entity_measurements`, `taxonomies`, `taxonomy_entries`, `relationship_type_definitions` | Shared catalogue values, normalized measurements and runtime classifications. |
| Calendar and recurrence | `calendars`, `birthday_event_links`, `calendar_edit_history`, `event_recurrences`, `event_recurrence_exceptions`, `event_recurrence_splits`, `event_icalendar_identities` | Local Calendar configuration, Birthday links, recurrence and import identity. |
| External Calendar state | `calendar_subscriptions`, `external_calendar_events` | Read-only source configuration and last-known-good cache. |
| Attention and execution | `reminder_policies`, `reminder_overrides`, `inbox_items`, `inbox_item_actions`, `scheduled_jobs`, `job_runs`, `scheduler_checkpoints`, `automation_rules`, `automation_runs` | Policy, current attention, append-only transitions and deterministic runtime history. |
| Review and traceability | `audit_events`, `audit_event_records`, `provenance_metadata`, `entity_edit_history`, `data_quality_finding_state`, `inference_batches`, `inference_suggestions` | Audit, provenance, merge/edit history, finding disposition and inference review. |

The schema itself, not this table, is authoritative for exact columns and constraints.

## Canonical entities

`entities` stores shared identity: `id`, `type`, display name, notes, timestamps, favourite/recent metadata and `deleted_at`. Each canonical entity has exactly one matching typed row. `entities.summary` remains a legacy search/storage field but is not an active form field.

Typed storage is definition-driven. Missing active columns can be added during repair, and the `entities.type` check is rebuilt when the active domain set changes. Field renames may copy data from declared previous columns; obsolete fields are then removed by an explicit migration when keeping them would create ambiguity.

Important domain boundaries:

- Person display name is derived from given and family names.
- Locations own purpose-specific current or historical address assertions and role-specific current or historical geometries. People and Organisations connect to Locations through Relationships instead of copying place facts.
- Documents own local file metadata and use Relationships for issuer/creator meaning.
- Events share entity identity, belong to one local Calendar and use the standard Relationship table rather than Event-specific endpoint foreign keys.

Aliases, multi-value references and measurements use normalized external tables rather than repeated typed columns. Reference items are stable local catalogue records. Measurements store a canonical decimal value plus the user's display unit. Small domain-specific controlled values may remain validated text when a shared catalogue would add no value.

Structured dates, coordinates and whole-number Asset values are normalized and validated before writes. Location geometry stores a validated geometry type and compact canonical JSON coordinate array in WGS84 longitude/latitude order. Point, line, multi-line, polygon and multi-polygon nesting is supported without requiring a spatial extension; polygon rings must be closed. The projection index selects current/preferred assertions by Location, purpose or role, while partial unique indexes permit at most one preferred address per purpose and one preferred geometry per role.

`locations` now carries only the typed-row identity. `location_addresses` keeps physical, postal and delivery assertions with independent current/preferred state, confidence and source snapshots. `location_geometries` keeps representative point, boundary, entrance, route-anchor and path assertions with confidence, optional positive accuracy radius and source snapshots. A representative point must be a Point. `location_provider_references` stores neutral provider/feature/version identities separately, so removing a provider reference cannot alter accepted canonical geometry.

## Reviewed provider promotion and Map lists

Migration `20260808_35_map_feature_lists` adds one seeded `Favourites` list plus user-created named lists. `map_feature_list_memberships` has one row per list/provider/feature tuple and stores a user-owned label for intelligible offline display. It does not store feature version, address, coordinates, source snapshot or availability. Those external facts resolve from the current provider when available and may disappear without deleting or repointing membership.

Provider-to-canonical promotion uses the existing canonical tables rather than a staging entity. The review is read-only. Confirmation of a new Location atomically creates the entity, applicable source-reported address/representative-point assertions and one versioned `location_provider_references` row. Confirmation against an existing reviewed duplicate inserts only that provider reference. Pack/browser payloads therefore cannot overwrite already accepted canonical assertions.

## Journey configuration and cache boundary

`mobility_profiles` and `routing_policies` are durable local configuration, not entities and not provider-owned records. Each has a stable lowercase key, display name, positive revision, canonical JSON definition and audit identity. Profiles retain one stable primary Walk/Cycle/Drive/Public transport mode. Policies retain one provider-independent hard-exclusion, soft-avoidance, preference, added-cost or added-buffer kind and an enabled state. Edits preserve identity and increment the revision so dependent fingerprints change. N3 deliberately installs no default profile values or policies; later measured values and adapter translations may specialize the validated JSON contract without moving ownership to a provider.

Journey results are not stored in the canonical database. `app/journey_cache.py` owns a bounded SQLite result cache at ignored runtime storage. Rows contain only a semantic fingerprint, normalized result JSON, calculation/freshness times and local cache timestamps. They report fresh, stale or miss; malformed or semantically incompatible entries are discarded. N6's reviewed Gold Coast walking capability supplies a 128-entry maximum and 24-hour static-source freshness window; every request, endpoint, profile/policy revision, adapter, coverage and source dependency remains in the fingerprint. Clearing or deleting the file cannot remove Locations, profiles, policies or Events.

## Relationships and taxonomies

`relationships` stores one source/target row with its type, taxonomy definition, status, optional dated interval and certainty, notes, lifecycle and inference provenance. Reverse navigation and labels are derived from `relationship_type_definitions`; inverse rows are never stored.

`taxonomies` and `taxonomy_entries` provide reusable paths of at most three levels. `relationship_type_definitions` adds endpoint types, direction, perspective roles, inverse labels and selectable state to Relationship Type entries. Archived or legacy definitions remain resolvable for old data but are excluded from new choices.

Both entities and Relationships use timestamped soft deletion. Ordinary queries exclude recycled rows; restoration clears the timestamp without changing identity. Permanent entity deletion is allowed only from the Recycle Bin and cascades owned typed/reference/journal/relationship data. Generic audit rows intentionally survive because they do not foreign-key the deleted canonical row.

## Calendars, Events and occurrences

`calendars` is the sole canonical Event grouping/configuration table. Each kind has one active default. Deleting a Calendar is restricted while any active or recycled Event refers to it. The protected Birthdays Calendar links People to synchronized canonical Events through `birthday_event_links`.

`events` enforces one of two mutually exclusive schedules:

- timed: bounded UTC start/end plus originating IANA timezone;
- all day: start date plus exclusive end date.

Cancellation, Event archive and entity Recycle Bin state use separate columns and meanings. Recurrence definitions remain attached to one Event; exceptions and splits preserve occurrence and successor-series traceability without materializing every occurrence as an Event row.

Not every occurrence is persisted. `app/temporal_occurrences.py` adapts canonical or cached source facts into deterministic logical occurrences. Source tables retain their dates; shared reminder and Inbox tables are the downstream persistence boundary.

## Reminders, Inbox, Jobs and automation

Reminder timings are validated canonical tokens stored as JSON. Policies apply to a context such as a local or external Calendar; overrides apply to a source record or occurrence. Source, occurrence, due instant, timing and reason form the logical delivery identity.

`inbox_items` is the current attention projection. A partial uniqueness constraint permits at most one active/snoozed item for a source occurrence and reason. `inbox_item_actions` is append-only delivery and transition history. Resolving or dismissing attention never deletes that history.

Scheduled Jobs and deterministic automation deliberately use separate tables:

- `scheduled_jobs` selects only application-registered handler names; `job_runs` records execution attempts and `scheduler_checkpoints` records recovery progress.
- `automation_rules` selects only registered trigger/action names; `(rule_id, trigger_key)` makes logical execution idempotent and `automation_runs` retains outcome/failure history.

No row contains Python or arbitrary executable user code.

## Audit, provenance and review state

`audit_events` plus `audit_event_records` are the append-only operational audit source. They are not canonical Events or real-world Timeline items. `provenance_metadata` stores lightweight field/record origin. `entity_edit_history` stores entity edit and merge snapshots without a foreign key so survivor history remains valid after merge or deletion.

Family inference stores batches and suggestions only. A suggestion becomes a normal Relationship only after confirmation. Evidence fingerprints suppress unchanged rejections and flag later evidence changes without silently deleting confirmed Relationships.

Data-quality findings are deterministic projections. Only the user's disposition and notes persist in `data_quality_finding_state`; the finding itself is recalculated.

## External files, packs and network caches

Uploaded Document bytes live under `instance/documents/`. Writes use confined generated names. A successful replacement removes the old unreferenced file only after the database points to the replacement; recycling retains it; permanent deletion removes it only when no other Document references it. Missing files are tolerated and unsafe paths are never deleted.

iCalendar upload bytes are staged under ignored runtime storage and create canonical records only after preview and explicit confirmation. External Calendar cache rows are operational copies keyed by subscription and source UID. Refresh validates a complete response before atomically replacing a source's cache; failure retains the last-known-good state. Cached items never gain canonical entity identity or Relationships. The separate journey result cache is bounded and disposable rather than a route-history or recovery source.

Spatial packs also live outside the canonical database under `instance/spatial-packs/`. Each immutable installed version contains a strict manifest, vector MBTiles, fixed read-only search SQLite and coverage GeoJSON; `active.json` is an atomic operational pointer, not a database foreign key. Pack search rows and static-transit features are replaceable provider context and cannot receive entity identity or Relationships. Audit records describe activation, rollback and removal, but do not make the removed bytes recoverable personal data. Whole-platform export excludes packs; source/version/coverage/attribution in the visible manager supplies reacquisition context. Contextual **Improve coverage** review reads those active files directly and persists no recommendation, selected coordinate, candidate region or provider fact.

## Portability and recovery

Portable format version 1 is a ZIP containing:

- `manifest.json` with format version, export time, counts and SHA-256 checksums;
- a consistent SQLite snapshot made with the backup API;
- exactly the uploaded files referenced by Document rows.

Import rejects unsafe paths, bad checksums, invalid SQLite/foreign keys, a mismatched migration set, invalid typed entities or Relationships, invalid canonical geometry/containment, invalid journey profile/policy configuration, invalid portable Map-list state, and document-membership mismatches before apply. Apply requires an empty target and explicit confirmation, stages replacement, creates a recovery bundle and appends an import audit event. Durable profiles/policies and Map-list membership travel inside the database snapshot; disposable journey cache files, current provider facts and replaceable spatial packs do not.

The same recovery primitive runs before confirmed merge and permanent deletion. Recovery artifacts remain private ignored runtime data and never become application dependencies.
