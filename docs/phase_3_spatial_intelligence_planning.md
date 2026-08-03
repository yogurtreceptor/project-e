# Phase 3 Planning Workspace: Spatial Intelligence

## Status, purpose and authority

**Phase 3 — Planning in progress.** Spatial Intelligence is the current phase focus. This document records the desired end state, accepted direction, architectural boundaries, candidate capabilities and unresolved questions while the phase is shaped through use, research and explicit implementation prompts.

This is not a fixed release checklist, detailed specification or implementation authority. The capability envelope may expand, contract or change as practical work reveals better approaches or makes an idea disproportionate. Every implementation still requires explicit user authorisation, and completed work must be recorded separately from proposals.

Phase 2 is a complete development milestone. Its delivered Event, Calendar, reminder, Inbox, scheduler and deterministic-automation capabilities are current platform foundations rather than open Phase 3 work.

AI assistance and agent workflows are not assigned to a numbered later phase. They are postponed indefinitely as a primary focus, but they are not categorically banned: a small, bounded capability may be considered through its own explicit authorisation when it solves a demonstrated problem without bypassing canonical data, validation, audit, privacy or user control.

## Phase direction

Project E's first three platform layers can be understood as:

```text
Phase 1 — What exists
Phase 2 — When it matters
Phase 3 — Where it is and how to reach it
```

Phase 3 adds spatial intelligence to Project E. It should make location, geometry, distance, movement, travel time and reachability useful operational concepts across the same canonical information platform.

The goal is not general mapping-product parity. It is a private spatial layer that understands Project E's own Locations, records, relationships, Events, mobility preferences and routing policies.

## Planning approach

The phase is framed from the desired end state before its implementation sequence is known. Workstreams and capability groups below are therefore related areas of exploration, not a promised order. Early practical slices should establish reusable boundaries and allow real use to guide what follows.

Features may be revised or removed when they prove impractical, unsafe or insufficiently useful. Better capabilities may be added when they fit the phase direction and receive explicit authorisation. Planning should remain clear about current behaviour, accepted intent, open research and completed delivery.

## Current platform foundation

Project E already has:

- canonical Location entities containing address fields, optional latitude and longitude, source and notes;
- ordinary Relationships connecting Locations to People, Organisations, Assets, Projects, Documents and Events where valid;
- a derived Map view with toggleable Location, Organisation, Person and Asset markers;
- optional OpenStreetMap tiles and Nominatim address lookup, with manual entry and textual fallback when network resources are unavailable;
- canonical Events that may relate to Locations through the shared Relationship system;
- local Calendar, reminder, Inbox and deterministic scheduling services that may later consume carefully defined spatial results.

The current implementation does not yet model rich geometry, entrances, access points, spatial policies, mobility profiles, routing networks, transit data, journeys, travel-time matrices or reachability. Projects, Documents and Events do not currently appear as Map layers. Phase 3 planning does not claim these capabilities already exist.

## Core outcomes

A mature spatial layer should allow Project E to:

- represent meaningful places with suitable point, boundary and access context;
- explore canonical and related records through a richer Map projection;
- plan journeys between canonical Locations or deliberately selected map points;
- account for personal pace, transfer, preparation, access and routing preferences;
- explain route choices, estimates, exclusions and uncertainty;
- compare travel time and reachability among important Locations;
- connect Event destinations to journey and leave-by planning;
- retain useful local spatial capability in installed regions without making WAN access a prerequisite for personal records;
- distinguish canonical personal information from replaceable map, routing and timetable data.

## Spatial information model

### Canonical Locations

A canonical Location is a place that is meaningful enough to store inside Project E. Examples include Home, a regular workplace, a station the user wants to remember, a medical provider, a particular entrance or a named area of interest.

Browsing a map, calculating a route or passing through a transport stop must not automatically create canonical Locations. A future Map workflow may offer an easy **Save as Location** action that previews available name, address, coordinates, source and external identifiers, checks for likely duplicates and requires explicit confirmation before creation.

A Location should remain useful without complete geometry or installed regional data. Missing coordinates, boundaries or provider links affect available spatial projections, not the validity of the canonical record.

### Regional spatial data packs

OpenStreetMap geography, routing networks, public-transport stops and timetables may contain far more records than are personally meaningful. They should live in replaceable regional data packs or provider-owned indexes rather than becoming canonical entities in the main Project E database.

The intended coverage model is graduated:

- installed and personally relevant regions may provide rich local map and routing capability;
- selected areas may gain additional user-owned Locations, access points, annotations, overlays and policies;
- regions without detailed local data may retain general or optionally network-assisted coverage;
- absence or staleness of a regional pack must not make canonical records unusable.

Data-pack design must later define region selection, installation, update cadence, version identity, checksums, storage, licensing and attribution, failure recovery and whether packs are included in portability or reacquired separately.

### Links to spatial features

A canonical Location may link to one or more external spatial features, such as an OpenStreetMap object, a public-transport stop or a station entrance. Those links should allow updated data packs to improve spatial context without overwriting user-owned identity, notes, Relationships or decisions.

A transport interchange illustrates the boundary:

- the station may be a canonical Location when personally meaningful;
- platforms, entrances, lifts and nearby stops may remain data-pack features;
- an entrance or platform may be promoted to a canonical Location only when the user deliberately needs to store, relate or annotate it.

Stable external identifiers, source versions and reconciliation rules will be required to avoid duplicate truth when providers change.

### Geometry with distinct meaning

Point, line and polygon tooling may be shared, but stored geometry must retain its purpose:

- **Place geometry** describes a real Location, boundary, entrance or access point.
- **Interest overlays** highlight an area, route or set of points for information, exploration or comparison.
- **Routing-policy geometry** represents an avoidance zone, preferred corridor or other rule that changes route selection.

An arbitrary drawn shape should not silently become a canonical Location or an active routing rule. Creation workflows must make the intended meaning and consequence explicit.

### Provenance, confidence and time

Coordinates, boundaries, access points, provider links, route estimates, mobility observations and policy inputs should identify their source and relevant version or observation time. Provider values, generic estimates, user-entered facts, calibrated values and manual overrides must remain distinguishable.

Phase 3 should not solve richer provenance by adding unrelated confidence fields wherever convenient. Spatial provenance must fit the platform's wider evidence, audit and review direction while remaining useful for route explanation and data refresh.

## Location spatial dashboard

A mature Location page may become the canonical operational view of a place while retaining the established concise Overview and specialised-view grammar.

Potential context includes:

- identity, aliases, address, place type and verification state;
- coordinates, boundary, parent area, entrances and access points;
- related People, Organisations, Events, Projects, Assets and Documents;
- upcoming Events and other useful temporal projections;
- access instructions, opening hours, parking and personally recorded notes;
- nearby canonical Locations and transport features;
- travel times from Home or other selected key Locations;
- available modes, relevant policies and reachability.

Large maps, route displays and comparison tools should remain specialised views rather than making the ordinary Overview an overloaded dashboard.

## Map 2.0

Map 2.0 should be a platform projection over canonical records, Relationships, regional spatial features and explicit user-owned overlays. It should not become a competing data store or isolated mini-application.

Candidate capabilities include:

- search, select and open canonical Locations;
- create or save a Location from a map feature or selected point through a confirmed workflow;
- display point, line and area geometry;
- display and filter canonical Locations and related People, Organisations, Assets, Events, Projects and Documents as toggleable layers;
- project non-geographic records at their related Locations without pretending those records own independent coordinates;
- make records related to several Locations understandable rather than duplicating or arbitrarily choosing one marker;
- display routes, access points, avoidance zones, preferred corridors, boundaries and reachable areas;
- identify missing, conflicting or stale coordinates and provider links;
- preserve focused context when moving between the Map and canonical entity pages;
- provide keyboard-accessible controls, labelled non-colour distinctions and a useful textual alternative for represented information;
- remain explicit and useful when optional tiles, providers or detailed regional packs are unavailable.

## Journey planning

The flagship outcome is a personal journey-planning and spatial-decision system that operates on Project E's own records and policies.

Potential modes include walking, running, cycling, driving, public transport and multimodal combinations. The capability envelope includes departure-time and arrive-by planning, transfers, access legs, preparation and transfer buffers, route preferences and exclusions, accessibility constraints and explainable route selection.

Journey endpoints may initially be canonical Locations or manually selected map points. Live location, continuous tracking and location history are deliberately deferred because they introduce device, permission, privacy, accuracy and mobile-workflow questions. A later one-time **Use current location** action may be considered without creating stored position history by default.

### Events and destinations

An Event continues to relate to an ordinary canonical Location through the shared Relationship system. It does not gain a duplicate address or embedded map position merely for routing.

Journey planning may choose a more precise access point, such as a clinic entrance or station entrance, when calculating a route to that Event. The access choice belongs to the journey-planning context unless the user deliberately saves it as durable Location information. When several Location relationships or access points make the destination ambiguous, the planner should ask rather than guess.

A future Event integration may show expected travel time, a leave-by calculation and conflicts. It must not silently create or mutate a canonical travel Event, reminder or routing preference. Any such consequential write requires its own explicit workflow and authority.

### Routing ownership

Project E should own the provider-independent routing contract, spatial policies, canonical inputs, cache identity, explanations and user experience. The preferred direction is locally calculated routing where practical, using installed OpenStreetMap and transport data.

Whether the calculation is implemented directly in Project E or delegated to a proven free/open-source engine running locally is an implementation-feasibility decision. A justified local dependency or runtime may be preferable to reproducing complex road parsing, turn restrictions, pathfinding optimisation and public-transport timetable algorithms. Network routing, if explored, remains optional and replaceable rather than the sole holder of route truth.

Routing research must distinguish basemap rendering, geocoding, road or path routing, public-transport timetable routing and real-time enrichment; one provider or data format need not own every concern.

## Personal mobility profiles

Published travel times are generic estimates. Project E should eventually represent how the user actually moves without silently learning or overwriting behaviour.

A profile may include:

- walking, running or cycling pace;
- maximum comfortable distance by mode;
- preparation, parking, access and transfer buffers;
- slope, stairs and accessibility constraints;
- source, observation date, confidence and effective period;
- manual overrides and explicitly accepted calibration.

Travel-time output should distinguish published, generic estimated, user-configured, historically observed and manually overridden values. Calibration must be visible, attributable, reviewable and reversible. The storage and retention of detailed movement observations require a later privacy decision; raw location history is not implied by this phase direction.

## Personal routing policies

Routing policies should be structured and inspectable rather than hidden preferences. Early policy work may begin with mode, pace, distance, stairs and buffer choices. The intended phase outcome includes avoidance zones that alter routing and visibly explain their effect.

Possible later policies include:

- avoid an address, area, radius, segment, crossing or transfer point;
- prefer a route, corridor or useful intermediate stop;
- avoid stairs, tolls, motorways or other unsuitable infrastructure;
- require additional preparation, parking or transfer time;
- apply a policy only for a mode, direction, time or effective period.

Terms such as safe, well-lit, populated or accessible depend on incomplete and time-sensitive evidence. The interface must present them as attributed preferences or dataset claims, not safety guarantees.

A route explanation should identify applied policies, estimate sources, meaningful uncertainty and why the result differs from an unconstrained or provider-default route. It must also explain when no route can satisfy the active constraints.

## Spatial decision tools

### Travel-time matrix

Compare travel times among important Locations across selected modes, scenarios, profiles and policies. Each result should retain enough source and data-version context to explain or refresh it.

### Reachability explorer

Answer questions such as what can be reached within a selected time, which canonical services remain reachable under a route exclusion, or what area is practical from a candidate home. Reachability should follow the applicable transport network rather than drawing unexplained geometric circles.

### Location comparison

Compare Locations using configurable criteria such as travel time, transport access, nearby services, parking, accessibility, environmental context, personal policies, related People or Organisations and recurring commitments. A comparison is a derived decision view, not a new source of Location truth.

### Nearby exploration

Nearby exploration should initially use a user-selected canonical Location or temporary map point as its origin. It may surface relevant canonical Locations and related records without depending on the retired Task subsystem or silently inferring the user's present position.

## Platform integration

Spatial intelligence should be exposed as shared services rather than one isolated feature. Candidate integrations include:

- Event destination, travel-time, leave-by and conflict projections;
- Calendar access to journey planning without silent canonical mutation;
- Inbox attention for a deliberately defined and authorised travel condition;
- Location context on People, Organisations, Projects, Assets and Documents;
- toggleable Event, Project and Document Map layers projected through related Locations;
- spatial grouping for any future, separately designed work-item or errand capability;
- later Environment or Transport capabilities interpreted against canonical Locations;
- the same validated spatial queries for the human interface, deterministic automation and any later explicitly authorised assistance.

The retired experimental Task entity is not a current integration target and creates no compatibility requirement for future work management.

## Persistence and lifecycle boundaries

The intended classification is:

- canonical Locations and their user-owned identity remain canonical entity data;
- mobility profiles and routing policies are durable, inspectable configuration or policy records;
- installed map, routing and timetable datasets are replaceable local data packs;
- links from canonical Locations to provider features are durable references with provenance;
- route responses, travel-time matrices and reachable areas are derived results or versioned caches unless a later workflow deliberately saves a user-owned journey;
- temporary points and one-time access choices remain transient unless explicitly saved;
- provider payloads never become canonical merely because they were returned by a route or lookup.

Cache identity must eventually account for origin, destination, access points, mode, departure or arrival time, active profile and policies, routing-data version and timetable version. Stale results must remain distinguishable from current calculations.

Whole-platform export should preserve user-owned Locations, profiles, policies, overlays and provider references. Large reacquirable regional datasets and disposable caches should not automatically inflate personal recovery bundles; exact portability rules remain an implementation decision.

## Privacy, safety and local-first constraints

Spatial records can reveal home, appointments, routines, sensitive relationships and deliberately avoided places. External lookup or routing may disclose endpoints and policy information even when no canonical mutation occurs.

Phase 3 design must therefore define:

- which calculations remain entirely local;
- when a network provider is contacted and what is disclosed;
- explicit provider selection or consent where sensitivity warrants it;
- separation of personal policy from provider requests where practical;
- retention and deletion of observations, caches and route history;
- offline and stale-data behaviour;
- clear limitations for accessibility, environmental and safety-related claims.

The preferred direction is rich local capability in installed regions with replaceable optional online enrichment elsewhere. Core personal records and manually entered spatial facts remain usable without WAN access.

## Candidate workstreams

These workstreams describe related concerns, not a committed implementation sequence:

### Spatial foundations

Location semantics, geometry, access points, hierarchy, provider references, provenance, regional data packs, spatial query contracts, cache identity and lifecycle boundaries.

### Map 2.0

Canonical and derived layers, drawing and selection tools, Save as Location, routes, policies, overlays, comparison, accessibility and degraded operation.

### Routing and journey planning

Walking and other modes, local-engine feasibility, public-transport data, mobility profiles, policies, explanations, Event destinations and leave-by calculations.

### Spatial decision tools

Travel-time matrices, reachability, nearby exploration, Location comparison and policy-aware scenario analysis.

### Platform integration

Shared spatial services for Events, Calendar, Inbox and canonical entity views, with future integrations added only when their own domain capability exists.

## Completion signals

Phase 3 should be judged by a useful integrated spatial system rather than a rigid count of features. Expected end-state signals currently include:

- canonical Locations can carry reliable, attributable spatial identity without requiring every map feature to become an entity;
- rich local regional data can be installed or replaced without becoming canonical personal data;
- a Location can be saved easily from a map feature through a reviewed workflow;
- Location pages and Map 2.0 expose useful point, area, access and relationship context;
- canonical and related records can be explored through understandable toggleable Map layers;
- journeys can be planned between canonical Locations or deliberate map points using at least one useful locally available routing mode;
- at least one personal mobility profile affects an explained estimate;
- avoidance zones affect route selection and the difference is explained;
- travel times or reachability can support a meaningful Location decision;
- an Event Location can initiate journey planning and use a more specific access point where needed;
- derived routes and provider data do not become duplicate canonical truth;
- spatial privacy, degraded operation, data version and uncertainty remain visible and controlled.

These signals may be amended when implementation evidence demonstrates that a different boundary better serves the phase direction.

## Explicit deferrals

Phase 3 does not presently commit to:

- global offline map or routing completeness;
- full parity with commercial general-purpose maps;
- live turn-by-turn navigation;
- continuous location tracking or retained location history;
- a mobile application;
- opaque or AI-selected routing;
- silent behavioural learning or calibration;
- real-time traffic or transit as a core dependency;
- social reviews or public place ratings;
- safety guarantees based on incomplete spatial attributes;
- automatic creation or mutation of canonical Events, Locations, reminders or policies;
- bulk promotion of imported spatial features into canonical entities;
- a particular routing engine, geometry library, provider or data-pack format before feasibility work is authorised.

## Open planning questions

Important questions to resolve through later research and hands-on work include:

- the first installed region and practical data size for rich local coverage;
- the suitable boundary among Project E code, a local routing engine and optional network providers;
- the minimum geometry and spatial-indexing model that supports points, access points, lines and areas without premature complexity;
- how canonical Locations link to changing OSM and public-transport feature identifiers;
- public-transport source availability, timetable updates and station-complex modelling;
- policy precedence, effective dates and conflict resolution;
- useful uncertainty and provenance presentation for ordinary route decisions;
- offline basemap, geocoder, routing and data-pack installation experience;
- which spatial caches are worth retaining and for how long;
- the exact interaction among Event Location, access-point selection, leave-by calculation and reminders;
- which additional capability should follow once real use demonstrates the first spatial foundation.

## Phase 3 expansion workspace

**Planning only:** no Phase 3 implementation is authorised or recorded complete yet. Dated, numbered **Complete:** entries belong here only after explicitly authorised implementation has been delivered and verified.

## Guiding principle

> **Make location and movement first-class operational concepts across Project E without turning replaceable spatial data into competing personal truth.**
