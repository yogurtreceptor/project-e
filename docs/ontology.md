# Ontology

Operation Eddy models real-world information as entities and relationships.

## Entities

An entity is the canonical record for one real-world object.

Every entity has:

- a stable identifier
- an entity type
- a display name
- notes or descriptive fields where useful
- creation and update timestamps

Stage 1 entity types are:

- Person
- Organisation
- Location
- Project
- Document
- Asset

Each real-world object should have one canonical entity record. Create and edit flows warn about possible matches using normalized names and a small set of strong domain fields, but users may explicitly save anyway when two real objects genuinely share those values.

## People

A Person represents a real person.

Current fields include display name, title, given name, middle name, family name, preferred name, optional sex, birthday, email, phone and notes. Sex is optional and used only where it can improve relationship display labels, such as father/mother/parent or brother/sister/sibling. Email and phone remain direct Person fields for Stage 1 simplicity; contact methods may later become first-class related records if the model needs richer communication history or multiple contact points.

## Organisations

An Organisation represents a company, institution, group, team or other organisation.

Current fields include organisation name, organisation type, website, phone, email and notes. Organisation type is a controlled value with sensible presets and custom values when the preset list is too narrow.

Website, phone and email remain direct Organisation fields for Stage 1 simplicity; they may later become contact-method or communication-related records.

## Locations

A Location represents a place, address or meaningful area.

Current fields include location name, address lookup, address, address line 1, address line 2, suburb, city, state, post code, country, latitude, longitude, source and notes.

Maps are a later view over Location data, not the foundation of the Location model.

## Projects

A Project represents ongoing work or an area of responsibility. Projects organise information and relationships; they are not task-management records.

Projects can relate to People, Organisations, Locations, Documents, Assets and other Projects.

Current fields include project name, project type, status, started date and notes. Project type is controlled with custom values allowed. Status is controlled and uses Active, Paused, Completed or Abandoned.

## Documents

A Document represents a first-class document record, optionally backed by a locally uploaded file. The Document owns that file: replacement removes the superseded unreferenced file, and deleting the final referencing Document removes it from local storage.

Documents should be linked to other entities through relationships. A passport, receipt, manual or contract is a Document entity and should not be stored inside the Person, Asset, Organisation or Project it concerns.

Current fields include document name, document type, document date, issuer / created by, notes and optional local file metadata. Document type is controlled with custom values allowed.

## Assets

An Asset represents a physical or digital item such as a vehicle, laptop, phone, passport, appliance or smart device.

Assets can relate to People, Organisations, Locations, Projects and Documents. Assets may also carry direct coordinates when that is the most accurate available geographic information.

Current fields include asset name, asset type, status, serial number / asset number, acquisition date, value, latitude, longitude and notes. Asset type and status are controlled with custom values allowed. Value is stored as whole-number text and displayed with a dollar sign on read pages.

## Controlled Values

Controlled category fields are stored directly in their typed table columns as text. Preset-backed custom fields use the same column as preset values, so a custom organisation type or asset type is not a separate lookup-table record in Stage 1.

Current controlled fields are:

- Organisation `organisation_type`: Business, Government agency, School, University, Medical practice, Employer, Bank, Utility, Club, Charity, Political party, Other, or custom.
- Project `project_type`: Personal, Work, Education, Health, Finance, Home, Vehicle, Travel, Civic, Other, or custom.
- Project `status`: Active, Paused, Completed, Abandoned.
- Document `document_type`: Identification, Certificate, Contract, Receipt, Invoice, Manual, Medical, Government, Letter, Image, PDF, Other, or custom.
- Asset `asset_type`: Vehicle, Appliance, Tool, Electronic device, Computer, Phone, Document-like asset, Smart device, Furniture, Other, or custom.
- Asset `status`: Owned, Sold, Lost, Destroyed, In disrepair, Loaned out, Other, or custom.

## Relationships

A relationship is a first-class record connecting two canonical entities.

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

Relationships are editable and directly navigable from entity pages and the relationship browser. Creation and day-to-day editing should happen primarily from an entity page, because users usually think from one known entity outward. A single relationship can connect any two canonical entities, regardless of entity type.

The database stores one relationship row. Bidirectional navigation is derived from source, target and relationship type metadata rather than duplicated inverse records. Entity pages group relationships by connected entity type: People, Organisations and Locations.

Relationship creation is entity-first and perspective-based. Users start from the known entity page, choose either the existing-entity workflow or the new-entity workflow, then answer one question using explicit names: `What is [connected entity] in relation to [current entity]?` For existing entities the connected entity name is shown directly; for new entities the question updates live as the name is typed. Saving returns to the original entity page and the relationship appears from both connected entities with the inverse label derived automatically.

## Relationship Types

Relationship types are ordered definitions, not free-floating labels. The authoritative grouped catalogue is `app/relationship_catalog.py`; behavior that consumes it remains in `app/relationships.py`. Each definition includes:

- allowed source entity type
- allowed target entity type
- category
- subtype
- forward display label
- reverse display label
- whether direction matters
- optional usage notes
- whether the type is selectable for new relationships

The UI filters relationship options from these definitions after it knows the two endpoint entity types. Creation happens from the current entity page and asks what the named connected entity is in relation to the named current entity. The selected role is translated into the canonical source -> target direction so users never choose both sides manually.

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

Person-to-Person family definitions use neutral canonical types such as Parent / child and Sibling rather than storing Brother, Mother or Father as new relationship types. Display labels may become sex-specific when the viewed Person has Sex recorded as Female or Male. If Sex is Other or Unknown, neutral labels are used. For example, Parent / child can display as father of, mother of or parent of from the parent side, and son of, daughter of or child of from the child side.

Legacy generic or gendered keys such as `located_at`, `mother_of`, `father_of`, `child_of`, `related_to` and `associated_with` are preserved so existing relationships still load. They are not offered for new pair-specific relationship creation. Safe legacy location relationships continue to feed Geography and Map views.

Phone numbers, emails and websites remain simple direct fields in Stage 1. The recommended future approach is a lightweight Contact Method model linked to any entity, with method type, value, label, preferred status, validity dates and notes. That should be introduced only when multiple contact points or richer communication history justify it; it should not become a Communications domain during Stage 1.

## Relationship Dates

Relationship dates support exact calendar dates plus certainty metadata.

Current certainty values are:

- exact
- approximate
- unknown

This preserves uncertainty without blocking structured date entry.

## Geographic Ontology

A Location is the canonical geographic entity for a place, address or meaningful area. It may have a human-readable address, structured address fields, optional latitude/longitude and a geocoding source.

People and Organisations should be connected to Locations with `located_at` relationships when place information is known. They should not duplicate address fields.

The Map is a view over these canonical entities:

- Location markers represent Location entities with valid coordinates.
- Organisation markers represent Organisations connected to a coordinate-bearing Location.
- Person markers represent People connected to a coordinate-bearing Location.
- Asset markers represent Assets with valid direct coordinates or Assets connected to a coordinate-bearing Location.

Missing coordinates do not invalidate a Location. They only prevent that record, and entities relying on it, from appearing as markers.

Projects and Documents never appear as map markers.
