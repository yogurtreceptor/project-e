# Phase 3 Planning Workspace: Spatial Intelligence

## Status and intended outcome

**Phase 3 is planning only.** This document records accepted direction, current research, delivery order and decisions that require implementation evidence. It does not authorise implementation or claim that these capabilities exist.

Phase 3 adds “where it is and how to reach it” to the canonical records and operational time delivered by Phases 1 and 2. Its first useful outcome is a journey planner that calculates a walking, driving, cycling or public-transport trip, explains its assumptions, previews each stage and—after one confirmation—creates separate grouped Calendar Events. A commute is the representative workflow.

The current platform already has canonical Locations with address/optional coordinates, Relationships, a derived Map, optional OSM/Nominatim enrichment, and the Phase 2 Event/Calendar/reminder/Inbox/scheduler foundation. It does not yet have rich geometry, packs, offline search/routing, transit routing, mobility profiles, routing policies or journey groups.

> **Guiding principle:** Make location and movement first-class operational concepts without turning replaceable spatial data into competing personal truth.

## Accepted product contract

### Canonical place and derived spatial context

- A canonical Location is the user's durable identity for a meaningful place or area. Provider features, roads, stops and search results remain external context unless the user completes a reviewed **Save as Location** workflow with duplicate handling.
- People, Organisations, Events, Projects and Documents gain place through Relationships to Locations, not duplicate spatial fields. Existing Asset coordinates remain valid current data until deliberately migrated.
- User-owned geometry needs a stated role—such as representative point, boundary, entrance or route anchor—and provenance. Provider geometry, centroids and snapped network points remain distinguishable from accepted geometry.
- An entrance/access point becomes a separate Location only when independent naming, notes, Relationships, reuse or lifecycle justify it. Provider containment never silently creates canonical hierarchy.
- Maps, routes, matrices, reachable areas and nearby results are derived projections. Provider refresh may update external context but never silently overwrite canonical identity, geometry, notes, Relationships or policy.

### Providers, regional packs and partial coverage

- Canonical records and manual spatial facts remain useful without WAN access or installed packs. Basemaps, search indexes, street graphs and timetables are replaceable provider data outside the canonical database.
- Capabilities are independent: map display, search, reverse geocoding, street routing, timetable routing and live enrichment may have different providers and coverage. Every result identifies provider, local/network execution, coverage, data version, freshness and partiality.
- Optional online capability is absent/disabled by default. Deliberately enabling it permits visible automatic fallback without a button on every request. Only minimum coordinates, time, mode and constraints leave Project E; names, notes, Event titles and Relationships do not.
- Packs are declarative runtime data under ignored local storage, not executable plugins or repository content. Their manager may feel plugin-like—discoverable, separately installable, updateable and removable. Install/update uses inspect, verify, stage, validate and atomic activate/rollback; failure retains the last-known-good pack. Pack removal never deletes canonical data.
- Gold Coast LGA is the first pack target. Brisbane and Logan/intervening coverage follow as independent units or a declared corridor bundle. A boundary-only gap should offer either the adjoining LGA or a smaller bordering-suburb pack rather than require a whole LGA.
- Timetable/route-shape coverage may extend beyond installed map coverage. Available route coordinates and stops still render over blank space; enabled online tiles may supply background. Missing visual, search and street-routing capability remain separately labelled, and missing street data must not be presented as a complete access route.
- Static public-transport timetables are the default. Available live data from an enabled provider enriches them; absent or stale live data falls back visibly to the schedule.

### Journey calculation

A provider-independent request contains deliberate endpoints/access points, mode or multimodal intent, depart-at/arrive-by time, mobility profile, routing policies, buffers and requested alternatives. Ambiguous venues, access points or incompatible constraints require a decision or an honest no-result state.

A useful result includes:

- resolved endpoints and network snapping;
- alternatives split into mode/service/wait stages with distances and scheduled or estimated durations;
- named buffer assumptions and resulting leave/arrival milestones;
- applied, conflicting or unsatisfied policies;
- engine, source and timetable versions, calculation time, coverage, freshness and warnings;
- a textual itinerary equivalent to the essential map; and
- a fingerprint covering every input that affects meaning.

Routes and comparison outputs remain transient/cached unless one result is materialised to Calendar. Matrices, reachability, comparison and nearby exploration come after trustworthy single-route/search contracts.

### Mobility profiles and routing policies

- Walking uses recorded presets: **Regular walk** (default), **Fast walk/jog** and **Run**. A later **Sprint** preset may have a short maximum distance. Project E never recalculates a personal speed for every route or silently learns a new value.
- During implementation the user will measure known distances several times. A reviewed preset retains stable identity, speed/unit, source, measurement/effective date and applicability such as maximum continuous distance/duration. The initial rule applies limits per contiguous leg and warns about unusually high cumulative effort; fatigue modelling is deferred.
- If Regular walk cannot make a connection but an applicable faster preset can, the alternative is shown with a warning and requires selection. It is never chosen silently.
- Routing policy is structured, local and inspectable: hard exclusion, soft avoidance, preference or added cost/buffer scoped by mode, time, direction or scenario. Results explain its effect. Claims such as safe, accessible or well lit require attributed evidence rather than inference.

### One-time Calendar materialisation

- **Add journey to Calendar** creates one date-specific ordered journey group in one transaction. It does not create a reusable or recurring journey template; several future journeys, including a week ahead, are planned separately against their relevant timetable.
- Each stage is a canonical Event on an automatically provisioned ordinary Calendar: **Walk**, **Bus**, **Train**, **Tram**, **Ferry**, **Cycle**, **Drive** or **Wait**. These Calendars may be renamed/recoloured, have editable default reminders and accept ordinary manually created Events.
- Calendar membership alone grants no planner authority. Explicit journey-group membership locks every generated field and removes the ordinary edit action; manual Events on the same Calendar remain normal editable Events. Replan uses the planner; direct Event-level mutation is deletion only.
- Every generated stage resolves reminders through its assigned Calendar's ordinary default reminder policy, including Wait. There is no hidden journey reminder system.
- Journey scopes borrow recurrence-style language without being recurrence:
  - **This stage** keeps neighbouring boundaries fixed; an infeasible replacement is refused and offers a wider scope.
  - **This and following** preserves earlier/elapsed stages and atomically replaces or deletes the suffix.
  - **All stages** affects the future/unstarted group; elapsed stages remain history.
- Deleting a middle stage warns and leaves a visibly incomplete group; it never shifts remaining times. Changing destination partway uses **Replan this and following** from a deliberate boundary/origin/time, not inferred live position.
- Preparation, parking/access, transfer-safety and arrival buffers remain separately named planner inputs, never tiny Calendar blocks or inflated travel duration. Extra slack moves the preceding active stage earlier. Before a scheduled service it lengthens the Wait Event; before a destination Event it remains a gap. Example: a five-minute walk to a 09:15 service with five minutes' slack is Walk 09:05–09:10 and Wait 09:10–09:15; ten minutes' slack makes it Walk 09:00–09:05 and Wait 09:05–09:15.

### Live timetable enrichment

- Timetable start/end values remain the Calendar schedule. While Project E is running, any detected positive delay updates attributed live status and creates or refreshes one deduplicated local Inbox alert for that service/journey; changing estimates update the same attention rather than retiming Events or creating notification noise.
- Only cancellation or a connection made infeasible by delay may mutate the Calendar journey. Project E may atomically replan future stages using the same destination, profiles, policies and Calendar mapping, reconcile their pending reminders and notify that the journey Calendar changed. Ambiguous/no-route outcomes require attention rather than a guess.
- Provider prediction is not proof of boarding, arrival or actual travel. The confirmed schedule, latest prediction, source/time and applied replacements remain distinguishable and auditable.
- There is no background journey worker. Processing runs only while Project E is open/running. Startup catch-up reads current state only for in-progress/future journeys, never replays missed polls or updates/notifies past stages, and stops after the journey window or scoped deletion.

### Privacy, accessibility and degraded operation

- Network-backed work must disclose provider and transmitted inputs, exclude canonical/private labels, respect terms/attribution and avoid real endpoints in logs or fixtures.
- No tiles still permits coordinate lists, route lines and textual results; no geocoder permits manual entry; no router reports unavailable rather than weakening Location use. Stale/partial/corrupt packs show age, coverage and repair paths while last-known-good data remains available.
- Spatial results must have keyboard/textual equivalents and honest loading, empty, stale, partial and unavailable states. Accessibility, lighting, traffic and safety evidence is attributed and incomplete; Project E never promises a route is safe or accessible.
- User-owned Locations, accepted geometry, profiles, policies, provider references and materialised journey/audit state belong in whole-platform recovery. Reacquirable packs and disposable caches are excluded by default but retain enough manifest/configuration to reacquire them.

## Research recommendation and first evidence spike

### Pack architecture

Keep three layers separate:

1. **Source/capability packs:** immutable provider inputs, coverage, licence and manifest metadata.
2. **Derived builds:** disposable map/search/routing indexes fingerprinted by source-pack set, engine/adapter version and build policy.
3. **Personal data:** canonical spatial facts, profiles, policies and journey groups in Project E storage.

The provisional component contract is:

| Role | Format/direction |
| --- | --- |
| Boundary | Versioned official GeoPackage or build-time GeoJSON |
| Street/path source | Buffered `.osm.pbf` extract from a common snapshot |
| Timetable | Original separate Translink SEQ GTFS Schedule ZIP |
| Offline basemap | PMTiles v3 candidate, pending renderer/accessibility proof |
| Local search | Derived SQLite/GeoPackage candidate |
| Routing graph | Disposable engine-native cache, never the portable pack contract |
| Manifest/notices | `manifest.json`, checksums, versions, coverage, dependencies, licences and reacquisition data |

The Gold Coast spike should create the official buffered boundary extract, validate one portable source manifest, install SEQ GTFS separately, build a fingerprinted graph from the installed union, test internal/boundary routes and measure whether bordering-suburb cuts remain practical. Later Logan/Brisbane packs use the same source-snapshot contract; compatible source packs rebuild one union graph rather than overlay separately built engine graphs.

Research sources: [Queensland LGA boundaries](https://www.data.qld.gov.au/dataset/local-government-area-boundaries-queensland), [Translink SEQ GTFS](https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink), [GTFS overview](https://gtfs.org/documentation/overview/), [Osmium extract](https://docs.osmcode.org/osmium/latest/osmium-extract.html), [PMTiles v3](https://github.com/protomaps/PMTiles/blob/master/spec/v3/spec.md), [MapLibre PMTiles example](https://maplibre.org/maplibre-gl-js/docs/examples/pmtiles/) and [GeoPackage](https://www.ogc.org/standards/geopackage/).

### Routing engine

Project E should own the provider-independent adapter, stage normalisation, profile/policy translation, explanations, pack lifecycle and Calendar workflow—not its own OSM parser or pathfinding/timetable algorithms.

| Candidate | Position |
| --- | --- |
| [Valhalla](https://valhalla.github.io/valhalla/api/) | **Front-runner:** OSM+GTFS, all required modes, arrive-by, per-request walking speed, matrices/isochrones and local regional graphs. Prove transit stages, personal policy and Windows packaging. |
| [MOTIS](https://github.com/motis-project/motis) | **Primary challenger:** OSM+GTFS, all modes, geocoding/tiles and Windows binaries. Test if Valhalla import, stages or packaging disappoint. |
| [GraphHopper](https://github.com/graphhopper/graphhopper) / [OpenTripPlanner](https://docs.opentripplanner.org/en/latest/) | Comparators for custom road policy and transit correctness when the first two expose a concrete weakness. |
| [OSRM](https://github.com/Project-OSRM/osrm-backend) / custom router | Not primary: OSRM lacks integrated transit; a custom router duplicates mature network/timetable work. Consider only a bounded upstream extension after measured failure. |

Use the same Gold Coast OSM and SEQ GTFS inputs for representative walking, cycling, driving, arrive-by transit, transfer, faster-walk, distance-limit, avoidance, boundary and no-route cases. Record source/derived size, build time, memory, cold start, latency, result reproducibility, stage/service semantics, pace/policy support, stale/malformed feed behaviour and Windows operation. Keep the selected engine behind a standard-library Python adapter using a controlled subprocess or loopback service.

## Delivery order and verification

Likely dependency order, not implementation authority:

1. Gold Coast pack/engine evidence spike and decision record.
2. Spatial foundations: geometry/provenance, provider envelope and pack lifecycle.
3. Map/search/save-as-Location workflow.
4. Single-mode walking journey and explanation/cache proof.
5. Public transport and stable stage model.
6. One-time Calendar materialisation, mode Calendars, reminders and scoped lifecycle.
7. Live delay alerts and cancellation/missed-connection replacement.
8. Driving/cycling, measured profiles and one explained routing policy.
9. Matrix/reachability/comparison after route/search trust is established.

Each authorised slice begins with its concrete workflow, current-code/data constraints, representative licensed/fictional fixtures, alternatives, evidence needed, privacy/licensing/storage/failure analysis, migration/audit/portability impact, verification and rollback. A spike is evidence, not production architecture.

Verification should cover:

- fresh schema and representative upgrades without parallel spatial truth;
- adapter contracts and deterministic fictional geometry/network/timetable fixtures;
- pack integrity, incompatibility, overlap, interrupted update, rollback and removal;
- offline/refused-network, stale, corrupt and partial-coverage behaviour;
- route/profile/policy determinism, provenance and explanation;
- journey locking, scoped replan/delete, buffers, mode-Calendar mapping and reminder inheritance;
- live alert deduplication, unchanged scheduled times for delay, cancellation/missed-connection replacement, reminder reconciliation and startup/past-stage rules;
- one-time-only materialisation, audit/recovery, accessible textual/UI behaviour, performance and storage.

The full test/compile suites remain required for implementation. UI slices also need temporary-port smoke and visual/keyboard review.

## Deferred implementation decision gates

These grouped IDs preserve the earlier register while making the working set smaller. Resolving a gate does not itself authorise implementation.

| IDs | Remaining decision/evidence | Safe position already accepted |
| --- | --- | --- |
| D01, D06, D16, D18 | Pack archive/directory shape, boundary buffer, raw-input retention, prebuilt vs local build, suburb dependency closure, overlap and measured resource budgets. Prove with Gold Coast, a bordering-suburb cut and Logan/Brisbane union. | Gold Coast first; portable source packs plus disposable derived builds; independent LGA/suburb units; route coordinates survive missing map coverage; never silently claim absent routing capability. |
| D02–D05 | Geometry/provenance/index schema, access-point/hierarchy cardinality and provider-link reconciliation. Needs current-data audit, station/building workflows, upgrade fixtures and two provider versions. | Preserve existing valid Location data; one canonical truth; explicit roles/units/CRS; no inferred hierarchy, duplicate geometry truth or automatic provider relink. |
| D07, D08, D14, D19 | Map renderer/tile format, local/online search, provider consent/disclosure, optional plugin boundary and any durable overlay/saved-view identity. | Retain current Map/text/manual entry; online capability is optional, durably enabled and visible; avoid query logs; viewport/selection remain transient. No reusable saved journey. |
| D09, D12, D17 | Final engine, transit source/update workflow, station-complex semantics and native/Java acquisition/process/upgrades. Needs the Gold Coast/SEQ comparison and repeatable Windows setup. | Provider-independent adapter; Valhalla first, MOTIS challenger; static timetable default; no custom router or network-dependent core. Runtime code is not a data pack. |
| D10, D20 | Journey-group/baseline schema, cache/operational-history retention and cross-timezone handling. Needs one-time save, scoped lifecycle and cancellation replacement cases. | Unsaved results transient; materialised group retains minimum confirmed baseline/provenance/audit; Event/Calendar IANA timezone remains authoritative; no reusable template or incidental route history. |
| D11, D15 | Measured preset values/aggregation, Sprint and distance applicability, policy precedence and accessibility/environmental evidence. Needs user measurements, real engine controls and worked conflicts. | Regular walk default; named faster profiles require selection; per-contiguous-leg limits initially; no silent learning or unsupported safety/accessibility claims. |
| D13 | Exact group persistence, Calendar-role repair, initial colours/reminder timings, stage titles and scope mechanics. Needs multi-stage, unavailable-Calendar, deletion/replan and rollback cases. | Auto-provision editable Walk/Bus/Train/Tram/Ferry/Cycle/Drive/Wait Calendars; every generated stage inherits Calendar reminders; group membership alone locks fields; buffer becomes earlier movement/Wait, not an Event. |
| D21 | Live provider, enable inheritance, in-process polling/window, delay-alert identity/status persistence and disruption semantics. Needs changing delay, cancellation, platform/stop change, missed connection, stale data, startup and deletion cases. | Run only while Project E runs; any delay produces one updated local alert/status without retiming; mutate future stages only for cancellation/missed connection; reconcile reminders; ignore past stages; never infer location, boarding or arrival. |

When resolving a gate: state the workflow/IDs, inspect current code/data, collect representative evidence, compare doing less, spike the riskiest assumption, choose the narrowest reversible option and record rationale, migration, verification and reconsideration trigger. Ask before changing accepted product direction; if evidence is insufficient, keep the safe position or narrow the slice.

## Explicit exclusions

Phase 3 does not include global offline completeness, commercial-map parity, turn-by-turn navigation, continuous/personal location tracking, mobile access, a background journey worker while Project E is closed, reusable/recurring journeys, opaque AI-selected routing, silent behavioural learning, realtime data as a core/offline dependency, external push/OS notifications, public reviews, safety guarantees, arbitrary executable packs or automatic mutation outside the accepted cancellation/missed-connection journey contract.

## Completion and expansion workspace

Phase 3 is complete only when one useful installed region supports trustworthy map/search, all four intended journey modes, explained profiles/policy and at least one useful matrix/reachability/comparison workflow; one-time grouped Calendar materialisation behaves safely; optional live enrichment follows its alert/mutation boundary; pack failure/partial coverage and privacy/accessibility remain understandable; and user-owned spatial/journey state is recoverable independently of packs/caches.

Add dated numbered **Complete:** entries here only after explicitly authorised implementation is delivered and verified. Each entry should name the slice, resolved decision IDs and durable contract.
