# Database Design

Project E uses SQLite as the embedded local database and canonical source of truth for Phase 1 and subsequent phases. `app/db.py` remains the public facade, with schema/migration, entity, relationship and discovery operations separated into focused modules.

## Schema Versioning

`schema_migrations` records each applied migration identifier and timestamp. Ordered migrations are append-only in `app/db_schema.py`: do not rename or remove an identifier after use. Existing databases are adopted by running missing idempotent migrations and recording them only after success.

The current-schema repair pass still runs on every startup. During active development, clean current architecture takes priority over backwards compatibility: use a practical migration when possible, accept a development reset when necessary, and do not retain obsolete duplicate models.

## Core Tables

- `entities` stores shared identity and metadata for every canonical record.
- `people`, `organisations`, `locations`, `projects`, `documents` and `assets` store type-specific fields keyed by `entity_id`.
- `relationships` stores first-class links between any two entities.
- `journal_entries` stores individual chronological plain-text observations linked to an entity identity.
- `entity_aliases` stores repeatable alternate names for entities; Organisation Other names are the first consumer.

## Entity Storage

Every real-world object starts in `entities` with:

- `id`
- `type`
- `display_name`
- `notes`
- timestamps
- discovery metadata such as favourite and last viewed state
- `deleted_at`, empty for active records and timestamped for records in the Recycle Bin

For Person records, `entities.display_name` is maintained automatically from `people.given_name` plus `people.family_name`. `people.alias` and `people.nickname` are additive optional columns and use the standard definition-driven typed-column migration. Existing records retain their stored display names until edited or merged, preserving legacy local data; new writes never require users to enter both forms of the name. Legacy `preferred_name` columns may remain physically present after an additive upgrade but are no longer active model fields.

Typed tables hold fields that only apply to one entity type. Schema creation is definition-driven, missing typed columns are added during startup and the central entity type constraint is rebuilt when new entity domains are introduced so local databases can evolve additively.

Migrations `20260704_10_reference_data` and `20260704_11_measurement_units` add normalized platform stores. `reference_data_types` and `reference_data_items` define reusable local catalogue values, including optional parent links. `entity_reference_values` links any entity field to one or more catalogue rows in a stable order. `measurement_units` adds symbols, categories, canonical flags, conversion factors and offsets to unit catalogue items. `entity_measurements` stores one canonical decimal text value and selected display-unit foreign key per entity field. These tables cascade entity-owned values on permanent deletion while catalogue rows remain shared.

The `entities.summary` column remains in existing and new databases as a legacy compatibility/search field, but it is no longer part of active creation or edit forms. Notes are the flexible free-text area.

Migration `20260704_09_entity_soft_delete` adds `entities.deleted_at`. Repository reads exclude timestamped rows by default, including relationship hydration, so any relationship with a deleted endpoint is preserved but hidden. Recycle Bin reads opt in explicitly. Restore clears only the selected entity's timestamp. Permanent deletion is restricted to Recycle Bin records and then uses the existing foreign-key cascades for typed data, relationships, journal entries and inference dependencies; unrelated entities are never deleted. Generic audit rows have no entity foreign key and therefore survive permanent deletion.

Person observations use `journal_entries` rather than accumulating in the shared Notes field. Each entry stores `entity_type`, `entity_id`, body, created/updated timestamps and an optional archive timestamp. The generic entity linkage leaves room for later entity types, while application routes currently permit People only. Active lists omit archived entries; permanently deleting an entity cascades to its entries, while soft deletion preserves them for restore. Journal entry deletion is permanent and remains a secondary UI action.

Field renames may be handled additively when that remains clean. Obsolete fields are removed by explicit migration rather than retained as duplicate truth.

Controlled field value aliases are applied during startup where needed. For example, legacy Project status `active` is normalised to `Active`, and legacy Asset status `active` is normalised to `Owned`.

## Additional Domain Storage

Projects store lightweight organising metadata:

- `project_type`
- `status`
- `started_at`
- `target_date`
- `ended_at`

Documents store document metadata plus local file metadata:

- `document_type`
- `document_date`
- `identifier`
- `expiry_date`
- `file_name`
- `file_path`
- `mime_type`
- `file_size`

Uploaded files are stored in `instance/documents/` through `app/document_storage.py`, which owns safe naming, metadata and path confinement. Documents should be related to other entities through the relationship table rather than embedded inside those entities.

A Document owns its uploaded file. A successful replacement deletes the superseded file only after the database points to the replacement. Soft deletion retains the current file for restoration; permanent deletion removes it only when no other Document still references it. Missing files are tolerated, unsafe paths are never deleted, and newly written files are removed if the corresponding database write fails. File metadata submitted through hidden form fields is not trusted.

Assets store useful item metadata such as asset type, status, manufacturer, model, serial number / asset number, acquisition date, whole-number value and optional direct coordinates.

Project target/end and Document expiry are validated ISO dates and timeline sources. An end date cannot precede its Project start, and an expiry date cannot precede its Document date. `documents.identifier` participates in duplicate review. Migration `20260705_14_document_domain_cleanup` removes the obsolete issuer column and maps format-like purpose values to `Other`; issuer and creator facts use relationships.

Migration `20260705_13_entity_aliases` adds normalized aliases with case-insensitive per-entity uniqueness and an indexed value. Alias hydration uses the same external-field boundary as references and measurements. Search, duplicate review and merge consume the rows without copying them into Organisation text columns.

## Controlled Field Storage

Controlled dropdown values are stored as text in the relevant typed table column. Preset-backed custom values use the same column rather than a separate lookup table in Phase 1.

This text-backed rule applies to small domain controls such as statuses and types. Reusable cross-domain facts use the reference-data catalogue instead. Person Languages and Nationalities therefore store foreign-key links rather than copied labels. Person Height and Weight store canonical measurements (metres and kilograms respectively) while retaining the user's selected display unit.

The tracked language and country catalogue is generated from the IANA Language Subtag Registry snapshot recorded in `app/reference_catalogue.py`. Startup seeding is additive, so existing databases receive newly tracked catalogue rows without replacing entity links or requiring network access. The generator selects active two-letter language and region subtags and can be rerun explicitly when the project chooses to adopt a newer snapshot.

The tracked ethnicity catalogue is generated from ABS ASCCEG 2025 Table 1.3 by `tools/update_ethnicity_catalogue.py`. Its stable four-digit ASCCEG codes become reference item keys. Person Ethnicities are ordered, multi-value links in `entity_reference_values`; no ethnicity is inferred or stored as duplicated text.

Structured dates, coordinates and whole-number asset values also remain text-backed in Phase 1. `FieldDefinition.value_kind` drives normalization and validation before form saves: dates must be real ISO calendar dates, coordinates must be numeric and within geographic bounds, and asset values must be non-negative whole-number text. Blank optional values remain valid.

## Phase 2 persistence boundaries

Phase 2 is complete and preserves SQLite as the canonical store through migration-safe evolution. The current model uses `calendars` as the sole Event grouping and configuration store. A fresh installation receives the default General Event Calendar plus the protected Birthdays Calendar. Calendars have stable identifiers, case-insensitive unique names, colour, timezone, default duration, ordering, timestamps, archive state, a `kind`, and a database-enforced default per kind. Event colour derives from the Calendar; there is no Event-specific colour override.

Events are canonical first-class entity records connected through the existing relationship model. Every Event selects exactly one local Calendar. Calendar views primarily project canonical records or traceable derived occurrences; enabled read-only Calendar subscriptions are the explicit non-canonical external projection described below.

Migrations `20260720_21_task_lists_and_tasks` and `20260723_22_task_temporal_values` are historical ledger entries for an unsuccessful experimental Task model. Migration `20260801_31_retire_task_subsystem` removes its tables, entity type, relationship taxonomy, reminder contexts and proposal storage. It first refuses the upgrade if any Task entity, Task row, proposal or Task relationship exists, so retirement cannot silently erase user data. A fresh database still records the append-only historical migrations before applying the retirement migration, but its current schema contains no Task tables or Task entity constraint. Future work-management storage requires a new design and forward migration rather than compatibility with the retired model.

Migration `20260723_23_reminder_and_inbox_foundation` adds `reminder_policies`, record/occurrence `reminder_overrides`, and durable `inbox_items`. Policy and override timings are stored as validated JSON timing tokens, not user-entered comma-separated text; forms submit each timing as an integer/unit pair before the service produces its canonical token. The service resolves source defaults with local Calendar, URL Calendar or global derived-source policy where present, custom additions and individual suppression. Calendar policies contain at most ten timings, and canonical Event override validation limits the resulting effective set to ten. An absent Calendar policy inherits the platform Event defaults; a canonical Event with no custom additions or suppressions inherits its linked local Calendar policy, while a cached URL Calendar occurrence has no record-level override and uses its URL Calendar policy. Saving an empty Calendar notification creator restores platform inheritance. Inbox delivery keys are unique hashes of source, logical occurrence, due instant, timing and reason, so repeated manual evaluation cannot duplicate a delivery while a changed due instant has a new identity. Inbox state preserves active, snoozed, acknowledged, dismissed and resolved history; snooze changes only the next-attention time and does not create a replacement record.

Migration `20260725_24_inbox_delivery_timing` records the timing token on each new Inbox reminder delivery. This lets reminder-policy reconciliation resolve only active or snoozed deliveries whose timing was removed, while retaining unchanged deliveries. Existing deliveries retain an empty timing marker and are not retrospectively reclassified, except that disabling their reminder source still resolves pending attention.

Migration `20260725_28_birthday_calendar` adds the `birthday` Calendar kind and `birthday_event_links`. It creates one canonical all-day yearly Event per Person birthday, uses the original birthday as its recurrence anchor, and migrates the old global birthday timing policy to the Birthdays Calendar's Event policy.

Migration `20260730_29_calendar_interchange` adds three focused interchange tables. `event_icalendar_identities` associates one canonical imported Event or series anchor with a unique source UID, sequence, normalized fingerprint and import time; it provides repeat safety without adding interchange fields to every Event. `calendar_subscriptions` stores externally owned source configuration, safe refresh validators/state and independent Other-calendars ordering. `external_calendar_events` is the last-known-good parsed cache keyed by subscription and source UID. Subscription rows and cache items are operational local state: they do not create `calendars`, `entities`, `events`, relationships, record-level reminder definitions, edit history or Recycle Bin records.

Migration `20260730_30_external_calendar_reminders` expands the checked reminder-policy context vocabulary with `calendar_subscription`. A URL Calendar can therefore reuse validated Event timing tokens without becoming a canonical Calendar. Cache refresh updates existing rows by source-scoped UID so their internal projection/reminder identifier remains stable; a materially changed or removed occurrence resolves pending attention, while title or description refreshes do not redeliver it. Disabling or removing a URL Calendar resolves pending deliveries, and removal also deletes its contextual policy while retaining historical Inbox rows and action history.

iCalendar upload preview is read-only and staging remains under ignored runtime storage. Explicit confirmation creates the optional local Calendar, canonical Events, recurrence definitions, identity rows, provenance and audit records in one transaction. Public-HTTPS subscription refresh validates a complete response before atomically reconciling one source's stable UID-keyed cache; a fetch or parse failure retains the previous cache. Whole-platform portability includes these tables and contextual reminder policies through its database snapshot, while selected Calendar ZIP export is a separate interoperability format and does not replace portability.

Migration `20260725_25_inbox_action_history` adds append-only `inbox_item_actions`. Each delivery and subsequent user or system state transition records its action, prior and resulting state, next-attention time, note and timestamp; `inbox_items` remains the current-state projection.

`app/temporal.py` owns the first shared temporal contract. Timed local wall values require an IANA timezone and normalize to UTC; nonexistent daylight-saving wall times are rejected and ambiguous times require the caller to choose the earlier or later occurrence. Timed intervals require a bounded end after their start. All-day Events retain ISO calendar dates and normalize the user-facing inclusive end date to an exclusive stored boundary. `app/timezones.py` reads the locally installed tzdb metadata to present selectable IANA identifiers with country names and current offsets; it is presentation data only and does not introduce a timezone table, fixed-offset storage or a network dependency.

Migration `20260719_17_canonical_events` added `event` to canonical entity identity and created the initial `events` typed table. Migration `20260719_18_remove_event_categories` is a forward-only correction for development databases that already applied the initial category-bearing schema: it rebuilds `events` without that foreign key, preserves Event and Calendar identifiers plus every temporal/lifecycle value, adds Calendar ordering, renames the untouched seeded default Calendar to General and drops the obsolete table. Migration `20260719_19_calendar_management_history` adds append-only `calendar_edit_history` for Calendar configuration and lifecycle changes. The earlier migration identifiers and historical functions remain append-only so an existing ledger migrates without manual intervention. Fresh databases run the ordered sequence and converge automatically on the corrected schema before startup completes; current-schema repair creates only the corrected Calendar-only model and Calendar history store.

Each Event references one Calendar with restricted deletion. `app/calendar_service.py` accepts only valid `#RRGGBB` colours, IANA timezones, positive duration values and integer ordering, records changes in Calendar history/audit/provenance, and requires exactly one active default per Calendar kind through its management operations and portability validation. Archiving a Calendar preserves all Event assignments; an archived Calendar cannot accept new or changed assignments, while an Event already assigned to it remains recoverable and editable. The service requires a non-default Calendar to have no Event rows, including recycled Events, before permanent deletion and never silently reassigns Events. Timed rows store a bounded UTC start/end pair plus the originating IANA timezone; all-day rows store date-only start and exclusive-end boundaries. A database constraint makes these temporal modes mutually exclusive. Date precision is `exact` or `approximate`; status is currently `planned` or `cancelled`; `archived_at` remains distinct from both cancellation and the entity Recycle Bin's `deleted_at`.

`app/event_service.py` is the Event write boundary. It applies the default Calendar only at creation, permits an existing Event to retain an archived Calendar while preventing new assignment to archived Calendars, and writes audit, provenance and entity-edit history through existing platform stores. Cancellation, reinstatement and rescheduling use dedicated service operations while status remains persisted. Event identity is stable through edits, rescheduling and archive/unarchive operations. Event archive state is independent from `entities.deleted_at`; Recycle Bin restoration does not alter archive or cancellation state. Event creation is deliberately not exposed through generic entity forms: the Calendar UI calls the Event service directly, and schedule edits retain the dedicated rescheduling operation. Its Month, Week and Day views are calculated from canonical Event rows at request time, using the active default Calendar timezone for timed display and preserving all-day date boundaries. Week and Day render timed intervals as hourly-grid duration blocks and clip overnight spans into each affected display day; Calendar filters do not mutate stored state. Migration `20260719_20_event_recurrence` adds `event_recurrences`, versioned cancellation/override `event_recurrence_exceptions`, and traceable `event_recurrence_splits`. The recurrence implementation derives occurrences at read time, applies current-version exceptions, and records occurrence overrides, cancellations, truncations and linked successor-series changes in Event history, audit and provenance. Global Search includes Events through a query-only canonical projection, and the read-only `/events/{id}` projection is available from Search and normal relationship links; neither introduces query/projection storage or a generic Event mutation path. Event links use the existing `relationships` table and its standard soft-delete, restoration, audit and provenance lifecycle; no Event-specific person, location, project or document foreign keys are introduced.

The shared temporal model must extend these compatible semantics for deadlines, recurrence and uncertainty; it does not require a premature universal base table. Initial Events store planned time only; actual start/end tracking is a deferred extension for concrete time-tracking workflows. Local Calendar settings provide overridable default Event duration and reminder policy; URL Calendar settings provide reminder policy but no default duration because the external source owns every schedule. Initial date precision is exact or approximate: an approximate date stores the user's closest known date plus its precision marker, not a date range or partial date. Recurrence must support calendar-grade interval, weekday, ordinal-weekday and bounded-date-range patterns. Generated occurrences remain traceable rather than duplicate Event rows; occurrence-specific, prospective-series and entire-series changes must be separately traceable. Reminder policy sources include canonical Events, cached URL Calendar occurrences and eligible record-derived dates such as Document expiries; approximate dates do not generate reminders. Each Person birthday deliberately synchronises one canonical yearly Event into the protected Birthdays Calendar and therefore uses the ordinary Event reminder path, while a Document expiry remains a derived all-day occurrence owned by its Document. All-day reminder sources use 09:00 in the configured platform timezone as their due anchor; it defaults to `Australia/Brisbane` (UTC+10) until user configuration is introduced, without changing existing reminder meaning. Calendar-month lead times retain calendar semantics. Reminder definitions are attached policies and overrides, while acknowledgement, snooze, delivery failure and delivery history are separate notification-delivery records. Broad canonical Event precedence is occurrence override, Event override, local Calendar policy, then global policy; a cached external occurrence uses its URL Calendar policy without item-level overrides. Custom timings add to inherited timings, individual inherited timings may be suppressed, and coincident timings have one delivery. A recurring this-occurrence reminder override is keyed to the stable generated occurrence identity; a this-and-following reminder edit uses the normal series split and applies the amended policy to the successor series, while an all-occurrences edit changes the policy of the current canonical series. All three canonical recurrence scopes recalculate only affected future pending deliveries and never rewrite historical occurrence or delivery records. Phase 2C establishes the local notification boundary without a background scan; Phase 2D performs delivery and startup recovery. A delivery identity contains source kind and identifier, stable logical occurrence identity, due anchor instant, timing and reason; database uniqueness constraints plus atomic claims protect future external side effects from concurrent duplicate execution. Repeated evaluation of identical inputs reuses that identity. A changed due anchor, recurrence occurrence, applicable timing or future policy creates a new identity only for its affected delivery; superseded active or snoozed deliveries are resolved, while unaffected deliveries remain valid. Disabling resolves active or snoozed pending delivery and suppresses future delivery; re-enabling evaluates only the current policy. Snoozing changes only the existing delivery's next-attention time. A dismissed reminder stays dismissed as history unless a material source reschedule or reminder-policy change creates a fresh pending delivery; immaterial changes never redeliver it. Recovery creates a missed delivery only when its logical pending delivery remains eligible and no matching active or historical delivery already exists. A source lifecycle change that removes the due condition suppresses future deliveries and resolves active reminder attention, while historical deliveries remain retained. Persistent System Health, issue suppression and escalation are deferred until separately authorised condition producers and actions exist.

ADR-028 requires future record-derived reminder sources to supply the shared occurrence identity, source link, due boundary and source-specific resolution policy through one registered temporal-occurrence boundary. It does not require one universal persistence table: canonical source tables retain their dates, while occurrence adapters and projections remain deterministic unless a separately authorised workflow deliberately materialises a canonical Event. The shared reminder-policy and delivery tables remain the downstream persistence boundary. The current source loop in `app/reminder_service.py` is not the final extension mechanism and must be replaced rather than expanded with another hardcoded domain branch during the next authorised reminder/Inbox refactor.

Scheduled jobs use database-backed definitions and run history, but handler names refer only to registered application capabilities. The first scheduler runs in the application process while it is running and exposes its scheduling, locking and handler contract behind a boundary suitable for a later local worker. Clean shutdown/startup timestamps and a durable scheduler checkpoint support recovery after both normal and unclean application stops. Recovered work runs serially in scheduled order, with a registered per-job catch-up policy that defaults to one overdue one-off run, one coalesced reminder/maintenance scan, one current high-frequency run after stale intervals are skipped, or every missed occurrence only for explicit historic processing. Jobs may override their default. Each job has one transactionally claimed active lease. A failed or expired lease is recorded for manual rerun; the initial scheduler has no automatic retry. Persistent System Health and escalation remain deferred rather than becoming automatic job-failure output. Database rows must not contain arbitrary executable code. Deterministic automations use the same application services and write audit/provenance through normal paths. Canonical Events use the normal Recycle Bin lifecycle; derived occurrences, calendar projections, notification and delivery history, job runs and audit records are historical or derived records rather than Recycle Bin entries. Export/import remains whole-platform: it includes Phase 2 canonical and operational records and validates their references and schema compatibility before apply.

Migration `20260725_26_operational_scheduler` adds `scheduled_jobs`, `job_runs` and `scheduler_checkpoints`. `scheduled_jobs.handler_name` is matched only against the application-owned registry in `app/scheduler_service.py`; it is never evaluated as code. The initial `reminder-delivery` definition is registered at runtime with a 60-second interval and a coalesced catch-up policy. Atomic immediate transactions claim a short lease before a Run row is created, and the Run's `(job, scheduled_for, trigger)` identity prevents duplicate scheduled or recovery execution. Startup first reactivates Inbox items snoozed until next open, then runs due jobs serially and writes a checkpoint. Manual runs and failure reruns retain their own trigger identities and do not change the normal next-run time. A failed Run is historical and awaits an explicit rerun or its next regular interval; it is not a Persistent Issue or automatic escalation.

Migration `20260725_27_deterministic_automation` historically introduced rules, runs and Task-only review proposals. Migration `20260801_31_retire_task_subsystem` removes the proposal table and the two dormant Task actions. The current automation schema contains `automation_rules` and `automation_runs` only. A rule stores a stable registered trigger/action name, optional declarative JSON conditions and enabled state; it never stores Python or user-authored executable code. `(rule_id, trigger_key)` is unique, making a logical trigger idempotent independently of process state. Runs retain input, outcome, source identity where applicable, status and failure reason.

Current controlled fields are:

- `organisations.taxonomy_entry_id`, referencing the reusable Organisation Classification taxonomy. The legacy `organisation_type` text remains migration history.
- `projects.project_type`, custom allowed.
- `projects.status`, presets only.
- `documents.document_type`, custom allowed, stores document purpose rather than file format.
- `assets.asset_type`, custom allowed.
- `assets.status`, custom allowed.

## Location Storage

Locations are the canonical place/address records. The active `locations` table fields include:

- `formatted_address`
- `address_line_1`
- `address_line_2`
- `suburb`
- `city`
- `state`
- `post_code`
- `country`
- `latitude`
- `longitude`
- `source`

Coordinates are optional text fields at this stage so users can save locations without coordinates and manually enter coordinates without a migration-heavy geospatial dependency. When supplied, latitude and longitude are validated and required as a pair. Validation for map display happens in the application layer.

Legacy Location columns are copied forward on startup:

- `locality` -> `city`
- `region` -> `state`
- `postal_code` -> `post_code`
- `geocoding_source` -> `source`

Legacy Asset `purchase_date` is copied to `acquisition_date`.

## Address Ownership

People and Organisations do not own address columns. They reference Location entities through `located_at` relationships where appropriate. This keeps one canonical record per real-world place and avoids duplicate address data.

Older local databases may still contain previously-created Organisation address columns. They are no longer part of the active entity definition and are ignored by the application.

## Relationship Storage

Relationships store source and target entity IDs, type, status, optional dates, date certainty and notes. The database stores one row per relationship; inverse navigation is derived from relationship metadata.

Reusable classifications live in `taxonomies` and self-referencing `taxonomy_entries`. Entries have stable keys, labels, parents, ordering and archive timestamps; validation caps paths at Type, Subtype and Specific subtype. Organisation and relationship rows reference one terminal entry. Archived branches remain resolvable for existing records but are excluded from new choices.

Relationship-only semantics live in `relationship_type_definitions`, keyed to a Relationship Type taxonomy entry. Endpoint types, canonical direction, symmetry, perspective roles, inverse phrases and optional sex-aware labels deliberately remain outside the generic hierarchy.

Relationship validation checks that the selected type is selectable and valid for the two endpoint entity types. The UI uses the same relationship definitions to show only relevant options after the connected entity type is known. Forced-pair workflows, such as Organisation to Person, only send that pair's valid options to the page.

Relationship saves normalise source/target direction into the definition's canonical order. The form submits the connected entity's role relative to the current entity, such as Daughter or Employee, and the data layer translates that role into source, target and type. The original entity context is preserved in the redirect, and bidirectional labels are derived from the normalised row.

Person Sex is stored as a controlled optional Person field with Male, Female, Other and Unknown values. It is not required for relationship creation. Relationship display may use Male or Female for family labels; Other and Unknown fall back to neutral labels.

`relationships.taxonomy_entry_id` is canonical while `type` remains an incremental compatibility snapshot for inference, graphs and upgrades. Legacy generic or gendered keys map to archived entries and remain loadable but non-selectable. Safe legacy `located_at` rows still contribute to Geography and Map views.

`tools/convert_legacy_family_relationships.py` provides an explicit, one-time cleanup path for gendered family keys. It is read-only by default, maps direction into the canonical neutral family definitions, creates an SQLite backup before `--apply`, and leaves duplicate or unknown relationships unresolved rather than guessing.

The relationship UI has independent existing-entity and new-entity workflows. Inline relationship creation reuses the standard definition-driven fields for supported entity types inside the new-entity workflow. The new entity is inserted in the same save path as the relationship; if the relationship is not valid, the pending inline entity insert is rolled back.

## Map Storage

The map has no separate persistence table. It is built as a view over existing `locations`, `entities` and `relationships` data. Future map layers should add canonical entity/relationship data first, then expose that data through the map layer registry.

Assets may appear on the map when they have valid direct coordinates or a `located_at` relationship to a coordinate-bearing Location. Projects and Documents never appear as map markers.

## Edit History and Merge Integrity

`entity_edit_history` is an append-only audit table keyed by the surviving entity ID. It records normal edits and merge events as JSON detail snapshots. It intentionally does not use a foreign key: history copied from a retired duplicate must remain attached to the canonical survivor.

Duplicate merges are same-type, previewed, and committed in one transaction. The survivor retains its ID and creation metadata. Non-conflicting values fill blanks, notes are combined, conflicts and the duplicate snapshot are retained in history, all relationship endpoints are repointed, and equivalent or newly self-referencing relationships are removed before the duplicate entity is deleted.


## Relationship inference storage

Automatic deterministic recomputation maintains suggestion state only. It does not create canonical relationships; explicit confirmation in the Inference Review Queue is required.

Confirmed suggestions become normal editable relationship rows. `relationships.created_from_inference` preserves their audit origin, `inference_suggestion_id` links to the reviewed suggestion, and `provenance_json` snapshots the source type, batch ID, rule key, supporting relationship IDs, evidence fingerprint, and inference/confirmation timestamps. `inference_evidence_status` is `current` while the original support still matches and `changed` when it no longer does; this flag never locks or deletes the relationship.

`inference_batches` stores review stacks and their trigger/status. `inference_suggestions` stores the canonical people/type pair, inferred date, deterministic rule, support IDs, fingerprint, and lifecycle status (`pending`, `confirmed`, `rejected`, or `invalidated`). Rejected fingerprints remain stored to prevent unchanged suggestions from reappearing. Batches are archived automatically after all suggestions are reviewed. Historic decisions can be undone: rejected suggestions return to pending, while confirmed suggestions also remove the relationship created by that confirmation before the batch reopens.

Suggested dates are stored only when rule-specific DOB evidence is sufficient. Direct-generation rules may use the younger endpoint's DOB alone; peer and collateral rules require DOBs for both endpoints and use the chronologically lower value. The date participates in the evidence fingerprint.

## Audit, provenance, and finding state

Migration `20260628_06_platform_infrastructure` adds append-only generic audit events with affected-record links, lightweight per-field/relationship provenance, and user disposition state for deterministic data-quality findings. These tables do not provide snapshots, rollback, versioning, or evidence storage.

Migration `20260628_07_backfill_platform_audit` restores operational-history visibility for pre-audit databases by seeding create/edit events from canonical timestamps and relationship-create events from relationship timestamps. It is one-time and does not alter canonical records.

## Relationship soft deletion and audit projection

`relationships.deleted_at` is the canonical relationship deletion marker and is indexed. Empty means active; a timestamp means hidden and recoverable. Active repositories, graph validation, query filters, integrity checks, data-quality checks and inference inputs exclude deleted relationships. Restoration clears the marker without recreating the row, preserving identifiers, dates, provenance and audit references.

Migration `20260705_15_relationship_soft_delete` adds the column additively to existing databases; fresh schema creation includes it directly. The append-only `audit_events` and `audit_event_records` tables remain the sole operational audit source. Event action is stored in `event_type`, while typed record references supply subject scope; the System Audit applies filters as a read projection and preserves legacy `relationship_change` rows.


## Portable bundles and recovery

Portable format version 1 is a ZIP containing `manifest.json`, `data/project-e.sqlite3`, and the uploaded files referenced by canonical Document rows. The manifest identifies the format/version, export timestamp, record counts and a SHA-256 digest for every member. SQLite's backup API creates the database member so export does not depend on copying a live database file.

Import accepts only the current migration set, a clean SQLite integrity and foreign-key check, recognized entity types with typed rows, valid relationship endpoint/type combinations, safe archive paths, matching counts and an exact match between Document file references and bundled files. Apply requires an empty target, explicit preview confirmation and a pre-import recovery bundle. Replacement is staged; failures restore the previous document directory and do not intentionally expose partially imported canonical data. Import appends an `import` audit event while preserving the bundle's prior audit and provenance rows.

Recovery bundles use the same format. Confirmed merge and permanent deletion create them before mutation. Merge repoints both active and recycled relationship rows while preserving `deleted_at`; only duplicate or self-referencing results are removed. Permanent deletion reports active and recycled counts separately before the existing foreign-key cascade.
