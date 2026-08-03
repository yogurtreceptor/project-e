# Phase 3 Planning Workspace: Spatial Intelligence

## Status and authority

**Planning only.** This document defines an evolving desired boundary, candidate capabilities and open decisions. It is not implementation authority or a fixed release checklist. Delivered work may be recorded only after an explicit implementation prompt.

Phase 3 aims to make place, geometry, distance, movement, travel time and reachability useful across Project E without turning maps, providers or routing datasets into competing personal truth.

## Accepted direction

### Canonical Locations

A Location is a personally meaningful canonical place: home, workplace, provider, station, entrance or named area worth storing and relating. Browsing a map, calculating a route or encountering a transport stop never creates one automatically. A future **Save as Location** workflow should preview provider facts, check likely duplicates and require confirmation.

Locations remain valid without coordinates, complete geometry or installed regional data. Missing spatial enrichment limits projections, not canonical identity.

### Regional data and provider links

Large basemap, address, road, routing, transport and timetable datasets belong in replaceable regional packs or provider-owned indexes—not the main entity database. Pack design must eventually define coverage, installation/update, versions/checksums, attribution/licensing, failure recovery and portability/reacquisition.

A canonical Location may retain stable links to provider features such as an OpenStreetMap object, stop or station entrance. Provider updates may improve context but never overwrite user-owned identity, notes, Relationships or decisions. Personally meaningful provider features may be deliberately promoted to Locations; most remain external features.

### Geometry, provenance and policy

Shared point/line/polygon tooling must retain the geometry's purpose:

- place geometry describes a Location, boundary or access point;
- an interest overlay supports exploration/comparison;
- routing-policy geometry changes route selection.

Drawing a shape does not silently create a Location or activate policy. Spatial facts and estimates identify provider/data version, source and relevant observation/effective time. User facts, provider values, generic estimates, calibrated values and overrides remain distinguishable.

## Candidate capability envelope

| Area | Candidate outcome | Boundary |
| --- | --- | --- |
| Location views | Spatial identity, aliases, address, geometry, hierarchy, access points, related records and useful nearby/travel context. | Keep ordinary Overview concise; large maps/comparisons use specialised views. |
| Map 2.0 | Search/select/save Locations; point/line/area display; canonical and Relationship-projected layers; routes, access points, overlays and spatial-quality findings. | Map remains a projection with textual/degraded alternatives, never a second store. |
| Journey planning | Walking, running, cycling, driving, public transport and multimodal routes; depart/arrive-by, buffers, transfers, preferences and exclusions. | Endpoints are Locations or deliberate temporary points. No continuous tracking or silent Event mutation. |
| Event integration | Plan from an Event Location, choose a precise access point, show travel/leave-by and possible conflicts. | Access choice remains journey context unless explicitly saved. Ambiguity asks rather than guesses. |
| Mobility profiles | User-configured pace, distance, preparation/parking/transfer buffers, slope/stair/accessibility limits and accepted calibration. | Source, effective period and override remain visible; no silent behavioural learning. |
| Routing policies | Structured mode/time/direction-specific avoidance zones, corridors and infrastructure preferences. | Results explain applied policy, estimate source, uncertainty and unsatisfied constraints; never promise safety. |
| Decision tools | Travel-time matrix, reachability, Location comparison and nearby exploration. | Results are derived views with scenario/data-version context, not new Location facts. |

Project E should own provider-independent inputs, policy, cache identity, explanations and user experience. A proven free/open-source local routing engine may be preferable to reproducing road parsing, turn restrictions, pathfinding and timetable algorithms. Network routing, if explored, remains optional and replaceable.

## Platform integration

Spatial intelligence should be a shared service rather than an isolated map application. Candidate consumers include Location/entity views, Event/Calendar journey planning, deliberate Inbox travel conditions, Project/Document/Asset context and later explicitly authorised deterministic or AI assistance.

Events continue to relate to ordinary Locations through Relationships; they do not gain duplicate address/geometry columns for routing. The retired Task model creates no compatibility requirement for future work/errand capability.

## Persistence and lifecycle

| Information | Intended ownership |
| --- | --- |
| Location identity and user-owned geometry/annotations | Canonical entity data. |
| Provider feature links | Durable references with provenance/version context. |
| Mobility profiles and routing policies | Inspectable durable configuration/policy. |
| Basemap/routing/timetable datasets | Replaceable regional packs. |
| Routes, matrices and reachable areas | Derived results or versioned caches unless explicitly saved as a user-owned journey. |
| Temporary points/access choices | Transient until deliberately saved. |

Cache identity should account for origin/destination/access point, mode, departure/arrival time, active profile/policies and routing/timetable versions. Staleness remains visible.

Whole-platform export should preserve user-owned Locations, geometry, overlays, profiles, policies and provider references. Large reacquirable packs and disposable caches should not automatically inflate personal recovery bundles.

## Privacy, safety and degraded operation

Spatial records can reveal home, appointments, routines, sensitive Relationships and avoided places. Before implementation, define:

- which calculations remain local;
- when a provider is contacted and exactly what is disclosed;
- provider choice/consent for sensitive queries;
- separation of personal policy from provider requests where practical;
- observation, cache and route-history retention/deletion;
- offline and stale-data behaviour;
- honest limitations for accessibility, environment and safety claims.

The preferred direction is rich local capability in installed regions with optional online enrichment elsewhere. Core records and manually entered spatial facts remain usable without WAN access.

## Delivery approach and completion signals

Likely workstreams are spatial foundations/data packs; Map 2.0; routing/journey planning; personal profiles/policies; decision tools; and integration. Their sequence depends on authorised feasibility work and real use.

An integrated Phase 3 outcome should demonstrate that:

- canonical Locations remain distinct from external spatial features;
- a versioned regional pack can be installed/replaced safely;
- a map feature can be reviewed and saved as a Location;
- Map/Location views explain geometry, provider and degraded state;
- at least one useful local routing mode works between deliberate endpoints;
- a mobility profile and avoidance policy visibly affect an explained result;
- travel-time/reachability supports a meaningful comparison;
- Event journey planning uses a Location/access point without silent canonical mutation.

These are planning signals, not independent feature promises.

## Explicit deferrals

No present commitment exists for global offline completeness, commercial-map parity, live turn-by-turn navigation, continuous location tracking/history, mobile applications, opaque/AI-selected routing, silent learning, real-time traffic/transit as a core dependency, public reviews, safety guarantees, bulk feature promotion, automatic Event/reminder/policy mutation or a particular engine/provider/data format.

## Open decisions

- First installed region, useful coverage and practical pack size.
- Boundary among Project E, a local routing engine and optional providers.
- Minimum geometry/spatial-index model for points, access points, lines and areas.
- Stable reconciliation with changing OSM/transit identifiers.
- Public-transport data/update and station-complex modelling.
- Policy precedence, effective dates, conflict handling and uncertainty presentation.
- Offline basemap/geocoder/routing installation and cache-retention experience.
- Exact Event Location/access-point/leave-by/reminder interaction.

## Phase 3 expansion workspace

**Planning only:** add dated numbered **Complete:** entries here only after explicitly authorised implementation is delivered and verified.

> **Guiding principle:** Make location and movement first-class operational concepts without turning replaceable spatial data into competing personal truth.
