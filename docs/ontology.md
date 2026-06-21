# Ontology

Operation Eddy models real-world information as entities and relationships.

## Entities

An entity is the canonical record for one real-world object.

Every entity should have:

- a stable identifier
- an entity type
- a display name
- optional aliases or alternate names
- notes or descriptive fields where useful
- creation and update timestamps

Stage 1 entity types are:

- Person
- Organisation
- Location

Each real-world object should have one canonical entity record. Duplicate prevention is a product concern from the start.

## People

A Person represents a real person.

Useful Stage 1 fields may include name parts, display name, aliases, contact notes and general notes. Contact details should be structured where practical, but the first priority is maintainable entity identity.

## Organisations

An Organisation represents a company, institution, group, team or other organisation.

Useful Stage 1 fields may include display name, legal or alternate names, organisation type, website and notes.

## Locations

A Location represents a place, address or meaningful area.

Useful Stage 1 fields may include display name, address fields, locality, region, country, coordinates when available and notes.

Maps are a later view over Location data, not the foundation of the Location model.

## Relationships

A relationship is a first-class record connecting two entities.

Relationships should support:

- source entity
- target entity
- relationship type
- direction semantics where useful
- optional start and end dates
- confidence or status where useful
- notes
- creation and update timestamps

Relationships should be editable, searchable where useful and directly navigable from entity pages.

Example relationship types:

- person works for organisation
- person knows person
- organisation located at location
- person associated with location
- organisation related to organisation

