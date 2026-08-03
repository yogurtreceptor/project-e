# Ontology

Project E models real-world information as canonical entities and first-class Relationships. Configuration, derived projections and operational history are separate record categories because they have different ownership and lifecycles.

This document defines meaning. Exact fields live in `app/entities.py`, persistence in [Database Design](database_design.md), runtime ownership in [Architecture](architecture.md), and user-facing terminology in the [Glossary](glossary.md).

## Record categories

| Category | Meaning | Examples | Lifecycle |
| --- | --- | --- | --- |
| Canonical entity | One durable record for a meaningful real-world object or occurrence. | Person, Organisation, Location, Project, Document, Asset, Event | User-owned; editable; recoverable deletion. |
| Relationship | One asserted connection between two canonical entities. | Person works for Organisation; Event at Location | User-owned; editable; recoverable deletion. |
| Configuration | Local organisation or behaviour without becoming a real-world entity. | Calendar, Calendar Subscription, reminder policy | Managed through its owning service. |
| Derived projection | Deterministic, reproducible interpretation of source facts. | Timeline item, map marker, recurring occurrence, Calendar projection, data-quality finding | Recalculated; not independently edited. |
| Operational/history | Attention, execution or traceability state. | Inbox item, Job Run, Automation Run, audit event | State-specific; history generally append-only. |

A record can appear in a Calendar or Timeline without becoming an Event. Materialisation as an Event is a deliberate product choice that grants canonical identity and Event lifecycle; display alone never does so.

## Canonical entities

Every canonical entity has a stable ID, type, display identity, timestamps and optional notes. One real-world object should have one canonical entity even when it appears through many views.

| Entity | Represents | Important boundary |
| --- | --- | --- |
| **Person** | A real person. | Display name derives from given and family names. Languages, nationalities and self-identified ethnicities reference shared catalogues; height/weight are normalized measurements. Ethnicity is never inferred. Journal entries are separate observations. |
| **Organisation** | A company, institution, group, team or similar body. | Classification is taxonomy-backed and aliases are repeatable normalized names. Addresses belong to related Locations. |
| **Location** | A place, address or meaningful area. | It may exist without coordinates. It owns its address and optional point coordinates; maps are views over it. |
| **Project** | Ongoing work or an area of responsibility. | It coordinates related peers but does not own Events, Documents, People or other related records. |
| **Document** | A first-class record, optionally backed by a private local file. | Purpose is distinct from file format. Issuer/creator meaning is relational, not duplicate text. The Document owns its uploaded-file lifecycle. |
| **Asset** | A physical or digital thing. | Records such as receipts, manuals and certificates are Documents, not Assets. Direct coordinates are permitted when they best describe the thing's location. |
| **Event** | Something that occurs, occurred or is expected to occur. | It belongs to one local Calendar, has a bounded timed or all-day schedule, and connects to peers through ordinary Relationships. It is not a reminder. |

Duplicate warnings help find an existing canonical record but do not forbid genuinely distinct objects with similar facts.

### Event identity and time

An Event has one canonical source row. Recurring instances are deterministic occurrences of that source; an exception changes one occurrence and a split creates a traceable successor series. Neither turns every occurrence into an unrelated Event.

Cancellation, archive and Recycle Bin deletion are distinct:

- cancellation records that the Event will not occur;
- archive removes it from ordinary Calendar views while retaining it;
- Recycle Bin deletion marks the record as erroneous and recoverable.

Restoration preserves the other lifecycle states. A Person birthday is a canonical Event only because the protected Birthdays workflow deliberately creates and synchronises one linked yearly Event.

## Configuration and derived time

### Calendars

A **Calendar** is the sole local Event grouping and configuration record. It supplies colour, timezone, default duration, ordering, archive state and reminder defaults. Every Event belongs to one Calendar; the Calendar is not a second Event store or classification hierarchy.

The protected Birthdays Calendar is local and canonical. A **Calendar Subscription**, by contrast, is a configured public-HTTPS, read-only source under **Other calendars**. Its settings and last-known-good cache are operational local state. Cached items are not Entities or Events and receive no Relationships, edit history or Recycle Bin lifecycle.

### Occurrences and projections

A **temporal occurrence** is a stable, traceable instance adapted from a source fact. Examples include a recurring Event instance, cached external Calendar item or Document expiry. It identifies its source, logical occurrence, time boundary, navigation destination and resolution behaviour.

A **Calendar projection** displays eligible canonical Events or occurrences. A **Timeline item** is a derived real-world chronological fact. Neither is a source of truth.

New record-derived dates should join the shared occurrence provider boundary. They should not gain domain-specific reminder scanners or duplicate Event rows. Non-temporal attention, such as a future approval or system failure, must retain separate semantics.

## Operational and historical records

| Record | Meaning | Must not be confused with |
| --- | --- | --- |
| Reminder policy/override | Rules that decide when a source occurrence should attract attention. | Event or Notification. |
| Inbox item / Notification | Durable actionable attention produced for a due condition. | Reminder definition or source mutation. |
| Inbox action | Append-only delivery and state-transition history. | Current Inbox projection. |
| Audit event | Historical fact about a platform mutation or finding disposition. | Real-world Event or Timeline item. |
| Scheduled Job | Registered local work with a schedule and catch-up policy. | Calendar Event or arbitrary code. |
| Job Run | One execution attempt for a Scheduled Job. | Automation Run. |
| Automation Rule | Registered deterministic trigger/action configuration. | Scheduled Job, agent or executable script. |
| Automation Run | One idempotent execution for a stable trigger identity. | Job Run or canonical Event. |
| Data-quality finding | Recalculated deterministic warning over canonical facts. | Persisted canonical record; only user disposition persists. |
| Inference suggestion | Reviewable derived Relationship candidate. | Confirmed Relationship. |

Reminder delivery identity includes source, logical occurrence, due instant, timing and reason. Re-evaluating unchanged inputs does not duplicate delivery. One source occurrence/reason has at most one active or snoozed Inbox item; historical timing attempts and transitions remain retained.

Operational actions do not mutate their canonical source unless an explicitly authorised service operation says so. Current registered automation evaluates reminders and cannot create, edit, archive or delete a canonical Event.

## Relationships

A Relationship is a canonical assertion connecting any two canonical entities. One stored row carries:

- source and target entity IDs;
- one taxonomy-backed Relationship Type;
- optional status, dated interval, date certainty and notes;
- lifecycle, provenance and inference-origin metadata where applicable.

The type definition supplies valid endpoint kinds, canonical direction and forward/reverse language. The UI may ask from either endpoint's perspective, but saving normalises to one canonical direction. Bidirectional navigation is derived rather than represented by duplicate inverse rows.

Relationship types are controlled, pair-aware definitions. Legacy definitions may remain readable but non-selectable. Family types store neutral canonical meaning—Parent/child or Sibling—while a Person's optional sex can refine display labels such as Mother/Father/Parent. Sex does not alter the stored fact.

Relationships are ongoing unless explicitly former or ended. Exact, approximate and unknown date certainty qualifies structured dates; an approximate date is the closest known date plus a marker, not a partial date or range.

### Deterministic family inference

Manual parent/child Relationships are source facts. The inference engine may suggest only bounded bloodline conclusions: grandparent/grandchild, full sibling, aunt/uncle with niece/nephew, and cousin. It does not infer step, adoptive, half, foster, guardian, in-law or partner meaning.

A suggestion is not canonical until confirmed. Confirmation creates an ordinary editable Relationship and preserves its rule, supporting Relationship IDs and evidence fingerprint. Rejection suppresses unchanged evidence. Later evidence changes invalidate pending suggestions and flag confirmed evidence as changed without deleting the confirmed Relationship.

## Controlled and reference information

Use the smallest model that preserves meaning:

- Small domain-specific statuses/types may be validated text, with custom values only where intended.
- Reusable shared values such as languages, regions and ethnicities are stable reference items linked to entities.
- Hierarchical classifications use taxonomies.
- Measurements store a canonical value plus selected display unit.

Reference data is a selection aid, not an inference source. Presentation labels, units and catalogue hierarchy must not become duplicate canonical facts.

## Geographic meaning

Location is the canonical geographic entity. People and Organisations connect to Locations through Relationships rather than own duplicate address fields. An Asset may either connect to a Location or hold direct coordinates when that is the best known fact.

The Map derives markers from canonical records:

- Locations with coordinates;
- People or Organisations connected to a coordinate-bearing Location;
- Assets with direct coordinates or a qualifying Location Relationship.

Missing coordinates affect map eligibility, not Location validity. Projects, Documents and Events are not map-marker entities in the current model. Richer geometry, regional data and routing remain Phase 3 planning questions.

## Ontology checks for new work

Before adding a record type, ask:

1. Is it a real-world object/assertion, configuration, a derived projection, or operational history?
2. Who owns its canonical facts and lifecycle?
3. Can it be derived from an existing source instead of stored again?
4. Does it need independent user editing, Relationships, audit and recovery?
5. Could a shared reference, taxonomy, occurrence provider or existing operational record express it cleanly?

These questions prevent convenience views, caches and workflow state from becoming parallel sources of truth.
