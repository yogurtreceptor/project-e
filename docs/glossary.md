# Glossary

This glossary is the shared vocabulary for Project E. Use it when project terminology is unclear or when future implementation work needs consistent wording.

## Index

[A](#a) · B · [C](#c) · [D](#d) · [E](#e) · F · G · H · [I](#i) · [J](#j) · K · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · Q · [R](#r) · [S](#s) · [T](#t) · U · V · W · X · Y · Z

## A

### Alias

A repeatable alternate name for a canonical entity. Organisation aliases include former, trading and abbreviated names; they are normalized values used by search and duplicate review, not comma-separated text.

### Approximate Date

A closest known calendar date marked as approximate. It does not represent a date range or a partial year/month value.

### Architecture Decision Record (ADR)

A short record of an important architecture decision, why it was made and its consequences.

See also: Repository Source of Truth.

### Archived

An inactive record or workflow item that remains part of its normal platform domain and may be shown through an archive-specific control. Archiving is not deletion and archived items do not enter the Recycle Bin.

See also: Deleted, Recycle Bin.

### Artificial Intelligence

Future-phase capability where models may consume, interpret or propose changes to platform data through shared, governed capabilities. AI is not part of Phase 1 and is not the platform's foundation.

See also: Phase 1, Decision Support, Automation, Odysseus.

### Asset

An entity representing a physical or digital item, such as a vehicle, appliance, device, tool or important possession.

See also: Entity, Document, Location.

### Audit event

An operational record of a canonical-data mutation or finding resolution.

### Automation

Autonomous, goal-directed execution that can schedule work, perform consequential actions without review or create external side effects. This form of automation is not part of Phase 1. Ordinary deterministic application behaviour and reviewed assistance are not automation in this sense.

See also: Deterministic Assistance, Phase 1, Decision Support, Artificial Intelligence.

### Automation Rule

A database-backed, explicit trigger-condition-action configuration that references only a registered local trigger and action. It is not executable user-authored code, a Scheduled Job, Event or Task.

### Automation Run

One idempotent execution of an Automation Rule for a stable logical trigger identity. It records inputs, outcome and failure state separately from a Job Run.

## C

### Calendar

A first-class local Event grouping and configuration record, comparable to a Google Calendar calendar. Every Event belongs to exactly one Calendar. A Calendar supplies a name, colour, IANA timezone, default Event duration, ordering, archive state and default reminder policy; its edit form keeps the compact colour control and repeatable reminder rows beside those defaults. A Calendar has at most ten notification timings. It is not an independent Event store. The protected Birthdays Calendar is a built-in category populated by linked canonical birthday Events from People. Archiving retains Event assignments and prevents new selection; an assigned Calendar cannot be deleted.

### Calendar Subscription

An explicitly configured, read-only public-HTTPS iCalendar source shown under Other calendars. Its external items remain non-canonical and uneditable. Project E retains a last-known-good local cache so Calendar rendering stays usable without WAN access, but the source is still externally owned.

See also: Calendar, Calendar Projection, iCalendar.

### Calendar Projection

A time-based display derived from a canonical record or derived occurrence. It is not a source of truth or a conversion of every dated record into an Event.

### Canonical Record

The single preferred record for one real-world object. Duplicate records should be avoided or resolved so each important person, organisation, place, document, asset or project has one main record.

See also: Entity, Repository Source of Truth.

### Canonical Unit

The designated storage unit for a measurement category. Values entered in another unit are converted to the canonical unit for persistence and converted back through a selected display unit for presentation.

See also: Measurement, Structured Data.

### Controlled Field

A structured field with known allowed or suggested values, such as status or type. Some controlled fields may allow a custom value when the preset list is too narrow.

See also: Structured Data, Custom Value.

### Custom Value

A user-entered value accepted by a controlled field when the built-in options are not enough.

See also: Controlled Field.

## D

### Dashboard

The main navigation and overview surface for the local information platform. It should help users move into entities, relationships and other views without becoming a command or chat interface.

See also: Entity Page, Map Layer.

### Data-quality finding

A deterministic, explainable observation produced by a registered validation rule.

### Decision Support

Future-phase capability that helps interpret information or support decisions. It is separate from Phase 1 storage, navigation and relationship modelling.

See also: Phase 1, Artificial Intelligence, Automation.

### Deleted

The recoverable state of an entity hidden from normal platform views, search and relationship navigation. A deleted entity remains stored until restored or permanently deleted from the Recycle Bin.

See also: Archived, Recycle Bin.

### Derived Occurrence

A deterministic, traceable temporal instance produced from a canonical record and definition, such as a yearly birthday from a Person birth date.

### Design System

The reusable visual and component rules that apply the Experience Philosophy consistently, including semantic tokens, typography, spacing, states, density, responsiveness and accessibility. It does not define domain-specific workflows or replace the Experience Philosophy.

See also: Experience Philosophy, Entity Page.

### Detail Page

A page that shows one record in detail. In Project E, the primary detail page for an entity is the entity page.

See also: Entity Page.

### Deterministic Assistance

Local, rule-based and explainable behaviour that preserves user control. It may calculate suggestions, warnings, derived views or internal maintenance state, but a consequential mutation requires explicit user confirmation. Deterministic assistance is permitted in Phase 1 and is distinct from autonomous automation.

See also: Automation, Inference Review Queue, Phase 1.

### Document

An entity representing a document record, optionally backed by a local uploaded file. Documents should be linked to other entities through relationships rather than embedded inside them.

See also: Entity, Relationship, Asset.

### Domain

A meaningful area of records in the platform, usually represented by an entity type such as People, Organisations, Locations, Projects, Documents or Assets.

See also: Entity, Phase 1.

## E

### Entity

A canonical record for one real-world object or meaningful thing in the platform.

See also: Canonical Record, Domain, Relationship.

### Entity Page

The main page for viewing and working from a single entity. It should expose structured fields, relationships, notes and related views for that entity.

See also: Detail Page, Relationship, Notes.

### Evidence Fingerprint

A stable digest of an inference rule, inferred date and supporting relationship rows. It identifies material evidence changes and prevents an unchanged rejected suggestion from reappearing.

See also: Inference Review Queue, Relationship.

### Event

A first-class entity representing something that occurs, occurred or is expected to occur at an instant or over an interval. An Event may be physical, remote, virtual, inferred or derived and may relate to any suitable entity through Relationships.

### Experience Philosophy

The experience-level authority describing why Project E should feel and behave as it does. It guides navigation, information layers, page architecture and visual character without defining low-level tokens or component specifications.

See also: Design System, Entity Page, Super Key.

### Export

Either a whole-platform portability bundle or a Calendar interchange download. The portability export is a versioned, checksummed local ZIP containing a consistent canonical database snapshot and its referenced uploaded documents. Calendar export is a selected ZIP of ordinary iCalendar members for interoperability and is not a backup.

See also: Import, iCalendar, Local-first.

## I

### IANA Timezone

A named timezone from the installed IANA timezone database, such as `Australia/Brisbane` or `America/New_York`. Calendar, Event and timed Task controls select and store this identifier; the local selector can be searched by current UTC offset, country, place or identifier. It never stores a display label or a fixed offset in place of the identifier.

### iCalendar

The RFC-style Calendar interchange format used by `.ics` and `.ical` files. Project E previews and validates a deliberately lossless supported subset before importing canonical local Events or exporting Calendar members. It is distinct from whole-platform portability and from renewable Calendar subscriptions.

See also: Calendar Subscription, Export, Import.

### Import

Either a confirmed whole-platform restoration or a previewed Calendar interchange operation. Portability import restores a validated bundle into an empty Project E target. Calendar import explicitly adds supported iCalendar Events to a selected local Calendar, optionally creating that Calendar, and never creates a subscription.

See also: Export, Canonical Record, iCalendar.

### Inference-created Relationship

A normal editable relationship created when a user confirms a deterministic suggestion. It behaves like a manually entered relationship while retaining inference provenance and evidence-health metadata for auditability.

See also: Inference Review Queue, Relationship.

### Inference Review Queue

A review workspace containing deterministic relationship suggestions that are not relationship records until confirmed. Completed batches archive automatically; one archive control reveals fully expanded searchable history with per-decision undo.

See also: Evidence Fingerprint, Inference-created Relationship, Relationship.

## J

### Job Run

One execution attempt of a Scheduled Job and its result.

### Journal Entry

A timestamped plain-text observation stored as an individual record against a Person. Journal entries appear chronologically and may be edited, archived or permanently deleted. Archiving hides an entry from the active journal without deleting it.

See also: Person, Notes.

## L

### Local-first

The principle that the user's local database and files are the primary source of truth, and the platform remains useful without WAN or cloud services.

See also: Repository Source of Truth, Phase 1.

### Location

An entity representing a place, address or meaningful area. Locations are the canonical home for address and coordinate information.

See also: Entity, Map Layer, Relationship.

## M

### Map Layer

A map view grouping derived from canonical entities and relationships. A map layer should not create a separate source of truth.

See also: Dashboard, Location, Relationship.

### Measurement

A numeric value associated with a unit and category, such as length, mass or temperature. Measurements are stored in their category's canonical unit independently of how they are displayed.

See also: Canonical Unit, Structured Data.

## N

### Notification

An actionable local-inbox attention item, such as a due reminder or required approval. It persists until acted upon and is distinct from a Persistent Issue, Audit Event and Job Run. Startup may create one deduplicated recovered Notification for a missed due condition.

### Notes

Free-text supporting information attached to an entity or relationship. Notes are useful for context, but important categories and statuses should be structured fields where practical.

See also: Structured Data, Controlled Field.

## O

### Odysseus

The leading candidate for Project E's future AI/agent layer and a possible integration or fork target. It is not part of the current architecture; future work should adapt Odysseus to a mature Project E platform rather than restructure Project E around it.

See also: Artificial Intelligence, Phase 1.

### Organisation

An entity representing a company, institution, group, agency, club, team or other organised body.

See also: Entity, Person, Location.

## P

### Person

An entity representing a real person.

See also: Entity, Organisation, Relationship.

### Persistent Issue

A durable system-health or configuration condition whose one current record changes state over time. It is deduplicated and does not create recurring inbox items merely because it remains unresolved.

### Phase 1

The completed foundational phase of Project E: a local-first Personal Information Platform for entities, relationships, navigation, forms and storage. It permitted deterministic assistance that preserves user control, but excluded AI, chat, dispatcher architecture, decision support, autonomous automation and scheduling.

See also: Deterministic Assistance, Local-first, Artificial Intelligence.

### Phase 2

The in-progress operational time and deterministic-automation phase. It is not complete until its agreed capabilities work coherently and pass an end-to-end completion review. AI is excluded from its initial implementation.

See also: Event, Task, Calendar Projection, Reminder, Scheduled Job.

### Platform Timezone

The initial single-user time interpretation and display zone, `Australia/Brisbane`. Calendars default to this IANA zone, while individual timed Events may select another IANA timezone. Precise instants are stored in UTC and displayed through the selected timezone.

### Project

An entity representing ongoing work, an area of responsibility or an organising context. A Project is not a task-management record in Phase 1.

See also: Entity, Relationship.

### Provenance

A lightweight origin classification for a field or relationship.

## R

### Recycle Bin

The platform-wide view of soft-deleted entities and relationships. It supports selective restore; entities may also be permanently deleted after explicit confirmation, active/recycled dependency warnings and recovery backup creation.

See also: Deleted, Archived.

### Reference Data

Shared controlled records, such as countries, languages, currencies or measurement units, that entity fields link to instead of duplicating labels as text.

See also: Controlled Field, Structured Data.

### Relationship

A first-class record connecting two entities. Relationships should be stored, displayed, edited and navigated directly.

See also: Entity, Relationship Category, Relationship Type.

### Relationship Category

A broad grouping for relationship types, such as Family, Location, Document, Role or Other. Categories help organise relationship choices and display.

### Relationship Type

A specific kind of relationship between two entities, including its direction and display labels where needed.

See also: Relationship, Relationship Category.

### Relationship type definition

Relationship-specific behavior attached to a selectable Relationship Type taxonomy entry: valid endpoint types, canonical direction or symmetry, perspective roles and natural inverse display labels.

See also: Relationship, Relationship Type.

### Reminder

A notification or attention policy attached to a record or derived occurrence. Calendar and record controls use repeatable positive-integer/unit rows, rather than comma-separated text or a policy-state picker. An Event without specific rows inherits its linked Calendar timings; an Event can resolve to at most ten effective reminders. Delivery history is a notification record, not the reminder's canonical definition.

### Repository Source of Truth

The current repository docs and code that future contributors should rely on when deciding how Project E works. Previous chat sessions are not source of truth unless reflected in the repository.

See also: Architecture Decision Record (ADR), Local-first.

### Review Proposal

An actionable operational record that describes a proposed consequential canonical Event or Task mutation, with evidence and approval state. It is not the mutation itself; explicit approval invokes the normal validated service.

## S

### Scheduled Job

Database-backed executable background work using a registered application handler, schedule and run history. A Scheduled Job is not a Calendar Event or Reminder.

### Specialised View

A focused page rendering of a canonical entity or connected information for a particular task, such as Relationships, Family Tree, Timeline, Documents, Map or Audit. It is a view over existing records, not a duplicate source of truth.

See also: Entity Page, Canonical Record.

### Structured Data

Information captured in named fields or relationships rather than only in free text. Structured data should be used for facts that need filtering, validation, navigation or reuse.

See also: Notes, Controlled Field.

### Super Key

A persistent deterministic quick-navigation control for short codes, concise destination names and one-step navigation. It is the **Go** intention and remains distinct from browsing the platform, global information Search, natural-language assistance and consequential commands.

See also: Experience Philosophy, Entity Page.

## T

### Task

A first-class entity representing work to be performed. A Task is neither an Event nor a Reminder and can relate independently to Projects, Events and other entities.

### Task List

A first-class local organisational record that groups Tasks by the user's intended category. It is not a Calendar, ownership boundary or separate classification layer. Archiving retains its assigned Tasks and prevents new assignment.

### Task Session

A repeatable planned all-day or bounded timed interval belonging to one canonical Task. It is a Calendar projection source, not an Event or separate canonical entity.

### Taxonomy

A reusable local hierarchy containing Type, optional Subtype and optional Specific subtype. A record stores one selected terminal entry representing the whole path. Archived entries remain readable on existing records but are unavailable for new selection.

### Timeline event

A derived real-world occurrence, separate from operational audit history.
