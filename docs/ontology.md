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

Each real-world object should have one canonical entity record. Duplicate prevention is a product concern from the start.

## People

A Person represents a real person.

Current fields include name parts, email, phone, summary and notes. The first priority is maintainable entity identity.

## Organisations

An Organisation represents a company, institution, group, team or other organisation.

Current fields include organisation type, website, email, phone, summary and notes.

## Locations

A Location represents a place, address or meaningful area.

Current fields include address lines, locality, region, country, summary and notes.

Maps are a later view over Location data, not the foundation of the Location model.

## Projects

A Project represents ongoing work or an area of responsibility. Projects organise information and relationships; they are not task-management records.

Projects can relate to People, Organisations, Locations, Documents, Assets and other Projects.

## Documents

A Document represents a first-class document record, optionally backed by a locally uploaded file.

Documents should be linked to other entities through relationships. A passport, receipt, manual or contract is a Document entity and should not be stored inside the Person, Asset, Organisation or Project it concerns.

## Assets

An Asset represents a physical or digital item such as a vehicle, laptop, phone, passport, appliance or smart device.

Assets can relate to People, Organisations, Locations, Projects and Documents. Assets may also carry direct coordinates when that is the most accurate available geographic information.

## Relationships

A relationship is a first-class record connecting two canonical entities.

Relationships support:

- source entity
- target entity
- relationship type
- direction semantics through type labels and inverse labels
- optional start and end dates
- date certainty for start and end dates
- status
- notes
- creation and update timestamps

Relationships are editable and directly navigable from entity pages and the relationship browser. Creation and day-to-day editing should happen primarily from an entity page, because users usually think from one known entity outward. A single relationship can connect any two canonical entities, regardless of entity type.

The database stores one relationship row. Bidirectional navigation is derived from source, target and relationship type metadata rather than duplicated inverse records. Entity pages group relationships by connected entity type: People, Organisations and Locations.

## Relationship Types

Implemented relationship types include:

- associated with
- knows
- works for / has worker
- located at / has location
- member of / has member
- belongs to / has item
- references / referenced by
- related to

These types are intentionally generic enough for People, Organisations, Locations and future entity domains. More specific types can be added through the central relationship type definitions.

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
