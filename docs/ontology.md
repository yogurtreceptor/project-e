# Ontology

Project E models real-world information as entities and relationships.

## Entities

An entity is the canonical record for one real-world object.

Every entity has:

- a stable identifier
- an entity type
- a display name
- notes or descriptive fields where useful
- creation and update timestamps

Delivered Phase 1 entity types are:

- Person
- Organisation
- Location
- Project
- Document
- Asset

Phase 2 additionally delivers Event and Task as canonical peer entity types. A Task represents work to be performed, is not an Event or reminder, and may relate independently to every current peer entity through normal Relationships. Tasks are grouped by one Task list selected by the user; the list is a personal organisational category, not ownership or a second classification system. A Task may be Open, Completed or Archived. Completion is a lifecycle fact with a timestamp; Task archive and Recycle Bin deletion remain distinct.

Tasks may carry an optional all-day or timed deadline and repeatable planned sessions. A deadline is a due fact, not a Calendar interval; a session is a planned work interval projected into the Calendar without becoming an Event.

Each real-world object should have one canonical entity record.

- Create and edit flows warn about possible matches using normalized names and a small set of strong domain fields.
- Users may explicitly save anyway when two real objects genuinely share those values.

## People

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
- Preferred name is not modelled in Stage 1.
- Sex is optional and used only where it can improve relationship display labels, such as father/mother/parent or brother/sister/sibling.
- Email and phone remain direct Person fields for Stage 1 simplicity. Contact methods may later become first-class related records if the model needs richer communication history or multiple contact points.

## Organisations

An Organisation represents a company, institution, group, team or other organisation.

Current fields include:

- organisation name
- taxonomy-backed organisation classification
- repeatable other names / aliases
- website
- phone
- email
- notes

Classification is one reusable path of up to three levels rather than unrelated broad and specific text values.

Other names are normalized rows, one value per alias. They cover alternate, former, trading and abbreviated names and participate in search and duplicate review.

Website, phone and email remain direct Organisation fields for Stage 1 simplicity; they may later become contact-method or communication-related records.

## Locations

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

## Projects

A Project represents ongoing work or an area of responsibility.

- Projects coordinate information and relationships; they do not own related records. Their overview projects related upcoming Events and open Tasks through normal Relationships.
- Projects are not task-management records in Phase 1. Planned Phase 2 Tasks remain independent peer entities, linked through relationships rather than nested ownership.

Projects can relate to People, Organisations, Locations, Documents, Assets and other Projects.

Current fields include:

- project name
- project type
- status
- started date
- target date
- ended / completed date
- notes

Controlled-value rules are:

- Project type is controlled with custom values allowed.
- Status is controlled and uses Active, Paused, Completed or Abandoned.

## Documents

A Document represents a first-class document record, optionally backed by a locally uploaded file.

The Document owns that file:

- Replacement removes the superseded unreferenced file.
- Deleting the final referencing Document removes it from local storage.

Documents should be linked to other entities through relationships. A passport, receipt, manual or contract is a Document entity and should not be stored inside the Person, Asset, Organisation or Project it concerns.

Current fields include:

- document name
- document purpose
- document date
- identifier / reference number
- expiry date
- notes
- optional local file metadata

Document purpose is controlled with custom values allowed. It describes what the record is; uploaded MIME metadata describes file format.

Issuer and creator are relationship concepts linked to canonical People or Organisations. The Document model has no duplicate issuer/creator text field.

## Assets

An Asset represents a physical or digital thing such as a vehicle, laptop, phone, appliance or smart device. A passport, receipt, certificate, manual or similar record is a Document, not an Asset.

Assets can relate to People, Organisations, Locations, Projects and Documents. Assets may also carry direct coordinates when that is the most accurate available geographic information.

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

Field rules are:

- Asset type and status are controlled with custom values allowed.
- Value is stored as whole-number text and displayed with a dollar sign on read pages.

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

A relationship is a first-class record connecting two canonical entities. Its identity and canonical facts survive soft deletion and restoration; recycled relationships are excluded from active graph views.

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
- An ongoing relationship with a start date is shown as `Since [start date]`.

Navigation and editing work as follows:

- Relationships are editable and directly navigable from entity pages and the relationship browser.
- Creation and day-to-day editing should happen primarily from an entity page, because users usually think from one known entity outward.
- A single relationship can connect any two canonical entities, regardless of entity type.

Relationship storage and display follow these rules:

- The database stores one relationship row.
- Its taxonomy-backed definition supplies canonical endpoint direction and natural inverse labels, so bidirectional navigation is derived rather than duplicated.
- Entity pages group relationships by connected entity type across the current domains.

Relationship creation is entity-first and perspective-based:

1. Users start from the known entity page.
2. They choose either the existing-entity workflow or the new-entity workflow.
3. They answer one question using explicit names: `What is [connected entity] in relation to [current entity]?`
   - For existing entities, the connected entity name is shown directly.
   - For new entities, the question updates live as the name is typed.
4. Saving returns to the original entity page, and the relationship appears from both connected entities.

Each entity profile labels the connected entity's resolved role from that profile's perspective; storage direction remains canonical and unchanged.

## Relationship Types

Relationship types are selectable taxonomy entries, not free-floating labels.

Runtime responsibilities are divided as follows:

- `relationship_type_definitions` stores the authoritative runtime definitions.
- `app/relationship_catalog.py` supplies deterministic seeds and legacy compatibility.
- `app/relationships.py` remains the behavior facade.

Each definition includes:

- allowed source entity type
- allowed target entity type
- a taxonomy path of up to three levels
- forward display label
- reverse display label
- whether direction matters
- optional usage notes
- whether the type is selectable for new relationships

The UI uses these definitions as follows:

- It filters relationship options after it knows the two endpoint entity types.
- Creation happens from the current entity page and asks what the named connected entity is in relation to the named current entity.
- The selected role is translated into the canonical source -> target direction so users never choose both sides manually.

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

Person-to-Person family definitions follow these rules:

- They use neutral canonical types such as Parent / child and Sibling rather than storing Brother, Mother or Father as new relationship types.
- Profile role labels may become sex-specific when the connected Person has Sex recorded as Female or Male.
- If Sex is Other or Unknown, neutral labels are used.
- For example, a parent's profile displays the connected person as Daughter, Son or Child, while the child's profile displays the connected person as Mother, Father or Parent.

Legacy relationship keys are handled as follows:

- Generic or gendered keys such as `located_at`, `mother_of`, `father_of`, `child_of`, `related_to` and `associated_with` are preserved so existing relationships still load.
- They are not offered for new pair-specific relationship creation.
- Safe legacy location relationships continue to feed Geography and Map views.

Contact information follows these boundaries:

- Phone numbers, emails and websites remain simple direct fields in Stage 1.
- The recommended future approach is a lightweight Contact Method model linked to any entity, with method type, value, label, preferred status, validity dates and notes.
- That model should be introduced only when multiple contact points or richer communication history justify it.
- It should not become a Communications domain during Stage 1.

## Deterministic Family Inference

Manual parent/child relationships are source facts.

The Inference Review Queue receives only safe bloodline candidates derived by the deterministic inference engine:

- grandparent/grandchild
- full sibling
- aunt/uncle with niece/nephew
- cousin

It does not infer:

- step relationships
- adoptive relationships
- half relationships
- foster relationships
- guardian relationships
- in-law relationships
- partner relationships

Inference review follows these rules:

- Suggestions are not relationships until confirmed.
- Confirmation creates a normal editable relationship while preserving its rule, source batch, supporting relationship IDs, evidence fingerprint and timestamps.
- Rejection suppresses the same evidence fingerprint.
- Later source changes invalidate pending suggestions but only flag changed evidence on confirmed relationships.

Evidence requirements are:

- Full-sibling evidence requires the same complete known parent set with at least two parents.
- Direct-generation dates may use the younger person’s DOB alone.
- Peer and collateral dates require both DOBs.

## Relationship Dates

Relationship dates support exact calendar dates plus certainty metadata.

## Planned Phase 2 temporal entities and projections

Phase 2 is in progress. Its Phase 2A temporal normalization, Calendar foundation and management, canonical Event persistence lifecycle, standard Event relationship catalogue integration, Search/related-record Event projections, Calendar-originated Event creation/editing, Month/Week/Day Calendar projections, and scoped recurrence mutations are implemented; Task entities are the next delivery. An Event represents something that occurs, occurred or is expected to occur at an interval; the initial timed model requires bounded start and end instants. A Task represents work that should be performed. Neither requires a Project, and neither is a reminder. Both use standard relationships to connect to any appropriate entity type, including each other.

An Event has one stable canonical entity identity and belongs to exactly one Calendar. Calendars alone group, colour, order, filter and configure Events. An Event's planned time is either a precise timed interval or an all-day date interval, never both. Cancellation records that the Event will not occur, archival removes it from ordinary views, and Recycle Bin deletion identifies an erroneous record; these states are semantically distinct. Restoring a deleted Event preserves its archive and cancellation state.

Events use selectable, pair-aware standard Relationships with People, Organisations, Locations, Projects, Documents, Assets and other Events. These links are peer connections, not embedded Event foreign keys or nested ownership: an Event may have multiple links of the same or different kinds, and relationship soft deletion and restoration retain their ordinary semantics.

A Calendar is a first-class local Event grouping and configuration record; it supplies name, colour, timezone, default duration, ordering, archive state and future reminder policy without becoming a second Event store. Archiving a Calendar retains its Event assignments and blocks new selection; it does not move or archive Events. A Calendar with assigned active or recycled Events is not deletable. A calendar view is a derived projection over canonical records and traceable derived occurrences. A canonical record remains its source type; a derived occurrence is a deterministically generated temporal instance such as a birthday; a calendar projection displays either one. See [the Phase 2 plan](phase_2_plan.md) for the detailed temporal, reminder, scheduler and automation semantics.

Current certainty values are:

- exact
- approximate
- unknown

This preserves uncertainty without blocking structured date entry.

## Geographic Ontology

A Location is the canonical geographic entity for a place, address or meaningful area.

It may have:

- a human-readable address
- structured address fields
- optional latitude/longitude
- a geocoding source

When place information is known:

- People and Organisations should be connected to Locations with `located_at` relationships.
- They should not duplicate address fields.

The Map is a view over these canonical entities:

- Location markers represent Location entities with valid coordinates.
- Organisation markers represent Organisations connected to a coordinate-bearing Location.
- Person markers represent People connected to a coordinate-bearing Location.
- Asset markers represent Assets with valid direct coordinates or Assets connected to a coordinate-bearing Location.

Missing coordinates:

- do not invalidate a Location
- only prevent that record, and entities relying on it, from appearing as markers

Projects and Documents never appear as map markers.
