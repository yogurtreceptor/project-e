# Ontology

Project E models real-world information as canonical entities and Relationships, with separate configuration, derived temporal, and operational records. These categories have different identities and lifecycles; they must not be collapsed into one generic record model.

## Model Map

The platform uses four complementary record categories:

- **Canonical entities** are durable records for meaningful real-world objects or work: Person, Organisation, Location, Project, Document, Asset, Event and Task.
- **Configuration records** set local organisation and behaviour without becoming entities: Calendars and Task lists.
- **Derived temporal records** are deterministic, traceable time instances and views: derived occurrences and Calendar projections.
- **Operational and historical records** support attention, execution and traceability: reminder policies, Notifications and their actions, Audit events, Scheduled Jobs and Job Runs, Automation Rules and Automation Runs, and Review Proposals.

A Calendar view may display canonical records, derived occurrences and operational projections, but is never an independent Event store. A Task deadline or session, Person birthday, Document expiry, Project target date or Scheduled Job Run does not become an Event merely because it appears on a Calendar.

## Canonical Entities

An entity is the canonical record for one real-world object or meaningful work item. Each has a stable identifier, entity type, display name, descriptive fields where useful, and creation and update timestamps.

The current canonical entity types are:

- Person
- Organisation
- Location
- Project
- Document
- Asset
- Event
- Task

Each real-world object should have one canonical entity record. Create and edit flows warn about possible matches using normalized names and a small set of strong domain fields, but users may explicitly save when distinct real objects genuinely share those values.

### People

A Person represents a real person.

Current user-entered fields are:

- Required: given name.
- Standard: middle name, family name, sex, birthday, email and phone.
- Optional, added on demand and shown only when populated: Alias, Nickname, Height, Weight, Languages, Nationalities and Ethnicities.

Field semantics and presentation rules are:

- Height and Weight are measurements normalized to canonical units; their selected display units remain presentation choices.
- Languages, Nationalities and Ethnicities may contain multiple links to shared reference records rather than copied text.
- Ethnicity is self-identified and must never be inferred from other Person data.
- Short observations are separate timestamped journal entries linked to the Person. The legacy shared Notes field remains in storage but is not the Person detail-page observation stream.
- A Person's internal display name is generated from given name plus family name. Middle name, alias and nickname are stored but are not part of the normal display name.
- Preferred name is not currently modelled.
- Sex is optional and is used only where it can improve relationship display labels, such as father/mother/parent or brother/sister/sibling.
- Email and phone remain direct Person fields. Contact methods may later become first-class related records if richer communication history or multiple contact points justify them.

### Organisations

An Organisation represents a company, institution, group, team or other organisation.

Current fields include:

- organisation name
- taxonomy-backed organisation classification
- repeatable other names / aliases
- website
- phone
- email
- notes

Classification is one reusable path of up to three levels rather than unrelated broad and specific text values. Other names are normalized rows, one value per alias; they cover alternate, former, trading and abbreviated names and participate in search and duplicate review.

Website, phone and email remain direct Organisation fields. They may later become contact-method or communication-related records when the model needs them.

### Locations

A Location represents a place, address or meaningful area.

Current fields include:

- location name
- address lookup
- address
- address line 1
- address line 2
- suburb
- city
- state
- post code
- country
- latitude and longitude
- source
- notes

Maps are a derived view over Location data, not the foundation of the Location model.

### Projects

A Project represents ongoing work or an area of responsibility. It coordinates information and Relationships; it does not own related records. Its overview may project related upcoming Events and open Tasks, but those records remain independent canonical peers.

Projects can relate to People, Organisations, Locations, Documents, Assets, Events, Tasks and other Projects.

Current fields include:

- project name
- project type
- status
- started date
- target date
- ended / completed date
- notes

Project type is controlled with custom values allowed. Status is controlled and uses Active, Paused, Completed or Abandoned.

### Events

An Event represents something that occurs, occurred or is expected to occur. It is a broad, user-owned time record, not only an appointment or meeting, and may relate to every appropriate canonical peer through normal Relationships.

- Every Event has one stable canonical entity identity and belongs to exactly one Calendar.
- Its planned time is either a precise, bounded timed interval or an all-day date interval, never both. Timed values retain their selected IANA timezone; all-day intervals retain calendar-date boundaries.
- A recurring Event has one canonical source and deterministic, traceable occurrences. Occurrence-specific exceptions and prospective series splits do not create duplicate Event entities.
- Cancellation records that an Event will not occur, archive removes it from ordinary views, and Recycle Bin deletion identifies an erroneous record. These states are independent; restoring a deleted Event preserves its cancellation and archive state.
- Event links to People, Organisations, Locations, Projects, Documents, Assets, Tasks and other Events use the shared recoverable Relationship lifecycle. There are no special embedded Event foreign keys or nested ownership models.

### Tasks

A Task represents work to be performed. It is neither an Event nor a Reminder, and may relate independently to every appropriate canonical peer through normal Relationships.

- Every Task belongs to one Task list selected by the user. The list is a personal organisational category, not ownership or a second classification system.
- A Task is Open or Completed; completion is a lifecycle fact with a timestamp. Archive is independent of completion, and Recycle Bin deletion is a separate recoverable lifecycle state.
- A Task may have an optional all-day or timed deadline. A deadline is a due fact, not a Calendar interval.
- A Task may have repeatable planned sessions. A session is a planned all-day or bounded timed interval projected into the Calendar without becoming an Event or separate canonical entity.
- Completing a Task removes its future sessions while retaining past session history.

### Documents

A Document represents a first-class document record, optionally backed by a locally uploaded file.

The Document owns that file:

- Replacement removes the superseded unreferenced file.
- Deleting the final referencing Document removes it from local storage.

Documents should be linked to other entities through Relationships. A passport, receipt, manual or contract is a Document entity and should not be stored inside the Person, Asset, Organisation or Project it concerns.

Current fields include:

- document name
- document purpose
- document date
- identifier / reference number
- expiry date
- notes
- optional local file metadata

Document purpose is controlled with custom values allowed. It describes what the record is; uploaded MIME metadata describes file format. Issuer and creator are relationship concepts linked to canonical People or Organisations; the Document model has no duplicate issuer/creator text field.

### Assets

An Asset represents a physical or digital thing such as a vehicle, laptop, phone, appliance or smart device. A passport, receipt, certificate, manual or similar record is a Document, not an Asset.

Assets can relate to People, Organisations, Locations, Projects, Documents, Events and Tasks. They may also carry direct coordinates when that is the most accurate available geographic information.

Current fields include:

- asset name
- asset type
- status
- manufacturer
- model
- serial number / asset number
- acquisition date
- value
- latitude and longitude
- notes

Asset type and status are controlled with custom values allowed. Value is stored as whole-number text and displayed with a dollar sign on read pages.

## Configuration Records

Configuration records are local organisational or behavioural settings. They have stable identity and history, but are not canonical entities or a second source of truth for the records they configure.

### Calendars

A Calendar is the sole local Event grouping and configuration record. It supplies a name, colour, IANA timezone, default Event duration, ordering, archive state and default reminder policy; it is not an independent Event store or a second Event classification layer.

- Every Event belongs to one Calendar and derives its colour from that Calendar. Event-specific colour overrides are not part of the model.
- A fresh installation provides the default General Calendar and the protected Birthdays Calendar. Each Person birthday synchronises to one linked, canonical, yearly recurring all-day Event in the Birthdays Calendar; it remains an Event rather than a derived Event type.
- Archiving a Calendar retains its Event assignments and prevents new or changed assignment to it. It neither archives nor moves existing Events.
- Exactly one active default Calendar is maintained for each Calendar kind. Before archiving a default Calendar, the user selects another active default of that kind.
- A Calendar with active or recycled Event assignments cannot be deleted.

### Calendar Subscriptions

A Calendar Subscription is an explicitly configured, read-only public-HTTPS iCalendar source shown under **Other calendars**. It is an operational configuration record rather than a local Calendar or canonical Event owner.

- Its local settings provide name, colour, IANA timezone, ordering, enabled state and a default Event-notification policy. It has no default Event duration because users do not create or schedule its items.
- Its source-scoped UIDs identify items in a last-known-good operational cache. Refresh reconciles that cache without creating `Calendar`, `Entity` or `Event` rows.
- Cached items remain non-canonical and have no relationships, item-level reminder override, edit history or Recycle Bin lifecycle. A Calendar-level policy may still create a durable local Notification for an upcoming cached occurrence.
- Disabling or removing the subscription suppresses future delivery and resolves active reminder attention without deleting retained Inbox history.

### Task Lists

A Task list is a first-class local organisational record that groups Tasks by the user's intended category. It is not a Calendar, ownership boundary or separate classification layer.

- A fresh installation provides one active default Tasks list.
- Every Task references one active Task list when it is created or reassigned.
- Archiving a Task list retains assigned Tasks and prevents new assignment. Task-list deletion is not implemented.

## Derived Temporal Records and Calendar Projections

A **derived occurrence** is a deterministic temporal instance traceable to a canonical source and definition, such as a generated recurring Event occurrence, a birthday from `Person.birth_date`, or a Document expiry.

A **Calendar projection** is a displayed time-based view of a canonical record or derived occurrence. It is not a source of truth and does not convert every dated record into an Event.

Calendar projections can display canonical Events, generated Event occurrences, Task deadlines and sessions, birthdays, Document expiries, Project target dates and Scheduled Job Runs. Derived occurrences and projections remain traceable to their source records and use no duplicate canonical Event rows unless a separately designed workflow deliberately materialises a new Event with explicit provenance.

## Operational and Historical Records

Operational and historical records support deterministic attention, execution, review and traceability. They are distinct from canonical entities and from one another.

### Reminders and Notifications

A Reminder is a policy attached to an Event, cached URL Calendar occurrence, Task deadline, derived occurrence or source-record policy; it is behaviour, not an independent domain entity. Local Calendar, Calendar Subscription, Task-list, record and occurrence contexts resolve the applicable reminder timings.

A Notification is the durable, actionable local Inbox delivery produced for a due condition. Delivery, acknowledgement, dismissal, snooze, resolution and failure history belong to the Notification and append-only action history, not to the Reminder definition.

- A delivery has a stable logical identity based on its source, occurrence, due instant, timing and reason. Re-evaluation of unchanged inputs does not duplicate it.
- A material future change to an affected due condition, occurrence or applicable timing creates a new pending delivery only where needed; superseded active or snoozed attention is resolved. Historical delivery records are retained.
- A Notification does not itself mutate its source Event, Task or other canonical record. Snoozing, dismissing or acknowledging changes operational attention only.

### Audit Events

An Audit event is an append-only historical fact about a canonical-data mutation or finding resolution. It records traceability without becoming a Timeline event, Notification, Job Run or canonical entity.

### Scheduled Jobs and Job Runs

A Scheduled Job is database-backed local background work using a registered application handler, schedule and run history. It is not an Event, Reminder or arbitrary executable user-authored code.

A Job Run is one execution attempt and result for a Scheduled Job. Job definitions and Runs retain their own identities even when a Calendar projects scheduled or completed work. Jobs use explicit local catch-up and lease behaviour so recovery remains deterministic and deduplicated.

### Automation Rules, Automation Runs and Review Proposals

An Automation Rule is an explicit, deterministic trigger-condition-action configuration referencing only registered local triggers and actions. It is not executable user-authored code, a Scheduled Job, Event or Task.

An Automation Run is one idempotent execution for a stable logical trigger identity. It records inputs, outcome and failure state separately from a Job Run.

A Review Proposal is an actionable operational record describing a consequential proposed Event or Task mutation, together with its evidence and approval state. It is not the mutation itself: explicit user approval invokes the normal validated service, while rejection is durable. Automation may recalculate derived state and create or update operational records, but it cannot automatically create, edit, complete, archive or delete a canonical Event or Task.

## Controlled Values

Controlled category fields currently follow these rules:

- Most remain direct typed text.
- Organisation classification is the first entity field migrated to the reusable taxonomy framework.
- Document purpose, Asset type and Project type remain small controlled/custom value sets rather than taxonomies.

Current controlled fields are:

- Organisation classification: a selected taxonomy path, for example `Business › Finance › Bank`. Clear legacy values are mapped; ambiguous and custom legacy values are retained as archived entries until reclassified.
- Project `project_type`: Personal, Work, Education, Health, Finance, Home, Vehicle, Travel, Civic, Other, or custom.
- Project `status`: Active, Paused, Completed, Abandoned.
- Document `document_type`: Letter, Licence, Receipt, Certificate, Statement, Contract, Invoice, Manual, Other, or custom purpose.
- Asset `asset_type`: Vehicle, Appliance, Tool, Electronic device, Computer, Phone, Smart device, Furniture, Other, or custom.
- Asset `status`: Owned, Sold, Lost, Destroyed, In disrepair, Loaned out, Other, or custom.

## Relationships

A Relationship is a first-class record connecting two canonical entities. Its identity and canonical facts survive soft deletion and restoration; recycled Relationships are excluded from active graph views.

Relationships support:

- source entity
- target entity
- relationship category
- relationship type
- relationship subtype where useful
- direction semantics through type labels and inverse labels
- optional start and end dates
- date certainty for start and end dates
- status
- notes
- creation and update timestamps

Relationship duration is presented as follows:

- Relationships are treated as ongoing unless they are explicitly marked as former or have an end date.
- Displays show an end date only when one is recorded.
- An ongoing Relationship with a start date is shown as `Since [start date]`.

Navigation and editing work as follows:

- Relationships are editable and directly navigable from entity pages and the relationship browser.
- Creation and day-to-day editing should happen primarily from an entity page, because users usually think from one known entity outward.
- A single Relationship can connect any two canonical entities, regardless of entity type.

The database stores one Relationship row. Its taxonomy-backed definition supplies canonical endpoint direction and natural inverse labels, so bidirectional navigation is derived rather than duplicated. Entity pages group Relationships by connected entity type across all current domains.

Relationship creation is entity-first and perspective-based:

1. Users start from the known entity page.
2. They choose either the existing-entity workflow or the new-entity workflow.
3. They answer one question using explicit names: `What is [connected entity] in relation to [current entity]?`
   - For existing entities, the connected entity name is shown directly.
   - For new entities, the question updates live as the name is typed.
4. Saving returns to the original entity page, and the Relationship appears from both connected entities.

Each entity profile labels the connected entity's resolved role from that profile's perspective; storage direction remains canonical and unchanged.

## Relationship Types

Relationship types are selectable taxonomy entries, not free-floating labels.

Runtime responsibilities are divided as follows:

- `relationship_type_definitions` stores the authoritative runtime definitions.
- `app/relationship_catalog.py` supplies deterministic seeds and legacy compatibility.
- `app/relationships.py` remains the behaviour facade.

Each definition includes allowed endpoint entity types, a taxonomy path of up to three levels, forward and reverse display labels, whether direction matters, optional usage notes, and whether the type is selectable for new Relationships. The UI filters options after it knows the two endpoint types and translates the selected perspective role into canonical storage direction.

Current pair-aware groups include:

- Person to Person: Family, Work, Education, Health, Social and Other.
- Person to Organisation: employee/employer, manager, director, member, volunteer, student, patient/client, customer, owner and Other.
- Person to Location: lives at, works at, visited, born at, located at and Other.
- Person to Project: contributor, involved in, managed/owned project and Other.
- Organisation to Location: located at, headquartered at, branch at, operates at and Other.
- Organisation to Project: involved in, sponsor, owner and Other.
- Asset to Location: stored at, located at, last known at and Other.
- Document to Person or Organisation: belongs to, created by, issued to/by, references and Other.
- Document to Asset or Project: belongs to, receipt/manual/references where relevant and Other.
- Event to Person, Organisation, Location, Project, Document and Asset: involvement, venue, related-project and reference connections where relevant.
- Event to Event: related Event.
- Task to Person, Organisation, Location, Project, Document and Asset: assignee, involvement, location, related-project and reference connections where relevant.
- Task to Event: related Event.
- Task to Task: related Task.

Person-to-Person family definitions follow these rules:

- They use neutral canonical types such as Parent / child and Sibling rather than storing Brother, Mother or Father as new relationship types.
- Profile role labels may become sex-specific when the connected Person has Sex recorded as Female or Male.
- If Sex is Other or Unknown, neutral labels are used.
- For example, a parent's profile displays the connected person as Daughter, Son or Child, while the child's profile displays the connected person as Mother, Father or Parent.

Legacy relationship keys are handled as follows:

- Generic or gendered keys such as `located_at`, `mother_of`, `father_of`, `child_of`, `related_to` and `associated_with` are preserved so existing Relationships still load.
- They are not offered for new pair-specific Relationship creation.
- Safe legacy location Relationships continue to feed Geography and Map views.

Contact information follows these boundaries:

- Phone numbers, emails and websites remain simple direct fields.
- The recommended future approach is a lightweight Contact Method model linked to any entity, with method type, value, label, preferred status, validity dates and notes.
- That model should be introduced only when multiple contact points or richer communication history justify it.
- It should not become a Communications domain without separately authorised product work.

## Deterministic Family Inference

Manual parent/child Relationships are source facts.

The Inference Review Queue receives only safe bloodline candidates derived by the deterministic inference engine:

- grandparent/grandchild
- full sibling
- aunt/uncle with niece/nephew
- cousin

It does not infer step, adoptive, half, foster, guardian, in-law or partner Relationships.

Inference review follows these rules:

- Suggestions are not Relationships until confirmed.
- Confirmation creates a normal editable Relationship while preserving its rule, source batch, supporting Relationship IDs, evidence fingerprint and timestamps.
- Rejection suppresses the same evidence fingerprint.
- Later source changes invalidate pending suggestions but only flag changed evidence on confirmed Relationships.

Evidence requirements are:

- Full-sibling evidence requires the same complete known parent set with at least two parents.
- Direct-generation dates may use the younger person's DOB alone.
- Peer and collateral dates require both DOBs.

## Relationship Dates and Certainty

Relationship dates support exact calendar dates plus certainty metadata. Current certainty values are exact, approximate and unknown. An approximate date stores the closest known calendar date marked as approximate; it is not a date range or partial date.

## Geographic Ontology

A Location is the canonical geographic entity for a place, address or meaningful area.

It may have:

- a human-readable address
- structured address fields
- optional latitude/longitude
- a geocoding source

When place information is known, People and Organisations should be connected to Locations with `located_at` Relationships rather than duplicate address fields.

The Map is a view over these canonical entities:

- Location markers represent Location entities with valid coordinates.
- Organisation markers represent Organisations connected to a coordinate-bearing Location.
- Person markers represent People connected to a coordinate-bearing Location.
- Asset markers represent Assets with valid direct coordinates or Assets connected to a coordinate-bearing Location.

Missing coordinates do not invalidate a Location; they only prevent that record, and entities relying on it, from appearing as markers. Projects, Documents, Events and Tasks never appear as map markers.

Detailed Phase 2 delivery status remains in the [Phase 2 workspace](phase_2_workspace.md). Persistence, migration and service mechanics remain in the [database design](database_design.md) and [architecture](architecture.md) documents.
