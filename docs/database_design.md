# Database Design

Operation Eddy uses SQLite as the embedded local database for Stage 1. `app/db.py` remains the public facade, with schema/migration, entity, relationship and discovery operations separated into focused modules.

## Schema Versioning

`schema_migrations` records each applied migration identifier and timestamp. Ordered migrations are append-only in `app/db_schema.py`: do not rename or remove an identifier after use. Existing databases are adopted by running missing idempotent migrations and recording them only after success.

The current-schema repair pass still runs on every startup. This preserves additive field, controlled-value and entity-type compatibility even when definitions evolve between explicit migrations.

## Core Tables

- `entities` stores shared identity and metadata for every canonical record.
- `people`, `organisations`, `locations`, `projects`, `documents` and `assets` store type-specific fields keyed by `entity_id`.
- `relationships` stores first-class links between any two entities.

## Entity Storage

Every real-world object starts in `entities` with:

- `id`
- `type`
- `display_name`
- `notes`
- timestamps
- discovery metadata such as favourite and last viewed state

For Person records, `entities.display_name` is maintained automatically from `people.given_name` plus `people.family_name`. Existing records retain their stored display names until edited or merged, preserving legacy local data; new writes never require users to enter both forms of the name. Legacy `preferred_name` columns may remain physically present after an additive upgrade but are no longer active model fields.

Typed tables hold fields that only apply to one entity type. Schema creation is definition-driven, missing typed columns are added during startup and the central entity type constraint is rebuilt when new entity domains are introduced so local databases can evolve additively.

The `entities.summary` column remains in existing and new databases as a legacy compatibility/search field, but it is no longer part of active creation or edit forms. Notes are the flexible free-text area.

Field renames are handled additively. New columns are created and existing values are copied from configured legacy columns when the new column is empty. Legacy columns are left in place so local databases are not destructively rewritten.

Controlled field value aliases are applied during startup where needed. For example, legacy Project status `active` is normalised to `Active`, and legacy Asset status `active` is normalised to `Owned`.

## Additional Domain Storage

Projects store lightweight organising metadata:

- `project_type`
- `status`
- `started_at`

Documents store document metadata plus local file metadata:

- `document_type`
- `document_date`
- `issuer`
- `file_name`
- `file_path`
- `mime_type`
- `file_size`

Uploaded files are stored in `instance/documents/` through `app/document_storage.py`, which owns safe naming, metadata and path confinement. Documents should be related to other entities through the relationship table rather than embedded inside those entities.

A Document owns its uploaded file. A successful replacement deletes the superseded file only after the database points to the replacement; deleting a Document deletes its file only when no other Document still references it. Missing files are tolerated, unsafe paths are never deleted, and newly written files are removed if the corresponding database write fails. File metadata submitted through hidden form fields is not trusted.

Assets store useful item metadata such as asset type, status, serial number / asset number, acquisition date, whole-number value and optional direct coordinates.

## Controlled Field Storage

Controlled dropdown values are stored as text in the relevant typed table column. Preset-backed custom values use the same column rather than a separate lookup table in Stage 1.

Structured dates, coordinates and whole-number asset values also remain text-backed in Stage 1. `FieldDefinition.value_kind` drives normalization and validation before form saves: dates must be real ISO calendar dates, coordinates must be numeric and within geographic bounds, and asset values must be non-negative whole-number text. Blank optional values remain valid.

Current controlled fields are:

- `organisations.organisation_type`, custom allowed.
- `projects.project_type`, custom allowed.
- `projects.status`, presets only.
- `documents.document_type`, custom allowed.
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

Coordinates are optional text fields at this stage so users can save incomplete locations and manually enter coordinates without a migration-heavy geospatial dependency. Validation for map display happens in the application layer.

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

Relationship category, subtype, option labels, ordered source/target entity types, direction semantics, usage notes and bidirectional display labels live in the grouped `app/relationship_catalog.py` definitions rather than separate lookup tables. This is the Stage 1 balance: the row stays lightweight and local databases avoid taxonomy migrations, while validation and forms can still offer context-aware relationship choices.

Relationship validation checks that the selected type is selectable and valid for the two endpoint entity types. The UI uses the same relationship definitions to show only relevant options after the connected entity type is known. Forced-pair workflows, such as Organisation to Person, only send that pair's valid options to the page.

Relationship saves normalise source/target direction into the definition's canonical order. The form submits the connected entity's role relative to the current entity, such as Daughter or Employee, and the data layer translates that role into source, target and type. The original entity context is preserved in the redirect, and bidirectional labels are derived from the normalised row.

Person Sex is stored as a controlled optional Person field with Male, Female, Other and Unknown values. It is not required for relationship creation. Relationship display may use Male or Female for family labels; Other and Unknown fall back to neutral labels.

Legacy generic or gendered relationship keys remain loadable but non-selectable. Existing rows are not rewritten in Stage 1. Safe legacy `located_at` rows still contribute to Geography and Map views. New records should use the pair-specific taxonomy.

The relationship UI has independent existing-entity and new-entity workflows. Inline relationship creation reuses the standard definition-driven fields for supported entity types inside the new-entity workflow. The new entity is inserted in the same save path as the relationship; if the relationship is not valid, the pending inline entity insert is rolled back.

## Map Storage

The map has no separate persistence table. It is built as a view over existing `locations`, `entities` and `relationships` data. Future map layers should add canonical entity/relationship data first, then expose that data through the map layer registry.

Assets may appear on the map when they have valid direct coordinates or a `located_at` relationship to a coordinate-bearing Location. Projects and Documents never appear as map markers.

## Edit History and Merge Integrity

`entity_edit_history` is an append-only audit table keyed by the surviving entity ID. It records normal edits and merge events as JSON detail snapshots. It intentionally does not use a foreign key: history copied from a retired duplicate must remain attached to the canonical survivor.

Duplicate merges are same-type, previewed, and committed in one transaction. The survivor retains its ID and creation metadata. Non-conflicting values fill blanks, notes are combined, conflicts and the duplicate snapshot are retained in history, all relationship endpoints are repointed, and equivalent or newly self-referencing relationships are removed before the duplicate entity is deleted.


## Relationship inference storage

Confirmed suggestions become normal editable relationship rows. `relationships.created_from_inference` preserves their audit origin, `inference_suggestion_id` links to the reviewed suggestion, and `provenance_json` snapshots the source type, batch ID, rule key, supporting relationship IDs, evidence fingerprint, and inference/confirmation timestamps. `inference_evidence_status` is `current` while the original support still matches and `changed` when it no longer does; this flag never locks or deletes the relationship.

`inference_batches` stores review stacks and their trigger/status. `inference_suggestions` stores the canonical people/type pair, inferred date, deterministic rule, support IDs, fingerprint, and lifecycle status (`pending`, `confirmed`, `rejected`, or `invalidated`). Rejected fingerprints remain stored to prevent unchanged suggestions from reappearing. Batches are archived automatically after all suggestions are reviewed. Historic decisions can be undone: rejected suggestions return to pending, while confirmed suggestions also remove the relationship created by that confirmation before the batch reopens.

Suggested dates are stored only when rule-specific DOB evidence is sufficient. Direct-generation rules may use the younger endpoint's DOB alone; peer and collateral rules require DOBs for both endpoints and use the chronologically lower value. The date participates in the evidence fingerprint.
