# Phase 3 Delivery and Planning Workspace: Spatial Intelligence

## Status and intended outcome

**Phase 3 is in progress.** Dated **Complete:** entries are delivered contracts; all other outcomes, ordering and candidates remain planning that does not authorise implementation or claim those capabilities exist.

Phase 3 adds “where it is and how to reach it” to the canonical records and operational time delivered by Phases 1 and 2. It has two connected primary outcomes: a map-dominant place/search workspace and a journey planner that calculates a walking, driving, cycling or public-transport trip, explains its assumptions, previews each stage and—after one confirmation—creates separate grouped Calendar Events. A commute is the representative journey workflow.

The current platform has canonical Locations with address and role-based geometry assertion history, explicit containment Relationships, the Map 2.0A canonical workspace with local coordinate rendering/search/state and explicitly requested Nominatim search, the provider-independent journey request/result/failure seam with durable mobility-profile/routing-policy identity and a disposable cache boundary, and the Phase 2 Event/Calendar/reminder/Inbox/scheduler foundation. It does not yet have installed map/search packs, a selected routing provider, calculated production routes, reviewed production profile/policy values or journey groups.

> **Guiding principle:** Make location and movement first-class operational concepts without turning replaceable spatial data into competing personal truth.

## Accepted product contract

### Canonical place and derived spatial context

- A canonical Location is the user's durable identity for one enduring physical place or area; it is not moved to unrelated coordinates. A Person, Organisation or designation such as current home moves by changing its Location Relationship. Provider features, roads, stops and results remain external context unless explicitly saved with duplicate review.
- An address describes a Location rather than becoming a standalone canonical entity. A Location may retain physical, postal, delivery and historical address assertions. **Current** means applicable now; **preferred** selects the default display/use, with at most one preferred address per purpose. Provider suggestions do not overwrite accepted values.
- A Location may hold multiple current or historical geometries. Supported concepts are point, line and area, including multi-part lines/areas, with roles such as representative point, boundary, entrance, route anchor or path. At most one geometry is preferred per role. WGS84 latitude/longitude is the portable canonical reference; exact storage encoding and engine conversions remain implementation choices.
- Each geometry/role assertion—not the whole Location—records provenance and confidence as **User confirmed**, **Source reported**, **Approximate** or **Unknown**, plus an accuracy radius only when genuinely supplied. Confidence is normally quiet metadata and becomes prominent only when uncertainty affects an action.
- Child Locations are explicit canonical records connected through typed parent/containment Relationships. A parent selection may reveal child pins and grouped sidebar details. A child may display a parent's address when it has none, but does not copy that address as duplicate truth. Provider data or future agent assistance may propose children, but neither creates them without an explicitly authorised, reviewable canonical operation.
- People, Organisations, Events, Projects and Documents gain place through Relationships to Locations, not duplicate spatial fields. Existing Asset coordinates remain valid current data until deliberately migrated.
- An entrance/access point becomes a child Location when independent naming, notes, Relationships, reuse or lifecycle justify it; otherwise it remains a geometry of its parent. Provider containment never silently creates canonical hierarchy.
- Maps, routes, matrices, reachable areas and nearby results are derived projections. Provider refresh may update external context but never silently overwrite canonical identity, geometry, notes, Relationships or policy.

### Providers, regional packs and partial coverage

- Canonical records and manual spatial facts remain useful without WAN access or installed packs. Basemaps, search indexes, street graphs and timetables are replaceable provider data outside the canonical database.
- Capabilities are independent: map display, search, reverse geocoding, street routing, timetable routing and live enrichment may have different providers and coverage. Every result identifies provider, local/network execution, coverage, data version, freshness and partiality.
- Optional online capability is absent/disabled by default. Deliberately enabling it permits visible automatic fallback without a button on every request. Only minimum coordinates, time, mode and constraints leave Project E; names, notes, Event titles and Relationships do not.
- Packs are declarative runtime data under ignored local storage, not executable plugins or repository content. Their manager may feel plugin-like—discoverable, separately installable, updateable and removable. Install/update uses inspect, verify, stage, validate and atomic activate/rollback; failure retains the last-known-good pack. Pack removal never deletes canonical data.
- Gold Coast LGA is the first pack target. Brisbane and Logan/intervening coverage follow as independent units or a declared corridor bundle. A boundary-only gap should offer either the adjoining LGA or a smaller bordering-suburb pack rather than require a whole LGA.
- Timetable/route-shape coverage may extend beyond installed map coverage. Available route coordinates and stops still render over blank space; enabled online tiles may supply background. Missing visual, search and street-routing capability remain separately labelled, and missing street data must not be presented as a complete access route.
- When a selected feature or route exposes missing capability, the existing sidebar becomes an **Improve coverage** manager without hiding the map or losing selection. It recommends relevant bordering-suburb packs using a measured proximity/corridor rule, the containing/adjoining LGA, and the optional online connection capability that reads remote data instead of installing local copies. Each choice states capability, extent, size/network use, source, attribution and persistence; nothing installs automatically.
- Static public-transport timetables are the default. Available live data from an enabled provider enriches them; absent or stale live data falls back visibly to the schedule.

### Map 2.0 workspace and search

- Map becomes a map-dominant desktop workspace inspired by familiar map applications rather than a panel followed by a long record list. A persistent search control and a results/details sidebar coexist with the map; opening a result never prevents zooming, panning or inspecting nearby context. Constrained desktop layouts may collapse the sidebar without losing selection or search state.
- Selecting a search result or clickable feature centres/highlights it with a familiar red selected pin. The pin remains while the user drags or zooms until selection is deliberately changed or cleared. Shape, outline, label and focus state keep selection understandable without relying on red alone.
- One search field groups and ranks canonical Project E results first, installed-pack addresses/places/stops second and enabled online results third. Every result shows type, source and coverage state. Search supports names, addresses and deliberate coordinates; no result is promoted or saved by selection.
- Panning or zooming never reruns a search: its ranked results remain stable until the query is changed or resubmitted, and there is no **Search this area** action. Enabled base/feature layers continue loading the data needed for the visible viewport independently of search.
- The details sidebar keeps the map visible and shows available identity, address/coordinates, provider/provenance and coverage warnings. Applicable actions are **Open canonical record**, **Save as Location**, **Directions from** and **Directions to**. Directions prefill the journey planner; saving a provider feature remains a reviewed canonical-creation workflow. Missing coverage switches the same sidebar into the contextual coverage manager above.
- Installed/online provider features such as roads/paths, addresses, businesses, parks, stations and stops are clickable while browsing, not search-only. Click opens the same non-mutating details flow and clearly distinguishes external context from canonical records.
- All canonical types can appear under a **Canonical records** layer group: Locations and Relationship-projected Organisations, People, Assets, Events, Projects and Documents. Sub-layers control visibility only and never change data; records related to several Locations must remain understandable.
- Canonical Locations use their own recognisable pin colour. If several enabled canonical records share one Location, Map shows one place pin and groups those records by type in its sidebar instead of stacking indistinguishable pins. Selection temporarily takes the accessible red selected state.
- Layer architecture distinguishes one base view from combinable overlays. Desired base views are normal map, satellite and terrain; desired overlays include canonical records, traffic, public transport, cycling, journey routes and routing-policy geometry. Each layer identifies its provider, local/network status, freshness and attribution. Unavailable layers remain visible-but-disabled with an install/enable or feasibility explanation rather than disappearing.
- The initial view uses the normal base map with canonical Locations plus available general-place and public-transport feature layers—including stops—visible. Other canonical projections and specialist traffic, cycling, journey and routing-policy overlays begin off unless the active workflow needs them; all remain user-toggleable and the user's choices persist locally.
- Map expansion is incremental. The first slice delivers the map-dominant shell, unified canonical/current-provider search, persistent selected pin, results/details sidebar and layer architecture. Installed-pack search, richer clickable features, reviewed Save as Location, coverage-manager recommendations, route overlays, nearby exploration and satellite/terrain/traffic/transit/cycle data follow as their data, licence, privacy, cost and performance gates are proven.
- Clicking unselected blank map space does not create a pin. Origins and reference points come from canonical Locations, search results or selected provider features.
- Phase 3 includes a late current-location slice. A deliberate locally stored preference and normal device/browser permission permit a one-shot device estimate; an IP-geolocation fallback is used only if its online provider is separately enabled and disclosed. Map opening priority is that current estimate, then the last viewport, then Gold Coast. The fix is transient local context unless explicitly saved as a Location: it centres the view only, with no continuous tracking, travel history or automatic journey origin. Denial/unavailability falls through without blocking Map.
- Map retains bounded, user-clearable recent searches/selections and supports durable favourites and named lists. An external provider feature may be saved to a list/favourites without becoming a canonical Location, but remains clearly labelled with provider identity and may become unavailable until its pack/provider is restored. User-owned list membership is portable; provider facts remain reacquirable external context. Exact retention and reconciliation remain D19 decisions.
- Cohesion also requires viewport-bounded loading with cancellation of stale requests, usable clustering/density handling, a sidebar back path, keyboard navigation, non-colour legends, visible attribution/offline/stale/error states and duplicate review before saving an external feature. Exact mechanisms remain implementation evidence rather than product choices.

### Journey calculation

A provider-independent request contains deliberate endpoints/access points, mode or multimodal intent, depart-at/arrive-by time, mobility profile, routing policies, buffers and requested alternatives. Ambiguous venues, access points or incompatible constraints require a decision or an honest no-result state.

Before accepting a request, an adapter declares its modes, coverage, time semantics, transit/live inputs, geometry output and supported policy controls. Project E refuses an unsupported requirement rather than silently weakening it.

A useful result includes:

- resolved endpoints and network snapping;
- alternatives split into mode/service/wait stages with explicitly labelled route distances and scheduled or estimated durations;
- named buffer assumptions and resulting leave/arrival milestones;
- applied, conflicting or unsatisfied policies;
- engine, source and timetable versions, calculation time, coverage, freshness and warnings;
- a textual itinerary equivalent to the essential map; and
- a fingerprint covering every input that affects meaning.

Distance/time meanings remain distinct: straight-line separation, network-route distance, scheduled duration, profile-based estimated duration and total elapsed journey time. Project E buffers are separate inputs, not disguised distance or travel duration.

Typed outcomes distinguish invalid/ambiguous endpoints, partial or absent coverage, unsupported mode/policy, no physically possible route, no policy-compliant route, stale/incompatible data and provider failure. **No route** is never reported when the provider merely failed.

Routes and comparison outputs remain transient/cached unless one result is materialised to Calendar. Matrices, reachability, comparison and nearby exploration come after trustworthy single-route/search contracts.

### Mobility profiles and routing policies

- Project E owns stable primary modes **Walk**, **Cycle**, **Drive** and **Public transport**. Multimodal results normalise into Walk, Wait, Bus, Train, Tram, Ferry, Cycle and Drive stages. A transfer is its real walk/wait/service sequence, not a vague extra mode.
- Mobility profiles are durable user-owned configuration translated by adapters, never provider-owned values. Pedestrian pace variants remain Walk profiles and use the Walk Calendar; future vehicle/e-bike variations likewise extend profiles or policies rather than the core mode taxonomy.
- Walking uses recorded presets: **Regular walk** (default), **Fast walk/jog** and **Run**. A later **Sprint** preset may have a short maximum distance. Project E never recalculates a personal speed for every route or silently learns a new value.
- During implementation the user will measure known distances several times. A reviewed preset retains stable identity, speed/unit, source, measurement/effective date and applicability such as maximum continuous distance/duration. The initial rule applies limits per contiguous leg and warns about unusually high cumulative effort; fatigue modelling is deferred.
- If Regular walk cannot make a connection but an applicable faster preset can, the alternative is shown with a warning and requires selection. It is never chosen silently.
- Routing policy is structured, local and inspectable: hard exclusion, soft avoidance, preference or added cost/buffer scoped by mode, time, direction or scenario. Results explain its effect. Claims such as safe, accessible or well lit require attributed evidence rather than inference.
- Feasibility/capability limits apply first. The journey may explicitly enable/disable saved policies; remaining hard exclusions must all hold, more-specific rules beat general ones, soft costs may combine and provider defaults come last. Contradictory hard rules require attention rather than a silent winner.

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

### Durability and cache boundary

- The database retains Locations, address/geometry assertions, Relationships, profiles, policies, favourites/lists and confirmed journey groups independently of every map or routing provider. Switching/removing a provider does not move or delete canonical Locations.
- Installed packs are replaceable external resources; search indexes, routing graphs and generated map data are reproducible derived builds. Both remain outside canonical truth and can be reacquired or rebuilt without personal-data loss.
- Route/geocoder/live caches are bounded local performance aids, not route history. A cache fingerprint covers meaningful request, profile/policy, adapter and source/timetable versions; lookup reports fresh hit, stale hit or miss, while the caller decides whether labelled stale display is acceptable.
- Stale cached results never silently create Events. Calendar materialisation copies the minimum schedule, stages and provenance needed for durable use and never depends on the cache surviving. A provider-only favourite may be unavailable when its source is absent until it is explicitly promoted to a canonical Location.

### Privacy, accessibility and degraded operation

- Network-backed work must disclose provider and transmitted inputs, exclude canonical/private labels, respect terms/attribution and avoid real endpoints in logs or fixtures.
- No tiles still permits coordinate lists, route lines and textual results; no geocoder permits manual entry; no router reports unavailable rather than weakening Location use. Stale/partial/corrupt packs show age, coverage and repair paths while last-known-good data remains available.
- Spatial results must have keyboard/textual equivalents and honest loading, empty, stale, partial and unavailable states. Accessibility, lighting, traffic and safety evidence is attributed and incomplete; Project E never promises a route is safe or accessible.
- User-owned Locations, accepted geometry, profiles, policies, provider references and materialised journey/audit state belong in whole-platform recovery. Reacquirable packs and disposable caches are excluded by default but retain enough manifest/configuration to reacquire them.

## Research recommendation and first evidence spike

### Pack architecture

Implement the accepted durability boundary as four layers:

1. **Source/capability packs:** immutable provider inputs, coverage, licence and manifest metadata.
2. **Derived builds:** disposable map/search/routing indexes fingerprinted by source-pack set, engine/adapter version and build policy.
3. **Bounded caches:** disposable result acceleration with explicit freshness and dependency fingerprints.
4. **Personal data:** provider-independent canonical spatial facts, profiles, policies, lists and journey groups in Project E storage.

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

## Implementation order and verification

Repository evidence at planning baseline `d11abb5` made the shared seam clear. Locations stored one flattened address and optional coordinate pair in the definition-driven typed table; the Relationship catalogue had no Location-to-Location containment type. `app/geo.py` derived point markers, while the Map was a small Leaflet page that automatically requested CDN code and OSM tiles, had no Map search/sidebar state and emitted separate markers for records sharing a place. Nominatim was a direct form-only network client. Packs, rich geometry, routing, spatial caches, profiles, policies and journey groups did not exist. Conversely, focused repositories, append-only migrations, `commit=False` Calendar/Event creation, Calendar reminder policy and the external-Calendar validate/stage/atomic-last-known-good pattern were reusable boundaries.

The order below is a dependency graph, not a fixed script. **Map 2.0 and journey planning are parallel, equal outcomes:** after the shared starting slice, their first slices may proceed together. Build only the foundation needed safely by the next outcome. A slice may be split, combined or reordered under its stated condition, with the changed dependency and verification recorded. Exact schemas, UI mechanisms, provider mappings, speeds, cache thresholds and similar choices remain inside the slice whose evidence can resolve them.

Evidence spikes produce measurements and decision records only. A provider may be explored earlier, but no new pack/search/routing provider becomes production architecture until the canonical Location/geometry and minimum profile/policy/routing/cache contracts below are complete. N2 may place the current Nominatim/OSM capability behind that neutral boundary; it does not settle the later local/online provider choice.

### Now

#### N1. Canonical place and endpoint foundation

- **Outcome:** Current Locations transition without duplicate truth to address assertions, role-based WGS84 geometry with assertion-level provenance/confidence, and explicit child/containment Relationships; existing detail, edit and Map projections continue through the preferred representative point.
- **Prerequisites:** Audit current Location values and reuse entity, Relationship, migration, audit, provenance and portability boundaries; expose only the address/representative-point/containment workflow needed next while making the storage model capable of the accepted point, line and area concepts.
- **Decision gates:** D02–D05.
- **Evidence/spike:** Prototype the narrowest schema/index/encoding options against fictional address-history, station/entrance, building/area and provider-version cases, plus a representative upgraded database.
- **Complete when:** Fresh and upgraded databases preserve existing values; preferred/current and geometry-role invariants are enforced; containment is explicit and cycle-safe; provider removal cannot move or delete canonical geometry; and current Map/text projections remain deterministic.
- **Reorder if:** Address and geometry migration risks differ enough to split them, containment can safely follow the representative-point read contract, or the migration is small enough to combine with N2 without coupling it to a renderer.

##### N1 evidence and D02–D05 resolution · 2026-08-05

The ignored current database was inspected before schema work: SQLite `quick_check` was `ok`, foreign-key violations were zero, 32 migration IDs were applied and no Location or Location Relationship rows existed. That meant there were no private place values to characterise or repair, but it did not remove the upgrade obligation. A representative pre-N1 fixture therefore carried a fictional structured physical address, WGS84 point, external source and field provenance through the real migration path.

An in-memory SQLite 3.45.1 spike exercised fictional current/historical physical and postal addresses, station/entrance containment, a building Polygon, a multi-part path and two versions of one provider feature. Partial unique indexes rejected a second preferred assertion and a second active parent; a recursive trigger rejected a cycle; and the current representative-point query used its projection index. Compact coordinates-only JSON used 67 bytes for the representative nested case versus 100 bytes for the equivalent full GeoJSON object. The address and geometry migration risks did not diverge, and coupling the migration to N2 would have weakened the neutral boundary, so the N1 slice was neither split nor reordered.

D02–D05 are resolved as follows:

- addresses are normalized purpose/status assertions; editable current forms project one preferred physical address and retain replaced values as history;
- geometries store a constrained type and compact WGS84 coordinate-array JSON in longitude/latitude order, validated with the standard library for Point, LineString, MultiLineString, Polygon and MultiPolygon; roles and current/preferred state stay queryable columns, and no spatial engine is selected;
- provenance/confidence and optional positive accuracy attach to each assertion, with provider name/reference/version copied as source snapshots; neutral provider feature references have their own removable lifecycle and no ownership of geometry;
- `contains_location` is an explicit directional Relationship with one active parent per child and repository plus SQLite cycle enforcement; parent address use is display-only inheritance;
- migration `20260805_33_canonical_place_foundation` refuses incomplete or invalid legacy coordinates, preserves valid values/provenance, removes flattened Location columns and is covered by fresh and representative upgrade tests. Whole-platform import independently validates geometry and containment.

Reconsider the coordinate encoding only when an authorised spatial engine needs measured query/index operations that compact JSON cannot serve; reconsider single active parent only for a concrete real place that cannot be represented by other Relationships without ambiguous hierarchy; and extend provider reconciliation only with N7's reviewed save/refresh evidence.

#### N2. Map 2.0A canonical workspace

- **Outcome:** A map-dominant shell provides stable unified canonical and deliberately enabled current-provider search, persistent accessible selection, one-pin shared-place grouping, results/details sidebar, canonical layer controls and a complete textual alternative without creating records on browse or blank-map click.
- **Prerequisites:** N1's representative-point and source/provenance read contract, existing canonical search/Relationship projections, and an explicit local/online capability boundary before any remote code, tile or query request.
- **Decision gates:** D07, D08, D14 and the Map-state subset of D19.
- **Evidence/spike:** Prove the renderer and server-rendered interaction seam with dense fictional shared-place data, constrained desktop and keyboard/non-colour use; specifically test removal of the current automatic CDN/tile dependency, stale viewport cancellation and stable results during pan/zoom.
- **Complete when:** Selection, sidebar/back path and query results survive pan/zoom; canonical ranking/source labels and default layers are deterministic; unavailable online resources degrade honestly; shared records remain understandable; and no interaction silently mutates or transmits canonical labels.
- **Reorder if:** The shell can begin against N1's stable read model while its migration finishes, Map-state persistence deserves a later sub-slice, or N3 offers more value while renderer evidence is unresolved.

##### N2 evidence and D07/D08/D14/Map-state D19 resolution · 2026-08-05

The renderer/server-interaction spike used the real N1 creation and projection paths with 96 dense fictional shared places and 768 related records. The N1 flat projection produced 864 markers in 171 ms median, 339 KB of compact JSON and 466 KB of rendered HTML; grouping by canonical place reduced the candidate JSON to 86 KB, while 250 viewport filters stayed below 0.9 ms. The committed page was also proven to request Leaflet from a CDN and OSM tiles automatically. These results supported N2 as one slice: the migration was already stable, Map state was small local browser state, and no N3 dependency offered a safer seam.

D07/D08/D14 and the N2 Map-state subset of D19 are resolved narrowly as follows:

- a browser-native, same-origin coordinate canvas renders canonical points with pan, zoom, accessible individual pins and zoomable density clusters; it selects no tile format, map provider, local search pack or routing architecture;
- a bounded local `/map/viewport` read endpoint returns at most 500 visible canonical place groups, identifies local execution, rejects invalid bounds and echoes a request token; the client aborts prior fetches and discards responses that are no longer newest;
- canonical search remains server-rendered and ranked before deliberate coordinates and optional current-provider results, so pan/zoom never reruns or mutates it; exact shared Locations produce one pin with grouped records and records shown at several Locations state that count;
- Leaflet CDN and automatic OSM tile requests are removed. Normal, satellite, terrain, general-place, public-transport and journey layers remain visible-but-unavailable with explanations. Nominatim is a replaceable existing query boundary used only when an off-by-default per-search control is deliberately selected; the page discloses that the entered query is transmitted, adds no canonical metadata and keeps canonical results when it fails;
- selection lives in the URL and survives viewport/sidebar/back interaction; last viewport, canonical layer choices and collapsed-sidebar state persist in failure-tolerant browser-local storage. Recents, favourites/lists, provider reconciliation and current-location state remain with N5/L1 rather than being pulled into N2.

A temporary-port Edge review with 18 dense fictional places and 108 mapped records proved wide and 820-pixel constrained layouts, no horizontal overflow, keyboard pan/zoom and focus visibility, non-colour selection/cluster/legend cues, selection and details persistence through pan/back/sidebar collapse, stable result text and zero cross-origin page resources. Reconsider the browser-native renderer when N4's selected local basemap cannot integrate without replacing it, the 500-place viewport bound proves inadequate on representative personal data, or a reviewed provider requires a materially different attribution/rendering lifecycle. No pack, tile, routing or later provider-specific architecture was selected.

#### N3. Provider-independent journey contract

- **Outcome:** A vertical fixture-backed journey seam resolves deliberate Location endpoints and defines capability declarations, request/result/failure types, distance/time meanings, normalised stages, minimum durable mobility-profile/routing-policy identity and a bounded clearable cache with dependency fingerprints—without choosing an engine.
- **Prerequisites:** N1 endpoint/geometry semantics, focused services behind `app/db.py`, ignored runtime storage for disposable cache data and fictional deterministic network/timetable fixtures.
- **Decision gates:** Contract and foundation portions of D09–D11 and D15; journey-group persistence remains D20.
- **Evidence/spike:** Exercise ambiguous endpoints, unsupported constraints, partial coverage, no-route versus provider failure, profile limits, policy conflicts and fresh/stale/miss cases through a test adapter; prototype only enough SQLite/cache structure to select the narrowest reversible contract.
- **Complete when:** An adapter cannot silently weaken a request; every meaningful input changes the fingerprint; stages and textual explanations are provider-independent; profiles/policies remain user-owned; cache clearing loses no personal data; and fixture results are deterministic.
- **Reorder if:** Pure request/result contracts and durable profile/policy/cache persistence need separate sub-slices; both must complete before a provider decision is adopted, while N2 may proceed independently after N1.

##### N3 evidence and D09–D11/D15 foundation resolution · 2026-08-05

A deterministic fictional adapter spike exercised deliberate and ambiguous Location/access-point endpoints, unsupported requirements and policy kinds, labelled partial coverage, no-route versus provider failure, contiguous profile limits, conflicting and unsatisfied hard policy outcomes, and fresh/stale/miss/corrupt cache cases. It also varied request, endpoint geometry, profile/policy revision and definition, adapter version, source version/freshness and coverage dependencies independently. These cases fit one seam: endpoint and capability refusal precede the adapter, result validation follows it, and disposable cache state remains separate from durable configuration. Splitting persistence from the pure types would have created two incomplete boundaries without reducing migration or provider risk, so N3 was neither split nor reordered.

The foundation portions of D09–D11 and D15 are resolved as follows:

- adapters declare stable identity/version, local or network execution, modes, normalized stage modes, depart/arrive semantics, static/live transit inputs, geometry, requirements, policy kinds, coverage keys and versioned source dependencies before calculation; unsupported requirements are refused, and typed failures keep invalid/ambiguous endpoint, absent/partial coverage, unsupported mode/profile/policy/requirement, no route, no policy-compliant route, profile limit, conflict, stale/incompatible data, provider failure and invalid result distinct;
- a request contains deliberate Location/geometry references, primary/access modes, timezone-aware depart-at or arrive-by time, ordered user-owned profile/policy keys, named buffers, alternative count and explicit completeness requirements. Route results preserve straight-line versus route distance, scheduled versus estimated versus elapsed duration, normalized stages, snapping, milestones, policy disposition, coverage, provenance, warnings and an essential textual itinerary;
- `mobility_profiles` and `routing_policies` retain stable user-owned keys, revisioned provider-independent JSON definitions and audited identity without installing presets or fixing measured speeds, provider mappings or the later exact D11/D15 schema. Every requested profile/policy must be reported exactly once; profile limits are checked per contiguous normalized stage and no faster profile is selected silently;
- the SHA-256 fingerprint covers the complete semantic request, resolved canonical geometry, profile/policy revision and definition, adapter declaration, coverage and source versions/freshness. A separately stored bounded SQLite performance cache under ignored runtime storage reports fresh/stale/miss, revalidates payloads before reuse, retains stale data only as an explicit candidate and can be cleared or lost without affecting profiles, policies, Locations or Events. Exact D10 retention/measurement choices remain later work;
- migration `20260805_34_journey_contract_foundation` adds only the two personal configuration tables. Whole-platform validation and recovery preserve them while excluding the disposable journey cache. Planning itself creates no Calendar Event, provider record, reusable journey or route history.

Focused fixture, endpoint, profile/policy, fingerprint, cache, failure, fresh-schema, representative-upgrade and portability tests plus the 325-test full suite passed. Reconsider the request or stage shapes only when X1 exposes a provider semantic they cannot represent without weakening meaning; specialize profile/policy definitions only from measured N6/N7/N9 evidence; and change the cache store or bounds only after representative size/latency/retention measurements. No routing engine, pack/provider choice, X1/N4 work or Calendar materialisation was begun.

### Next

#### X1. Gold Coast pack, renderer/search and routing evidence spike

- **Outcome:** One reproducible evidence package compares the Gold Coast source-pack/build route, local display/search candidates and Valhalla/MOTIS against N2/N3 contracts; it creates no production adapter, pack manager, committed regional data or provider-owned domain model.
- **Prerequisites:** N1–N3 contracts, the accepted four-layer durability boundary, separately licensed OSM/boundary/GTFS inputs and isolated ignored staging.
- **Decision gates:** D01, D06–D09, D11, D12 and D14–D18.
- **Evidence/spike:** Build the buffered Gold Coast/common-snapshot union and SEQ GTFS separately; measure source/build size, build time, memory, cold start, latency, Windows operation, attribution, boundary/suburb behaviour, map/search accessibility and representative walk/cycle/drive/transit/profile/policy/failure cases.
- **Complete when:** Results are repeatable and comparable, unsupported mappings are explicit, licences/reacquisition/rollback are recorded, front-runner and challenger have reconsideration triggers, and any proposed choice fits the existing standard-library subprocess/loopback boundary.
- **Reorder if:** Display/search/pack and routing work are safer as parallel spikes, a candidate fails packaging early, or exploratory work starts sooner; early results remain non-authoritative until N1–N3 are complete.

#### N4. First installed-region Map slice

- **Outcome:** A user can inspect, install and use one verified Gold Coast capability pack for a normal local basemap/search and clickable provider context, then update/remove it without losing canonical data or the last-known-good pack.
- **Prerequisites:** N1/N2, the applicable X1 decision evidence, declarative manifests under ignored runtime storage and inspect/verify/stage/validate/atomic-activate/rollback lifecycle services.
- **Decision gates:** D01, D06–D08, D14, D16 and D18.
- **Evidence/spike:** Run the selected production approach through interrupted install/update, corrupt/incompatible/overlap, offline, boundary and constrained-resource cases before fixing archive shape, buffers, retention or budgets.
- **Complete when:** Local map/search works without WAN, capability/coverage/version/freshness/attribution remain visible, removal retains canonical Locations, failure keeps the last-known-good activation and route/feature coordinates can remain visible beyond basemap coverage.
- **Reorder if:** Pack activation and first visible/searchable use can only be safe together, the routing graph is the strongest lifecycle driver, or N5's review flow is small enough to join without turning this into a broad pack-platform project.

#### N5. Map 2.0B review, bookmarks and coverage

- **Outcome:** Provider features use the shared details flow with reviewed duplicate-aware **Save as Location**, portable external favourites/lists and contextual **Improve coverage** recommendations that retain the selected feature or route.
- **Prerequisites:** N1 provider-link/acceptance semantics, N2 sidebar/selection state, N4 source identity and coverage metadata, and measured boundary examples.
- **Decision gates:** Provider-reconciliation portions of D02–D05, D18 and remaining Map-state/list portions of D19.
- **Evidence/spike:** Test two provider versions, disappearance/refresh, shared-place grouping, list revisit/export/clear, duplicate review and selected pins/routes near a boundary, bordering suburb and adjoining LGA.
- **Complete when:** Browse remains non-mutating; promotion is explicitly reviewed; user list membership survives provider removal while provider facts become honestly unavailable; recommendations explain scope/size/network/source and never install automatically or lose context.
- **Reorder if:** Reviewed saving belongs with N4's first provider details, lists can follow independently, or coverage recommendations must wait for route-corridor measurements from N6/N7.

#### N6. Trustworthy walking journey

- **Outcome:** A walking journey between deliberate endpoints returns an explained textual itinerary and Map route overlay using the reviewed Regular/Fast/Run profile, supported policy controls and bounded cache, with honest alternatives and failures.
- **Prerequisites:** N1–N3, X1's selected routing evidence, N2 route-overlay seam and an activated compatible street source/build from N4 or an explicitly enabled equivalent capability.
- **Decision gates:** D09–D11, D15 and D17.
- **Evidence/spike:** Map the selected engine against representative internal/boundary, faster-walk, contiguous-limit, avoidance, stale-version and failure cases; measure cache size/latency/retention and collect repeated user measurements before fixing thresholds, preset values or applicability.
- **Complete when:** Route distance, estimated duration, elapsed time and buffers remain distinct; capability/policy/profile effects and source versions are explained; stale results cannot be materialised; cache invalidation is deterministic; and offline/refused-network behaviour is honest.
- **Reorder if:** A useful textual journey can precede its overlay, N5 can wait while routing proves the pack boundary, or walking and drive/cycle mappings are small enough to combine without obscuring transit or profile evidence.

#### N7. Static public-transport journey and transport Map

- **Outcome:** Static SEQ timetable planning adds arrive-by/depart-at multimodal Walk/Wait/Bus/Train/Tram/Ferry stages, alternatives and accessible Map/itinerary transport context without depending on live data.
- **Prerequisites:** N3's stage/error contract, X1 transit evidence, compatible timetable/street coverage and N2's layer/route presentation seam; N6 is needed only where it resolves a shared adapter/cache uncertainty.
- **Decision gates:** D09, D12 and D17, with applicable D11/D15 translation evidence.
- **Evidence/spike:** Prove station-complex/access-point, transfer, service-day/timezone, route-shape, stale/malformed GTFS, partial street coverage, no-connection and faster-walk alternative cases.
- **Complete when:** Scheduled/service/wait/walk meanings and provenance are stable, unsupported constraints are refused, partial coverage is labelled, essential text equals the Map, and static results stay useful with live capability absent.
- **Reorder if:** Transit and walking adapters can proceed in parallel after N3/X1, the transport layer follows a complete textual planner, or a common engine makes N6/N7 a smaller combined adapter slice.

#### N8. One-time Calendar materialisation and lifecycle

- **Outcome:** One confirmed result atomically creates a locked, ordered journey group of ordinary mode-Calendar Events with inherited reminders, durable minimum provenance and safe stage/group delete and replan scopes.
- **Prerequisites:** At least one trustworthy N6/N7 stage model, existing `commit=False` Calendar/Event services and reminder reconciliation, plus a provider-independent journey baseline that survives cache/provider removal.
- **Decision gates:** D13 and journey-group/baseline portions of D20; cache-to-materialisation boundary in D10.
- **Evidence/spike:** Prototype exact group/role schema and transaction boundary using walking-only, multimodal, unavailable/renamed Calendar, rollback, middle deletion, scoped replan, timezone and stale-cache cases.
- **Complete when:** One confirmation yields all-or-nothing Events/audit state; group membership alone locks generated fields; manual Events on the same Calendars remain editable; reminders inherit normally; buffers retain accepted semantics; and stale/cache loss cannot change the saved schedule.
- **Reorder if:** Walking-only materialisation is a safe first sub-slice, scoped lifecycle needs a second independently safe boundary, or drive/cycle breadth has higher value first; it never precedes a trustworthy result contract.

#### N9. Drive/cycle breadth and explained policy

- **Outcome:** Drive and Cycle complete the four primary modes with applicable durable profile variants and at least one structured, attributed routing policy whose applied/conflicting/unsatisfied effect is explained.
- **Prerequisites:** N3, X1, compatible street data/build and the proven adapter/explanation/cache seam from N6; Calendar materialisation is not a prerequisite.
- **Decision gates:** D09, D11, D15 and D17.
- **Evidence/spike:** Test engine capability mappings, vehicle/cycle constraints, hard/soft conflict precedence, evidence quality, boundary routes and unsupported accessibility/environmental claims before fixing provider mappings.
- **Complete when:** Walk/Cycle/Drive/Public transport identities remain stable across adapters, policies never become opaque provider flags, unsupported claims are absent or attributed, and all new results meet N6's provenance/failure/cache boundary.
- **Reorder if:** It can run beside N7/N8, one mode exposes a distinct data gate and should split, or N6 evidence shows the two mappings are a genuinely small extension.

### Later

#### L1. One-shot current location

- **Outcome:** A deliberate local preference and normal device permission provide one transient centring estimate, with last viewport then Gold Coast fallback and a separately enabled/disclosed IP option only when device location is unavailable.
- **Prerequisites:** N2 Map state/selection model, explicit provider enablement and a transient-context boundary that cannot become a journey origin or canonical record without deliberate user action.
- **Decision gates:** Current-location portions of D14 and D19.
- **Evidence/spike:** Exercise grant/deny/unavailable/stale permission, restart and offline flows in supported browsers; assess the IP provider separately for transmitted data, cost, terms and coarse accuracy.
- **Complete when:** No tracking/history is created, denial never blocks Map, startup priority is deterministic, the estimate is visually/textually distinct from a Location and clearing the preference/state removes it.
- **Reorder if:** Device-only centring is valuable after N2 and can ship without the IP option, or browser support forces both mechanisms later; it does not gate routing or pack work.

#### L2. Live transit enrichment and disruption handling

- **Outcome:** While Project E runs, attributed live delay status updates one deduplicated Inbox alert without retiming Events; only cancellation or a newly infeasible connection may atomically replace future grouped stages.
- **Prerequisites:** N7 static baseline, N8 durable group/locking/reminder semantics and the existing registered in-process scheduler/Inbox boundaries; N9 is not required.
- **Decision gates:** D21 and applicable operational-history portions of D20.
- **Evidence/spike:** Test changing delay, cancellation, platform/stop change, missed connection, stale/failing data, startup catch-up, elapsed stages, deletion and reminder reconciliation before selecting provider/poll windows.
- **Complete when:** Schedule and prediction remain distinct/auditable; one logical alert is updated rather than duplicated; ambiguous/no-route cases request attention; past stages are untouched; and polling stops with the running process/journey window.
- **Reorder if:** A suitable live source is unavailable or its terms fail, or static all-mode journeys/Map work have higher value; live status and mutation may split only if the first slice cannot mutate Calendar.

#### L3. Gated Map layers and spatial comparison

- **Outcome:** Satellite, terrain, traffic, transit/cycle overlays, nearby exploration and at least one useful matrix/reachability/comparison workflow arrive independently as their data gates prove value; unavailable layers stay visible with an explanation.
- **Prerequisites:** N2/N4 layer and coverage contracts plus trustworthy N6–N9 search/routing results for any comparison; no layer may become a core WAN dependency.
- **Decision gates:** Remaining D07, D08, D10, D14, D18 and D19 questions, with D09/D11/D15 for route-derived analysis.
- **Evidence/spike:** Evaluate each layer/provider separately for licence, privacy, cost, attribution, offline/stale behaviour and desktop performance; choose one concrete comparison workflow from measured user value rather than implementing a generic analysis platform.
- **Complete when:** Every delivered layer is independently toggleable/attributed/degradable, preferences remain local, nearby/comparison results retain source/coverage/freshness and typed failures, and at least one comparison outcome is useful and accessible in text and Map form.
- **Reorder if:** Any layer or comparison becomes valuable immediately after its prerequisite slice; split by capability, combine only when sources/lifecycles truly match, and place matrix/reachability before live enrichment if it offers more value.

Every production slice retains the repository's full test/compile requirement; schema work verifies fresh and representative upgrades, and UI work adds temporary-port smoke plus visual/keyboard review. Evidence spikes instead finish at reproducible measurements and an explicit decision/reconsideration record.

## Implementation decision gates

These grouped IDs preserve the earlier register while making the working set smaller. Resolving a gate does not itself authorise implementation.

| IDs | Decision/evidence state | Safe position already accepted |
| --- | --- | --- |
| D01, D06, D16, D18 | Pack archive/directory shape, boundary buffer, raw-input retention, prebuilt vs local build, suburb dependency closure, proximity/route-corridor recommendation metric, overlap and measured resource budgets. Prove with Gold Coast, selected pins/routes near boundaries, a bordering-suburb cut and Logan/Brisbane union. | Gold Coast first; portable source packs plus disposable derived builds; independent LGA/suburb units; route coordinates survive missing map coverage; contextual sidebar offers nearby suburb, LGA and online capability choices but never auto-installs or silently claims absent routing capability. |
| D02–D05 | **Resolved by N1.** The current-data audit, fictional address/station/building/provider-version spike and real upgrade fixture support the normalized assertion, compact coordinate JSON, single-active-parent and neutral provider-reference choices recorded above. Reconsideration triggers remain explicit. | One Location is one enduring place; addresses are purpose/status assertions; current and preferred differ; point/line/area may be multi-part and role-specific in WGS84; confidence/provenance attach to geometry; child Locations and provider acceptance are explicit and never auto-created. |
| D07, D08, D14 | Renderer/local tile/search choices; normal/satellite/terrain sources; traffic/transit/cycle/place overlays; ranking and viewport-loading details; one-shot device/IP-geolocation implementation and consent; online connection packaging; licence/cost/privacy and constrained-desktop performance. | Build incrementally; search results never rerun on pan while enabled layers load visible features; persistent accessible red selection pin/sidebar; blank clicks do not pin; clickable provider features never mutate; current location is a Phase 3 deliverable with device-first one-shot use and optional disclosed IP fallback; no tracking or hidden query logging. |
| D19 | Recent-search/selection retention, last viewport/layer state, sidebar navigation, named-list/favourite schema, provider-reference reconciliation and portability. Needs external bookmark disappearance/refresh, shared-place grouping, list revisit and clear/export workflows. | Normal base, canonical Locations and available general-place/transit features begin visible; other canonical/specialist layers begin off and choices persist locally. Recents are bounded and clearable; external bookmarks need no canonical promotion; user membership is portable while provider facts are reacquired; no reusable saved journey. |
| D09, D12, D17 | **D09 contract foundation resolved by N3.** Final engine and capability mappings, transit source/update workflow, station-complex semantics and native/Java acquisition/process/upgrades still need Gold Coast/SEQ comparison and repeatable Windows setup. | Adapters declare capability and return normalised stages, distance/time meanings, provenance and typed failures; Valhalla is first spike and MOTIS challenger, not a production choice; static timetable remains default. |
| D10, D20 | **Cache contract foundation resolved by N3.** Exact cache store/retention/eviction thresholds, journey-group/baseline schema, operational-history retention and cross-timezone handling still need measured invalidation, one-time save, scoped lifecycle and cancellation replacement cases. | Personal data is durable; packs replaceable; builds/caches disposable. Cache returns fresh/stale/miss using full dependency fingerprints, creates no route history and cannot silently materialise stale results; confirmed journeys retain their minimum baseline independently. |
| D11, D15 | **Identity and refusal foundation resolved by N3.** Measured preset values/aggregation, Sprint and distance applicability, specialized profile/policy schema, adapter translation and accessibility/environmental evidence still need user measurements, real engine controls and worked conflicts. | Stable Walk/Cycle/Drive/Public transport modes normalise to mode-specific stages; pace variants remain Walk profiles; journey enable/disable selects the active policies, then remaining hard, specific, soft and provider-default rules apply in order; conflicts are surfaced; no silent learning or unsupported claims. |
| D13 | Exact group persistence, Calendar-role repair, initial colours/reminder timings, stage titles and scope mechanics. Needs multi-stage, unavailable-Calendar, deletion/replan and rollback cases. | Auto-provision editable Walk/Bus/Train/Tram/Ferry/Cycle/Drive/Wait Calendars; every generated stage inherits Calendar reminders; group membership alone locks fields; buffer becomes earlier movement/Wait, not an Event. |
| D21 | Live provider, enable inheritance, in-process polling/window, delay-alert identity/status persistence and disruption semantics. Needs changing delay, cancellation, platform/stop change, missed connection, stale data, startup and deletion cases. | Run only while Project E runs; any delay produces one updated local alert/status without retiming; mutate future stages only for cancellation/missed connection; reconcile reminders; ignore past stages; never infer location, boarding or arrival. |

When resolving a gate: state the workflow/IDs, inspect current code/data, collect representative evidence, compare doing less, spike the riskiest assumption, choose the narrowest reversible option and record rationale, migration, verification and reconsideration trigger. Ask before changing accepted product direction; if evidence is insufficient, keep the safe position or narrow the slice.

## Explicit exclusions

Phase 3 does not include global offline completeness, commercial-map parity, turn-by-turn navigation, continuous/personal location tracking, mobile access, a background journey worker while Project E is closed, reusable/recurring journeys, opaque AI-selected routing, silent behavioural learning, unreviewed automatic canonical Location/child creation, realtime data as a core/offline dependency, external push/OS notifications, public reviews, safety guarantees, arbitrary executable packs or automatic mutation outside the accepted cancellation/missed-connection journey contract.

## Completion and expansion workspace

Phase 3 is complete only when durable Location/address/geometry/child semantics and provider-independent route/cache boundaries survive provider replacement; one useful installed region supports a map-dominant, searchable and accessible place workspace with canonical/provider distinction, clickable inspection, reviewed saving, intentional layers and one-shot current-location centring; all four intended journey modes, explained profiles/policy and at least one useful matrix/reachability/comparison workflow work from those spatial contracts; one-time grouped Calendar materialisation behaves safely; optional live enrichment follows its alert/mutation boundary; pack failure/partial coverage remains understandable; and user-owned map/spatial/journey state is recoverable independently of packs/caches.

Add dated numbered **Complete:** entries here only after explicitly authorised implementation is delivered and verified. Each entry should name the slice, resolved decision IDs and durable contract.

1. **Complete: N1 · Canonical place and endpoint foundation (2026-08-05).** Resolved D02–D05 with normalized physical/postal/delivery address assertions; validated role-based WGS84 Point/LineString/MultiLineString/Polygon/MultiPolygon geometry assertions; assertion-level confidence, accuracy and source snapshots; removable neutral provider references; and single-active-parent, cycle-safe `contains_location` Relationships. Migration `20260805_33_canonical_place_foundation` preserves valid flattened address/point values and provenance while refusing silent coordinate loss. Current forms, Location detail and Map deterministically project the preferred current physical address/representative point, retaining replacements as history and inheriting parent address for display only. Fresh-schema, representative-upgrade, behavioral, portability and full-suite tests, compilation and a temporary-port create/detail/Map smoke passed. No N2 renderer, pack, search, routing or provider architecture was selected.
2. **Complete: N2 · Map 2.0A canonical workspace (2026-08-05).** Resolved D07/D08/D14 and the Map-state subset of D19 with a map-dominant, browser-native canonical coordinate canvas; stable canonical-first name/address/coordinate and explicitly requested current-provider search; one-pin shared-place grouping; persistent accessible selection, results/details/back and complete text equivalent; deterministic local layer controls; failure-tolerant local viewport/layer/sidebar state; and a bounded local viewport endpoint with stale-request abort/discard. Automatic Leaflet CDN and OSM tile dependence is removed; unavailable map/provider layers remain explained, and Nominatim is off by default, query-only, attributed, replaceable and honestly degradable. Dense fictional, behavioral, accessibility, degraded-network, HTTP/state/regression, full-suite/compile and temporary-port Edge wide/constrained/keyboard/visual checks passed. No N3 work, pack/tile/search/routing architecture, current-location workflow or later provider choice was begun.
3. **Complete: N3 · Provider-independent journey contract (2026-08-05).** Resolved the foundation portions of D09–D11/D15 with deliberate canonical Location/access-point resolution; strict versioned capability declarations; provider-independent request, normalized stage/result, distance/time, provenance/explanation and typed failure contracts; audited durable user-owned mobility-profile/routing-policy identity; full semantic dependency fingerprints; and a bounded clearable fresh/stale/miss cache outside personal data. Deterministic fictional adapters proved ambiguity, unsupported requirements, partial coverage, no-route/provider-failure separation, contiguous profile limits, policy conflict/no-compliant-route, cache corruption and provider replacement while every requested profile/policy remains explicit. Migration, recovery, focused regression and 325-test full-suite checks passed. No engine/provider/pack was selected or integrated, no X1/N4 work began and no Calendar Event or journey group is created.
