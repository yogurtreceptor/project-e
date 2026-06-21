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
- related to

These types are intentionally generic enough for People, Organisations, Locations and future entity domains. More specific types can be added through the central relationship type definitions.

## Relationship Dates

Relationship dates support exact calendar dates plus certainty metadata.

Current certainty values are:

- exact
- approximate
- unknown

This preserves uncertainty without blocking structured date entry.
