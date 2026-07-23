# Glossary

This glossary is the shared vocabulary for Project E. Use it when project terminology is unclear or when future implementation work needs consistent wording.

## Experience Philosophy

The experience-level authority describing why Project E should feel and behave as it does. It guides navigation, information layers, page architecture and visual character without defining low-level tokens or component specifications.

See also: Design System, Entity Page, Super Key.

## Design System

The reusable visual and component rules that apply the Experience Philosophy consistently, including semantic tokens, typography, spacing, states, density, responsiveness and accessibility. It does not define domain-specific workflows or replace the Experience Philosophy.

See also: Experience Philosophy, Entity Page.

## Super Key

A persistent deterministic quick-navigation control for short codes, concise destination names and one-step navigation. It is the **Go** intention and remains distinct from browsing the platform, global information Search, natural-language assistance and consequential commands.

See also: Experience Philosophy, Entity Page.

## Specialised View

A focused page rendering of a canonical entity or connected information for a particular task, such as Relationships, Family Tree, Timeline, Documents, Map or Audit. It is a view over existing records, not a duplicate source of truth.

See also: Entity Page, Canonical Record.

## Architecture Decision Record (ADR)

A short record of an important architecture decision, why it was made and its consequences.

See also: Repository Source of Truth.

## Artificial Intelligence

Future-stage capability where models may consume, interpret or propose changes to platform data through shared, governed capabilities. AI is not part of Stage 1 and is not the platform's foundation.

See also: Stage 1, Decision Support, Automation, Odysseus.

## Asset

An entity representing a physical or digital item, such as a vehicle, appliance, device, tool or important possession.

See also: Entity, Document, Location.

## Alias

A repeatable alternate name for a canonical entity. Organisation aliases include former, trading and abbreviated names; they are normalized values used by search and duplicate review, not comma-separated text.

## Automation

Autonomous, goal-directed execution that can schedule work, perform consequential actions without review or create external side effects. This form of automation is not part of Stage 1. Ordinary deterministic application behaviour and reviewed assistance are not automation in this sense.

See also: Deterministic Assistance, Stage 1, Decision Support, Artificial Intelligence.

## Canonical Record

The single preferred record for one real-world object. Duplicate records should be avoided or resolved so each important person, organisation, place, document, asset or project has one main record.

See also: Entity, Repository Source of Truth.

## Canonical Unit

The designated storage unit for a measurement category. Values entered in another unit are converted to the canonical unit for persistence and converted back through a selected display unit for presentation.

See also: Measurement, Structured Data.

## Controlled Field

A structured field with known allowed or suggested values, such as status or type. Some controlled fields may allow a custom value when the preset list is too narrow.

See also: Structured Data, Custom Value.

## Custom Value

A user-entered value accepted by a controlled field when the built-in options are not enough.

See also: Controlled Field.

## Dashboard

The main navigation and overview surface for the local information platform. It should help users move into entities, relationships and other views without becoming a command or chat interface.

See also: Entity Page, Map Layer.

## Decision Support

Future-stage capability that helps interpret information or support decisions. It is separate from Stage 1 storage, navigation and relationship modelling.

See also: Stage 1, Artificial Intelligence, Automation.

## Deterministic Assistance

Local, rule-based and explainable behaviour that preserves user control. It may calculate suggestions, warnings, derived views or internal maintenance state, but a consequential mutation requires explicit user confirmation. Deterministic assistance is permitted in Stage 1 and is distinct from autonomous automation.

See also: Automation, Inference Review Queue, Stage 1.

## Detail Page

A page that shows one record in detail. In Project E, the primary detail page for an entity is the entity page.

See also: Entity Page.

## Document

An entity representing a document record, optionally backed by a local uploaded file. Documents should be linked to other entities through relationships rather than embedded inside them.

See also: Entity, Relationship, Asset.

## Domain

A meaningful area of records in the platform, usually represented by an entity type such as People, Organisations, Locations, Projects, Documents or Assets.

See also: Entity, Stage 1.

## Entity

A canonical record for one real-world object or meaningful thing in the platform.

See also: Canonical Record, Domain, Relationship.

## Entity Page

The main page for viewing and working from a single entity. It should expose structured fields, relationships, notes and related views for that entity.

See also: Detail Page, Relationship, Notes.

## Measurement

A numeric value associated with a unit and category, such as length, mass or temperature. Measurements are stored in their category's canonical unit independently of how they are displayed.

See also: Canonical Unit, Structured Data.

## Reference Data

Shared controlled records, such as countries, languages, currencies or measurement units, that entity fields link to instead of duplicating labels as text.

See also: Controlled Field, Structured Data.

## Export

A versioned, checksummed local ZIP containing a consistent canonical database snapshot and its referenced uploaded documents. It supports migration, review and recovery without an external service.

See also: Import, Local-first.

## Import

A confirmed way to restore a validated portable bundle into an empty Project E target. Import checks integrity and document membership, previews its effects, creates a recovery backup, preserves canonical identity/provenance and records an audit event.

See also: Export, Canonical Record.

## Local-first

The principle that the user's local database and files are the primary source of truth, and the platform remains useful without WAN or cloud services.

See also: Repository Source of Truth, Stage 1.

## Location

An entity representing a place, address or meaningful area. Locations are the canonical home for address and coordinate information.

See also: Entity, Map Layer, Relationship.

## Map Layer

A map view grouping derived from canonical entities and relationships. A map layer should not create a separate source of truth.

See also: Dashboard, Location, Relationship.

## Notes

Free-text supporting information attached to an entity or relationship. Notes are useful for context, but important categories and statuses should be structured fields where practical.

See also: Structured Data, Controlled Field.

## Journal Entry

A timestamped plain-text observation stored as an individual record against a Person. Journal entries appear chronologically and may be edited, archived or permanently deleted. Archiving hides an entry from the active journal without deleting it.

See also: Person, Notes.

## Archived

An inactive record or workflow item that remains part of its normal platform domain and may be shown through an archive-specific control. Archiving is not deletion and archived items do not enter the Recycle Bin.

See also: Deleted, Recycle Bin.

## Deleted

The recoverable state of an entity hidden from normal platform views, search and relationship navigation. A deleted entity remains stored until restored or permanently deleted from the Recycle Bin.

See also: Archived, Recycle Bin.

## Recycle Bin

The platform-wide view of soft-deleted entities and relationships. It supports selective restore; entities may also be permanently deleted after explicit confirmation, active/recycled dependency warnings and recovery backup creation.

See also: Deleted, Archived.

## Organisation

An entity representing a company, institution, group, agency, club, team or other organised body.

See also: Entity, Person, Location.

## Person

An entity representing a real person.

See also: Entity, Organisation, Relationship.

## Project

An entity representing ongoing work, an area of responsibility or an organising context. A Project is not a task-management record in Stage 1.

See also: Entity, Relationship.

## Relationship

A first-class record connecting two entities. Relationships should be stored, displayed, edited and navigated directly.

See also: Entity, Relationship Category, Relationship Type.

## Relationship Category

A broad grouping for relationship types, such as Family, Location, Document, Role or Other. Categories help organise relationship choices and display.

## Taxonomy

A reusable local hierarchy containing Type, optional Subtype and optional Specific subtype. A record stores one selected terminal entry representing the whole path. Archived entries remain readable on existing records but are unavailable for new selection.

## Relationship type definition

Relationship-specific behavior attached to a selectable Relationship Type taxonomy entry: valid endpoint types, canonical direction or symmetry, perspective roles and natural inverse display labels.

See also: Relationship, Relationship Type.

## Relationship Type

A specific kind of relationship between two entities, including its direction and display labels where needed.

See also: Relationship, Relationship Category.

## Repository Source of Truth

The current repository docs and code that future contributors should rely on when deciding how Project E works. Previous chat sessions are not source of truth unless reflected in the repository.

See also: Architecture Decision Record (ADR), Local-first.

## Stage 1

The completed foundational phase of Project E: a local-first Personal Information Platform for entities, relationships, navigation, forms and storage. It permitted deterministic assistance that preserves user control, but excluded AI, chat, dispatcher architecture, decision support, autonomous automation and scheduling.

See also: Deterministic Assistance, Local-first, Artificial Intelligence.

## Phase 2

The in-progress operational time and deterministic-automation phase. It is not complete until its agreed capabilities work coherently and pass an end-to-end completion review. AI is excluded from its initial implementation.

See also: Event, Task, Calendar Projection, Reminder, Scheduled Job.

## Event

A first-class entity representing something that occurs, occurred or is expected to occur at an instant or over an interval. An Event may be physical, remote, virtual, inferred or derived and may relate to any suitable entity through Relationships.

## Task

A first-class entity representing work to be performed. A Task is neither an Event nor a Reminder and can relate independently to Projects, Events and other entities.

## Task List

A first-class local organisational record that groups Tasks by the user's intended category. It is not a Calendar, ownership boundary or separate classification layer. Archiving retains its assigned Tasks and prevents new assignment.

## Task Session

A repeatable planned all-day or bounded timed interval belonging to one canonical Task. It is a Calendar projection source, not an Event or separate canonical entity.

## Calendar Projection

A time-based display derived from a canonical record or derived occurrence. It is not a source of truth or a conversion of every dated record into an Event.

## Calendar

A first-class local Event grouping and configuration record, comparable to a Google Calendar calendar. Every Event belongs to exactly one Calendar. A Calendar supplies a name, colour, IANA timezone, default Event duration, ordering, archive state and eventually a default reminder policy; it is not an independent Event store. Archiving retains Event assignments and prevents new selection; an assigned Calendar cannot be deleted.

## Platform Timezone

The initial single-user time interpretation and display zone, `Australia/Brisbane`. Calendars default to this IANA zone, while individual timed Events may select another IANA timezone. Precise instants are stored in UTC and displayed through the selected timezone.

## Derived Occurrence

A deterministic, traceable temporal instance produced from a canonical record and definition, such as a yearly birthday from a Person birth date.

## Approximate Date

A closest known calendar date marked as approximate. It does not represent a date range or a partial year/month value.

## Reminder

A notification or attention policy attached to a record or derived occurrence. Its source context and any record-level override are defined by the approved Phase 2 reminder rules; delivery history is a notification record, not the reminder's canonical definition.

## Notification

An actionable local-inbox attention item, such as a due reminder or required approval. It persists until acted upon and is distinct from a Persistent Issue, Audit Event and Job Run. Startup may create one deduplicated recovered Notification for a missed due condition.

## Persistent Issue

A durable system-health or configuration condition whose one current record changes state over time. It is deduplicated and does not create recurring inbox items merely because it remains unresolved.

## Scheduled Job

Database-backed executable background work using a registered application handler, schedule and run history. A Scheduled Job is not a Calendar Event or Reminder.

## Job Run

One execution attempt of a Scheduled Job and its result.

## Odysseus

The leading candidate for Project E's future AI/agent layer and a possible integration or fork target. It is not part of the current architecture; future work should adapt Odysseus to a mature Project E platform rather than restructure Project E around it.

See also: Artificial Intelligence, Stage 1.

## Structured Data

Information captured in named fields or relationships rather than only in free text. Structured data should be used for facts that need filtering, validation, navigation or reuse.

See also: Notes, Controlled Field.


## Evidence Fingerprint

A stable digest of an inference rule, inferred date and supporting relationship rows. It identifies material evidence changes and prevents an unchanged rejected suggestion from reappearing.

See also: Inference Review Queue, Relationship.

## Inference-created Relationship

A normal editable relationship created when a user confirms a deterministic suggestion. It behaves like a manually entered relationship while retaining inference provenance and evidence-health metadata for auditability.

See also: Inference Review Queue, Relationship.

## Inference Review Queue

A review workspace containing deterministic relationship suggestions that are not relationship records until confirmed. Completed batches archive automatically; one archive control reveals fully expanded searchable history with per-decision undo.

See also: Evidence Fingerprint, Inference-created Relationship, Relationship.

- **Audit event:** An operational record of a canonical-data mutation or finding resolution.
- **Provenance:** A lightweight origin classification for a field or relationship.
- **Timeline event:** A derived real-world occurrence, separate from operational audit history.
- **Data-quality finding:** A deterministic, explainable observation produced by a registered validation rule.
