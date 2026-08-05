# Phase 3 Planning Workspace: Spatial Intelligence

## Status, purpose and authority

**Phase 3 is planning only.** This document records the desired outcome, accepted boundaries, candidate capabilities and decisions that must be made through later authorised implementation work. It is not implementation authority, a fixed release checklist or a claim that the described capabilities exist.

The phase can be understood as the next layer of the same platform:

```text
Phase 1 — What exists
Phase 2 — When it matters
Phase 3 — Where it is and how to reach it
```

Phase 3 aims to make place, geometry, distance, movement, travel time and reachability useful across Project E without turning maps, providers or routing datasets into competing personal truth. The target is a private spatial layer for Project E's own Locations, Relationships, Events and decisions—not general mapping-product parity.

The first intended end-to-end outcome is a journey planner that can calculate a trip, expose each stage and its assumptions, preview the resulting Calendar mutations and—after one explicit confirmation—create separate Calendar Events for the stages. A commute is a representative workflow. Walking, driving, cycling and public transport are all intended modes; delivery order remains evidence-led.

The document uses four planning states:

| State | Meaning |
| --- | --- |
| **Accepted direction** | A durable product or authority boundary that later work should preserve unless the user explicitly changes direction. |
| **Candidate** | A potentially valuable outcome whose scope and priority remain subject to explicit implementation authorisation and evidence from use. |
| **Deferred decision** | An intentionally unresolved choice that needs a concrete workflow, representative data, a feasibility spike or other implementation evidence. It is not permission to guess. |
| **Complete** | Delivered and verified work recorded in the expansion workspace after an explicit implementation prompt. |

A deferral is a decision about *when and how to decide*, not an omitted design. An authorised workstream should resolve only the decisions needed for its coherent slice. Material product changes or long-term conventions still require user direction; ordinary reversible engineering choices may be settled from evidence and recorded with their rationale.

## Current platform foundation

Project E currently has:

- canonical Location entities with address fields, optional latitude/longitude, a source field and notes;
- ordinary Relationships connecting Locations to other canonical records, including `event_at_location` for Events;
- a derived Map view with Location, Organisation, Person and Asset markers;
- optional OpenStreetMap tiles and Nominatim address lookup, with manual entry and textual/offline fallback;
- canonical Events, Calendar, reminders, Inbox and deterministic scheduling services that could consume deliberately defined spatial results.

It does **not** currently have rich geometry, Location hierarchy, access points, regional packs, offline spatial search, routing networks, transit data, mobility profiles, routing policies, journeys, matrices or reachability. Projects, Documents and Events are not current Map layers. Planning language below must not be read as current architecture or silently added to current reference documentation.

## Accepted direction

### One personal truth, many spatial projections

- A Location is a personally meaningful canonical place, address or area worth storing, relating and recovering. Most map features, roads, stops and addresses are not canonical Locations.
- Browsing, searching, routing or encountering a provider feature never creates a Location automatically. **Save as Location** must be a reviewed canonical-creation workflow with likely-duplicate handling.
- People, Organisations, Events, Projects and Documents gain spatial context through Relationships to Locations rather than duplicate address or geometry fields. Existing direct Asset coordinates remain a valid current fact and require deliberate migration analysis if a later model changes them.
- A map, route, matrix, reachable area or nearby result is a projection over sources. It does not become canonical because it is useful or displayed often.
- Provider updates may improve or challenge spatial context but never overwrite user-owned identity, notes, geometry, Relationships, policy or decisions without review.

### Local-first with explicit replaceable enrichment

- Canonical records and manually entered spatial facts remain usable with no WAN connection and no installed regional pack.
- Rich local capability should be possible inside deliberately installed regions. Optional online lookup, tiles, routing or live data must remain replaceable and local in effect when unavailable.
- Basemap, address, road, elevation, routing and timetable datasets stay outside the main entity database as provider-owned indexes or replaceable regional packs.
- Public-transport planning uses the applicable installed static timetable by default. When an installed/enabled provider also supplies current live service data, Project E uses it automatically for affected planning and materialised journeys; absent, stale or failed live data falls back visibly to the scheduled timetable rather than disabling the journey.
- Transit timetable/shape coverage and visual map coverage are independent. A service that crosses an uninstalled map area remains drawn from its available coordinates over a blank background; enabled online tiles may fill that background. The interface identifies the missing capability and offers the adjoining LGA pack or a smaller bordering-suburb pack. Missing street/path coverage may still limit access-leg routing and must be reported rather than disguised as visual-only absence.
- Regional packs are installed runtime data under ignored local storage, never committed source-repository content. They should be independently installable at a useful small-area granularity where source data and routing correctness permit it.
- An optional online spatial capability may be absent/disabled by default. Deliberately installing or enabling it can grant durable consent for automatic out-of-coverage fallback; each result must still identify the online provider and disclosed/fallback state without requiring a button on every request.
- A data pack contains declarative data and metadata, not arbitrary executable code. Any parser, adapter or local engine is reviewed application/runtime code with an explicit dependency decision.
- Project E owns provider-independent requests, result meaning, policy, provenance, cache identity, explanations, degraded states and user experience. A provider or engine supplies bounded capabilities; it does not define personal truth or silently choose product behaviour.

### Deliberate authority and understandable consequences

- Drawing or selecting geometry first creates draft interaction state. The user must choose whether it describes a Location, an informational overlay or an active routing policy.
- Temporary map points, route endpoints and one-time access choices remain transient unless explicitly promoted.
- Spatial calculation may create or refresh derived cache state but remains read-only over canonical records. The accepted **Add journey to Calendar** workflow is a separate reviewed mutation: one confirmation may atomically create the fully previewed set of stage Events. Ordinary recalculation or static timetable refresh never silently edits those Events.
- Materialised journey-stage Events are planner-managed. Nothing on them is directly editable in the ordinary Event form; the user may delete with a journey scope or return to the planner for a reviewed replan. Calculated start/end/timezone, routing/service fields and presentation remain under planner ownership.
- An installed/enabled live-service provider authorises bounded deterministic monitoring while Project E is running. Every detected delay updates attributed status and creates or refreshes one deduplicated local alert, but timetable start/end values remain the Calendar schedule. Only a cancellation or a connection made infeasible by delay may atomically replace future planner-managed stages and reconcile their reminders. It does not authorise destination changes, edits to elapsed stages, mutation of manually created Events or location tracking.
- Ambiguous endpoints, multiple Event venues, missing access points or incompatible constraints ask for a decision or report no result; they are not silently guessed away.
- The same validated spatial query boundary should eventually support human views and any separately authorised deterministic or bounded AI consumer. No consumer receives a privileged mutation path.

### Honest evidence, time and safety

- User assertions, provider facts, generic estimates, user-configured values, observed values, accepted calibration and manual overrides remain distinguishable.
- Spatial facts and results identify source, relevant dataset/provider version, calculation time and observation/effective time where those affect meaning.
- Results distinguish straight-line distance, network distance, scheduled travel time, estimated duration, buffers and uncertainty rather than collapsing them into one authoritative number.
- Accessibility, lighting, traffic, environmental conditions and perceived safety are incomplete, contextual and time-sensitive. Project E may expose attributed evidence and personal preferences but never promise a route is safe or accessible.
- Visual maps retain a meaningful textual alternative, keyboard-reachable controls, labelled/non-colour distinctions and honest loading, empty, stale, partial and unavailable states under the existing design contracts.

## Planned information boundaries

These classifications guide later modelling without preselecting table shapes.

| Concept | Intended meaning and lifecycle |
| --- | --- |
| Canonical Location | User-owned identity for a meaningful place; editable, auditable, exportable and recoverable even without geometry. |
| Place geometry | User-owned or explicitly accepted spatial description of a Location, with role and provenance. Its exact storage model is deferred. |
| Access point | A named or typed way to approach a Location. It may remain a Location component/provider feature or become its own Location when independently meaningful. |
| Location hierarchy | Personally meaningful containment or part-of meaning between Locations. Provider administrative hierarchy remains external context unless deliberately asserted. |
| Provider feature link | Durable reference from a Location or spatial component to an external feature, including provider namespace and reconciliation context. It is not ownership of the provider feature. |
| Interest overlay | Durable user-owned spatial configuration for exploration or comparison, not necessarily a canonical entity and never routing-active by implication. |
| Mobility profile | Inspectable configuration describing how the user intends a calculation to estimate movement and buffers. It is not a silent medical or behavioural profile. |
| Routing policy | Inspectable configuration that constrains or prefers routes for stated modes, directions, times or contexts. |
| Regional pack | Replaceable, verifiable external spatial data plus a manifest; reacquirable unless licensing or local derivation requires deliberate backup treatment. |
| Journey request/result | A versioned calculation and explanation. An unsaved result is derived/transient or cached; saving means one-time Calendar materialisation for the selected date/time, not a reusable or recurring journey template. |
| Calendar journey materialisation | One user-confirmed ordered group of separate canonical Events representing the journey's stages. All fields on generated stages are planner-owned; change occurs through scoped replan, scoped delete or provider-enabled live-service updates, never ordinary Event editing. The grouping mechanism is deferred. |
| Matrix/reachability/comparison | Scenario-bound derived decision output, reproducible where source versions remain available and visibly stale otherwise. |

### Location identity, address and geometry

A Location may be useful with only a name, only an address, only a point, an area, or no spatial enrichment yet. Address, identity and geometry are related but not interchangeable:

- a postal address can refer to a site containing several meaningful destinations;
- one meaningful Location can have several entrances or routing anchors;
- a boundary can describe an area while a representative point supports display;
- a provider label or feature is evidence/context, not the canonical display identity;
- reverse geocoding a point produces a proposal, not a user-owned address fact.

Geometry must carry a purpose such as representative point, boundary, entrance, route anchor, informational overlay, avoidance area or preferred corridor. A derived centroid or snapped network point must remain distinguishable from accepted place geometry. Coordinate reference system, axis order, precision and units must be explicit at service/storage boundaries even though their exact representation is deferred.

An access point should become a separate canonical Location only when independent naming, notes, Relationships, reuse, comparison or lifecycle justify that identity. Otherwise it should remain a structured component of its parent Location or an external feature selected for one journey. The first real station/building workflows must test this rule before schema is fixed.

Location-to-Location hierarchy will need explicit semantics rather than coordinate containment alone. A campus may contain a building and a station complex may contain an entrance, but provider containment must not silently create canonical parent Locations or Relationships. Whether hierarchy uses ordinary Relationship types, structured Location components or both is deferred to the first hierarchy workflow.

### Provider references and reconciliation

A durable provider reference should be namespaced and retain enough type, identifier and dataset/version context to re-check it. A label or coordinate alone is not a stable link. On refresh:

- an exact continuing feature can refresh external context without changing user facts;
- a moved, split, merged, retired or missing feature produces reviewable status rather than automatic relinking;
- fuzzy spatial/name matching may suggest a replacement but never asserts one;
- one Location may reference several providers when they describe different aspects of the same place;
- provider identifiers must never be exposed as Project E entity identity.

The reconciliation state model, matching thresholds and treatment of provider history need representative pack upgrades before they can be designed responsibly.

## Regional data and provider boundary

### Capability separation

Basemap rendering, place/address search, reverse geocoding, feature lookup, geometry operations, road/path routing, timetable routing, elevation and live enrichment are separate capabilities. One engine, provider or format need not own all of them.

Every capability invocation should expose a common envelope:

- requested capability and provider/engine selected;
- local, network or unavailable execution;
- input scope and normalised assumptions;
- coverage and data/version identity;
- result provenance, warnings, partiality and calculation time;
- whether fallback is possible and whether fallback would disclose data externally.

Provider selection and fallback must be deterministic and inspectable. Network fallback is permitted automatically only when the relevant optional online capability has been deliberately installed/enabled; otherwise local failure remains local. The result must make the provider transition visible. A visual tile request can reveal viewport interest just as a geocoder or router can reveal a query; privacy treatment must cover all network spatial resources, not only route endpoints.

### Minimum regional-pack contract

Before the first production pack, its manifest and lifecycle must account for:

- stable pack identity, format version and compatible adapter/application versions;
- declared geographic coverage and available capabilities;
- component/source versions, build time and effective dates;
- size, checksums and integrity validation;
- licensing, redistribution status, required attribution and source notices;
- acquisition/reacquisition information without embedding credentials;
- staged installation, validation, activation, rollback and interrupted-update recovery;
- separately installable units, declared dependencies and optional user-facing bundles;
- overlap/conflict behaviour when several packs cover a request;
- health, staleness, removal and dependent-cache invalidation;
- export/backup classification and storage cleanup.

Installation should follow inspect/consent, acquire, verify, stage, validate and atomically activate. A failed update leaves the last-known-good pack usable. Removing or replacing a pack cannot delete canonical Locations or user-owned geometry; affected provider context and calculations become unavailable or stale with a clear repair path.

Pack construction and distribution must use only data whose licence and attribution obligations Project E can actually satisfy. The first pack should prove the contract for one useful region and capability rather than invent a universal packaging system in advance.

Brisbane and Gold Coast are the first user-priority areas. LGA-sized install units are the preferred complete-area experience, but administrative boundaries cannot be assumed to equal route coverage. A local Brisbane–Gold Coast journey also needs the intervening corridor, including Logan; the manager should be able to install required adjoining units or a Brisbane–Gold Coast corridor bundle while retaining independent pack identity. When only a route edge crosses a boundary, the user should also be offered a smaller pack covering the relevant bordering suburb or suburb group instead of being forced to install the entire adjoining LGA. Exact subdivision boundaries, dependency closure and whether these smaller units are downloaded prebuilt or generated from a common source remain feasibility decisions.

Different components may need different extents. An OSM-derived street/path or basemap pack can be clipped into small areas, while a public-transport timetable may cover a wider service network and should not be duplicated into every LGA pack merely for visual symmetry. A timetable route/shape may therefore extend beyond installed map coverage: its coordinates and stops remain visible over blank space, with a clear partial-coverage explanation and install action. Online map resources fill that visual context only when the optional provider is enabled. Coordinate display does not claim missing street/path routing or feature-search capability.

Pack and online-provider management should feel plugin-like—discoverable, separately installable/enabled, updateable and removable—without making ordinary data packs executable extensions. Whether the optional online capability uses a built-in adapter, the application's future plugin mechanism or another reviewed boundary is deferred to dependency/security feasibility work. Its absence must leave the local platform coherent.

### Pre-implementation pack research and recommendation

**Research recommendation, not an implementation selection.** The most promising pack architecture separates portable/versioned inputs from engine-specific derived indexes. This keeps user-managed LGA packs independently meaningful while allowing the active routing graph to be rebuilt from the union of installed coverage rather than attempting to stitch incompatible prebuilt graphs at route time.

The recommended logical layers are:

1. **Source/capability packs:** immutable provider data, coverage, licensing and manifest metadata that can be installed independently.
2. **Derived capability builds:** disposable map/search/routing indexes fingerprinted from the exact source-pack set, engine/adapter version and build policy.
3. **Personal spatial data:** canonical Locations, accepted geometry, profiles, policies and materialised journeys in Project E's ordinary protected storage; never inside either external layer.

A Project E pack should be an installed directory with a small `manifest.json`, not one proprietary mega-database. Download transport may later use an archive, but activation should expose independently verifiable component files. The manifest should identify pack/version, coverage and boundary source, provider snapshot/effective time, capabilities, component paths/checksums/sizes, licences/attribution, dependencies, compatible adapter/build versions and reacquisition information.

| Component role | Provisional format | Reasoning |
| --- | --- | --- |
| Coverage/boundary | GeoPackage or build-time GeoJSON | Queensland publishes current official LGA boundaries in GeoPackage and other open formats. Preserve boundary source/version; normalise a routing copy to the engine's required CRS. |
| Street/path source | `.osm.pbf` | Compact standard OSM input accepted by the leading routing candidates. LGA extracts can be produced from a common snapshot with a simplified buffered polygon. |
| Transit schedule | Original GTFS Schedule `.zip` | GTFS is already a ZIP of defined text tables. Translink publishes one South East Queensland feed covering urban bus, rail, light rail and ferry, so this should be a separate SEQ transit pack rather than copied into each LGA. |
| Offline basemap | PMTiles v3 candidate | A single-file tile archive with a public specification and demonstrated MapLibre integration; attractive for installation, integrity and removal. Renderer/accessibility feasibility remains D07. |
| Local feature/search index | Derived SQLite/GeoPackage candidate | Fits the current SQLite boundary and can combine structured provider features, full-text search and spatial lookup without entering the canonical entity database. Exact schema/index support remains D03/D08. |
| Routing graph | Engine-native derived cache | Graph formats are engine/version/build-policy specific. Rebuild from installed source packs; do not make an engine graph the portable pack contract or sole recoverable input. |
| Notices | Plain licence/attribution files plus manifest entries | Keeps source obligations inspectable and export/reacquisition behaviour honest. |

The proposed Gold Coast-first build path is:

1. acquire and version the official Queensland Gold Coast LGA boundary;
2. transform it to the routing CRS, simplify only within an explicit tolerance and add a measured boundary buffer;
3. extract Gold Coast OSM data from one common Queensland/Australia snapshot using the buffered polygon—`osmium extract` supports polygon/GeoJSON inputs and explicitly recommends a small buffer when boundary completeness matters;
4. validate references, coverage and licence/attribution, then write the Gold Coast source-pack manifest;
5. install the Translink SEQ GTFS feed as a separate schedule pack and validate feed dates before activation;
6. build an engine-native graph from the union of installed OSM packs plus applicable schedule packs, using content/version fingerprints for cache identity;
7. optionally build PMTiles and a local feature/search index from the same source snapshot;
8. smoke-test routes inside the LGA and across buffered edges, then atomically activate the pack/build while retaining last-known-good state.

Later Logan and Brisbane installs should repeat the same source-snapshot contract. Activating a new combination rebuilds or acquires one compatible derived graph for the union; it does not assume separately built LGA graphs can be overlaid safely. A user-facing Brisbane–Gold Coast bundle can therefore declare Gold Coast, Logan/intervening coverage, Brisbane and the SEQ transit feed as dependencies while each remains independently installable/removable.

This recommendation is based on the [Queensland LGA boundary dataset](https://www.data.qld.gov.au/dataset/local-government-area-boundaries-queensland), the [official Translink SEQ GTFS dataset](https://www.data.qld.gov.au/dataset/general-transit-feed-specification-gtfs-translink), the [GTFS specification overview](https://gtfs.org/documentation/overview/), [Osmium extract documentation](https://docs.osmcode.org/osmium/latest/osmium-extract.html), the [PMTiles v3 specification](https://github.com/protomaps/PMTiles/blob/master/spec/v3/spec.md), the [MapLibre PMTiles example](https://maplibre.org/maplibre-gl-js/docs/examples/pmtiles/) and the [OGC GeoPackage standard](https://www.ogc.org/standards/geopackage/). The exact installed directory/archive shape, buffer distance, whether reacquirable raw inputs remain after a successful build and whether any prebuilt derived asset is distributed remain D06/D17 decisions to measure rather than settle abstractly.

### Routing-engine research and recommendation

Project E should build the provider-independent journey request/result adapter, profile/policy translation, stage normalisation, Calendar materialisation, provenance, pack lifecycle and review workflows. It should **not** initially build its own OSM parser, street graph, turn-restriction logic, shortest-path algorithms or timetable router.

| Engine | Fit for Project E | Main concern | Planning position |
| --- | --- | --- | --- |
| [Valhalla](https://valhalla.github.io/valhalla/api/) | OSM plus user-supplied GTFS; car, bicycle, pedestrian and multimodal transit; arrive-by, per-request `walking_speed`, matrices, isochrones, regional tiled graphs and a JSON HTTP API. Native tools can run locally and offer a one-shot mode where a server is undesirable. | Graph/transit build and Windows packaging complexity; personal polygon/cost policy and exact GTFS stage semantics still require representative tests. | **Front-runner for the first Gold Coast/SEQ spike.** Its documented walking-speed control directly matches recorded pace presets. |
| [MOTIS](https://github.com/motis-project/motis) | One OSM PBF plus multiple GTFS feeds; walking, cycling, car and public transport; geocoding, reverse geocoding, tiles, OpenAPI and published Windows binaries in one MIT-licensed runtime. | Younger/smaller ecosystem; one-PBF import means Project E must produce the installed-pack union first; exact pace, avoidance-policy and Calendar-stage detail need testing. | **Primary challenger.** Spike if Valhalla's transit import, stages, policy controls or packaging disappoint. |
| [GraphHopper](https://github.com/graphhopper/graphhopper) | OSM road modes, time-dependent GTFS routing, Windows support, custom models/areas, isochrones and a local HTTP service. | Java runtime and engine-native graph cache; interaction between per-request personal models and transit needs proof. | Credible fallback/comparator, not the first spike unless its custom-model fit proves materially better. |
| [OpenTripPlanner](https://docs.opentripplanner.org/en/latest/) | Mature OSM+GTFS/NeTEx transit planning with walk speed, transfer slack, arrive-by and detailed itinerary filtering. | Larger Java service and configuration/API surface; mapping/geocoding remain separate; general road routing is less aligned with Project E's single-engine preference. | Transit-correctness benchmark if Valhalla/MOTIS produce weak connection or station results. |
| [OSRM](https://github.com/Project-OSRM/osrm-backend) | Fast mature OSM route/table service with car, bicycle and foot profiles. | No integrated GTFS/public-transit planner; profiles are largely preprocessing-time and separate mode graphs increase orchestration/storage. | Do not use as the primary Phase 3 engine; it would force a second transit engine too early. |
| Custom Project E router | Total semantic control. | Re-implements complex parsing, restrictions, network algorithms, timetable search, updates and safety/correctness maintenance with little personal-platform value. | Reject for initial work. Consider only a bounded engine extension/fork after measured failures of suitable open-source engines. |

The engine spike should use one fixed Gold Coast OSM extract and the same current Translink SEQ GTFS feed, then run the same fictional/representative cases through Valhalla first and MOTIS when needed:

- direct walk, drive and cycle routes;
- arrive-by public-transport routes with initial/final walking legs;
- rail, light-rail, bus and transfer cases;
- a connection missed at Regular walk but caught at Fast walk/jog;
- a walking preset rejected because the leg exceeds its configured range;
- a cross-boundary route near Gold Coast pack coverage;
- an avoidance area, stairs/surface preference and no-satisfying-route case;
- route, matrix and reachability outputs with version/provenance detail.

Record graph-build time, installed/source/derived size, peak memory, cold start, ordinary route latency, Windows/local-process packaging, leg/service identifiers, transfer semantics, walking-speed effects, policy support, malformed/stale-feed behaviour and result reproducibility. The selected engine remains behind a standard-library Python adapter using a controlled subprocess or loopback service. Engine-native files remain disposable. A custom Project E routing algorithm is justified only if this evidence shows a bounded requirement cannot be expressed through, wrapped around or contributed to the shortlisted engines.

## Candidate experience and capability envelope

### Location spatial views

A Location Overview should remain concise: identity, address/geometry summary, important provenance or quality warnings and links into focused spatial views. Candidate specialised context includes boundaries, access points, parent/contained Locations, related records, nearby canonical Locations, transport features, travel-time summaries and data coverage.

Opening hours, parking instructions or accessibility notes require their own ownership and freshness semantics before becoming structured fields. Until a workflow demonstrates those semantics, ordinary notes or external provider context are safer than premature schema.

### Map 2.0

Map 2.0 remains a projection over canonical records, Relationships, installed data and explicit overlays. Candidate behaviour includes:

- search scopes that clearly distinguish canonical records, installed provider data and optional online results;
- selection and inspection without mutation;
- reviewed **Save as Location** from a provider feature, coordinate or drawn area;
- points, lines and areas with purpose-specific styling and textual equivalents;
- canonical layers and Relationship-projected Event, Project, Document, Person, Organisation and Asset context;
- understandable handling of a record related to zero, one or several Locations;
- routes, access points, overlays, policy geometry, reachable areas and quality findings;
- preserved context when moving between Map and canonical pages;
- useful canonical-coordinate and textual operation without tiles or network access.

Map viewport, layer and selection state should be transient by default. A durable overlay or reusable saved view requires an explicit save action and lifecycle; the exact saved-view model is deferred until repeated use demonstrates what should persist.

### Journey planning contract

A journey request should be provider-independent and make its assumptions visible. Candidate inputs include:

- origin, destination and optional intermediate points, each resolved from a Location, access point or deliberate temporary point;
- walking, driving, cycling, public transport or a permitted multimodal combination;
- depart-at, arrive-by or untimed planning intent;
- chosen mobility profile—including an explicit walking pace preset—and routing policies;
- preparation, parking, access, transfer and desired-early-arrival buffer values that move applicable active stages earlier without inflating their duration or becoming artificial Calendar blocks;
- accessibility/infrastructure constraints and preference strength;
- requested alternatives and scenario time.

A useful result should contain more than a polyline and one duration:

- the resolved endpoints/access points and any network snapping;
- one or more alternatives with legs, modes, distance, scheduled/estimated duration, waits and transfers as applicable;
- stage boundaries suitable for Calendar preview, such as walk, vehicle/service, wait/transfer and final access legs;
- each named buffer assumption, the slack it creates and the resulting departure/arrival milestones;
- applied, ignored, conflicting or unsatisfied policies;
- source/engine and dataset/timetable versions;
- calculation time, coverage, freshness, uncertainty and warnings;
- a textual itinerary or summary equivalent to the essential visual result;
- a stable result fingerprint suitable for cache identity and later comparison.

For Event planning, time components should remain legible. A buffer changes the calculation anchor; it is not added to the duration of the movement stage:

```text
Event start
  minus desired early-arrival buffer
= arrival target
  minus route duration (including modelled route waits/transfers)
= leave-by time
  minus preparation buffer
= begin-preparing time
```

Parking or an access walk belongs either in route legs or an explicitly named calculation allowance, never both. Public-transport schedule time, generic movement estimates and personal buffer values must not be presented as one equally certain number.

Routes, matrices and reachability calculations are derived. Cache reuse requires equivalent normalised inputs and source versions; a visually similar request is not enough. The accepted Calendar action may deliberately materialise one result as separate stage Events; saving a reusable journey/template or retaining route history remains deferred until repeated commute use proves the required identity, privacy and lifecycle.

### Mobility profiles and routing policies

A mobility profile is user-configured calculation input. Walking begins with named presets for **Regular walk**, **Fast walk/jog** and **Run** rather than a newly inferred speed for every route. A later **Sprint** preset may apply only below a configured distance. The exact values will be deliberately measured by the user during implementation rather than guessed from generic defaults.

Each preset should retain stable identity, canonical speed/unit, source (`manual`, `measured` or later explicitly accepted calibration), measurement/effective date and an applicability boundary such as maximum continuous distance or duration. A minimal accepted measurement may record test distance, elapsed time and derived speed without retaining a GPS trace. Several observations may support one reviewed value, but Project E never recalculates it silently. Whether distance limits apply per contiguous leg, cumulatively across a journey or through a fatigue model must be tested rather than hidden in the first schema.

A practical implementation-time calibration should use a known measured distance, several separately recorded attempts and notes for material conditions such as gradient, stops, surface and whether the result felt sustainable. Project E can calculate candidate speeds and a median/representative value, but the user chooses the accepted preset. The provisional first rule is to apply a maximum to each contiguous walking/running leg and separately warn when the journey's cumulative effort is unusually high; a cumulative fatigue model should not be invented without observed need.

Regular walk is the default. If an arrive-by route or public-transport connection is infeasible at that pace but feasible under a faster existing preset, the planner may calculate and present the faster alternative with a prominent warning and the required assumption. It never silently selects that pace or invents an arbitrary speed. User confirmation selects the alternative, and any created Calendar stage Events retain the chosen pace/provenance so the plan can later be understood or reviewed.

Other candidate profile values include comfortable distance, cycling pace, transfer or parking allowance, slope/stair/accessibility limits and accepted calibrations. Running/sprinting may need route-suitability rules for surface, stairs, gradient and crossings rather than only dividing distance by a higher speed. Values need units, source, effective period and override semantics. No observation changes a profile until the user reviews and accepts it; continuous movement history is not implied.

A routing policy is a structured, inspectable rule. It may express hard exclusion, soft avoidance, preference or an added cost/buffer and may be scoped by mode, direction, time, effective period or scenario. Candidate geometry includes an area, radius, segment, crossing, transfer point or preferred corridor.

The result must explain which policy affected it and when no route satisfies hard constraints. Deterministic precedence and conflict rules are required before policies can be trusted, but their exact algebra should be designed against a real engine and examples rather than abstractly. Labels such as “safer,” “accessible” or “well lit” must be replaced by specific personal preference or attributed dataset claims.

### Journey and Calendar integration

An Event continues to relate to ordinary Locations through Relationships. It does not gain routing-specific address or geometry columns. The core workflow may start from an existing Event destination or as a standalone journey/commute, then:

- calculate one or more journey alternatives with explicit pace/profile assumptions;
- ask which venue/access point applies when Relationships are ambiguous;
- calculate arrival target, leave-by and begin-preparing milestones where relevant;
- preview every proposed Calendar Event, time boundary, title, mode/service and source journey before mutation;
- atomically create a separate canonical Event for each selected stage after one explicit **Add journey to Calendar** confirmation;
- preserve a group identity so the journey can be opened, reviewed, replanned or removed coherently without erasing each Event's ordinary lifecycle;
- show conflicts or stale-source warnings without silently changing the committed plan outside the provider-enabled live-service contract.

A public-transport journey might therefore create a sequence such as walk to station, wait for service, take a named train, wait/transfer, take the connecting train, take a bus and walk to the destination. Each stage appears as its own Calendar Event on the matching ordinary local Calendar: **Walk**, **Bus**, **Train**, **Tram**, **Ferry**, **Cycle**, **Drive** or **Wait**. Running and other pedestrian pace presets initially remain Walk stages because pace does not change the transport network type.

These Calendars are automatically provisioned when journey functionality is configured and remain first-class user Calendars, not hidden or planner-exclusive containers. The user may rename/recolour them, change their default reminder settings and manually create normal editable Events with Locations on any of them. A stable internal stage-type-to-Calendar mapping—not a mutable Calendar display name—lets the planner select the destination Calendar and offer repair/remapping if one becomes unavailable. Calendar membership alone never makes an Event planner-managed: only explicit journey-group membership does. Exact initial colours, reminder timings and unavailable-Calendar repair UI remain implementation decisions against the existing Calendar lifecycle.

Every planner-generated stage participates in the ordinary default reminder policy of its assigned mode Calendar, including Wait. Changing that Calendar's defaults affects the same reminder-resolution contract used by General and Birthdays; generated stages do not introduce a separate hidden reminder system or require direct Event editing. A cancellation/missed-connection replan reconciles pending reminders for replaced future stages, while an ordinary delay alert does not move timetable-based reminders because the Calendar schedule has not changed.

The group is an ordered finite journey, not an Event recurrence rule. It should reuse the familiar scope vocabulary while preserving different semantics:

- **This stage** replans or deletes only the selected stage while treating its neighbouring boundaries as fixed constraints;
- **This and following** preserves completed/earlier stages and applies a reviewed replacement or deletion from the selected stage onward;
- **All stages** applies to the whole future/unstarted materialised journey; already elapsed stages remain historical records rather than being rewritten.

**Replan** opens the journey planner; generated Events have no ordinary edit action. A this-stage replacement that cannot fit its fixed start/end boundaries or would invalidate a connection is refused with an explanation and an offer to use **This and following**; it never creates an overlap or silently compresses another stage. Changing destination partway through a plan uses **Replan this and following** from a deliberate stage boundary/origin and time; Project E does not infer live position. It previews the replacement sequence and atomically applies the confirmed difference while earlier stages and audit history remain intact. Deleting one middle stage is allowed only with a continuity warning and leaves the group visibly incomplete; it never shifts remaining times automatically.

Buffers are planner inputs selected before materialisation, not post-copy Event-time adjustments and never standalone buffer Events. Preparation, parking/access, transfer-safety and arrival buffers remain separately named in journey metadata so they cannot be double counted. Extra buffer shifts the relevant preceding active stage earlier while preserving its calculated duration. Where that creates real time spent awaiting a scheduled service, the existing **Wait** Event becomes longer; where it merely creates early arrival before a destination Event, the Calendar contains a gap rather than a tiny synthetic block.

For example, a five-minute walk feeding a 09:15 service with five minutes of chosen slack appears as Walk 09:05–09:10 and Wait 09:10–09:15. Increasing the chosen slack to ten minutes makes it Walk 09:00–09:05 and Wait 09:05–09:15; the walk never masquerades as a ten-minute movement. Changing a buffer after materialisation returns to a scoped replan/preview. Direct dragging or editing of generated start/end times is unavailable.

Saving a journey materialises one grouped journey for one selected date/time. The user may efficiently plan several separate future journeys, including a week ahead, but Phase 3 does not save reusable journey templates, recur a journey or automatically materialise future copies. A journey to a recurring destination Event is planned for one selected occurrence at a time so each result uses the relevant current timetable. Cross-timezone journeys must use precise instants while presenting local context at each end.

The calculation itself never creates Events or reminders. The confirmed one-time Calendar action is the explicit authority to create exactly the previewed stage Events in one transaction. Static provider/timetable changes and later manual recalculation produce a reviewed difference rather than silently editing committed Events. Generated stages have no directly user-editable fields; direct deletion is their only ordinary Event-level mutation, using the journey scopes and continuity warnings above. Replan remains a planner operation rather than direct editing.

#### Live timetable enrichment

The installed static timetable is always the planning and Calendar baseline. Live enrichment is a bounded, network-dependent improvement, not live turn-by-turn navigation or tracking of the user. When the configured provider supplies applicable realtime estimates, Project E consumes them automatically while the application/server is running. When it does not, scheduled times continue to work and are labelled as scheduled rather than live.

The model must distinguish the confirmed timetable schedule, latest provider prediction and actual personal travel. Ordinary delay never rewrites an Event's timetable start/end. Instead, the Event can display attributed live status such as “2 minutes late,” and any positive detected delay creates or updates one deduplicated local Inbox alert for that service within the journey. Later prediction changes update that same attention state rather than producing a stream of new alerts. Provider data never proves that the user boarded, arrived or completed a stage.

Cancellation and a predicted missed connection are the two live conditions allowed to change the Calendar journey. Project E may atomically replan the future suffix from the last justified stage boundary using the same destination, profiles, policies and Calendar mapping, supersede the cancelled/infeasible future stages and create their replacements at the new services' timetable times. It must create or update one local notification explaining, for example, that a service was cancelled and the journey Calendar was updated. Ambiguous alternatives, a changed destination, an earlier departure that no longer gives reasonable notice or absence of a satisfying route require attention rather than a guess.

Only a cancellation/missed-connection replan reconciles pending reminders for replaced future stages; ordinary delays leave timetable-based stage reminders unchanged and use the delay alert for operational attention. Already delivered attention/history is never erased and a newly past-due reminder is not replayed blindly.

There is no background journey worker. Polling and deterministic update handling run only while Project E is open/running. On the next start, catch-up reads only the current provider state for a journey that is still in progress or future; it does not replay missed polls and never retroactively updates or notifies about stages whose relevant time has passed. Processing stops after the journey window or scoped deletion, retains the scheduled/last-known-good state when live data fails, exposes staleness and never recreates a stage the user deliberately deleted. Exact feed/provider, in-process polling cadence, active-window boundary, delay-alert reconciliation and provider-enable/disable inheritance remain D21 decisions. Implementing cancellation/missed-connection replacement requires a separately authorised consequential registered handler with audit/recovery behaviour; this planning acceptance does not change the current Phase 2 runtime by itself.

### Spatial decision tools

- **Travel-time matrix:** compare selected Locations across explicit modes, profiles, policies and times. Each cell identifies scenario and freshness rather than masquerading as a Location fact.
- **Reachability:** show network-based areas or reachable canonical records for a stated time/mode/scenario. A geometric radius is acceptable only when clearly named as straight-line approximation.
- **Location comparison:** combine selected, explainable criteria such as travel time, nearby canonical records and attributed provider context. Weighting is user-visible and the output is not a recommendation fact stored on Locations.
- **Nearby exploration:** begin from a selected Location or temporary point and distinguish canonical results from provider features. It never assumes current position or promotes results automatically.

Decision tools should be introduced only after their underlying single-route/search results are trustworthy. Bulk calculation needs explicit limits, progress/cancellation, cache behaviour and clear handling of partial failure.

## Privacy, safety and degraded operation

Spatial information can reveal home, appointments, routines, health providers, relationships and deliberately avoided places. Before any network-backed spatial workflow ships, its design must state:

- the provider contacted and exact information disclosed, including viewport/tile requests;
- whether the request is always local, always explicitly invoked, allowed by a durable preference or confirmed per use;
- whether personal labels, entity IDs, notes, policies or Event details can be excluded from provider input;
- request, result, cache and diagnostic retention and deletion;
- provider terms, rate limits and attribution;
- the local/manual alternative and the state shown on refusal or failure.

Personal routing policy should remain local where practical; an enabled network provider should receive only the minimum geometry, time, mode and constraints needed for the requested calculation—not Project E names, notes, Event titles or Relationship context. Provider use should be visible on the result without requiring per-request confirmation after durable enablement. Logs, diagnostics and fixtures must not capture real private endpoints. Exact route-history and cache retention defaults require a threat/lifecycle review during the first routing slice.

Degraded behaviour is capability-specific:

- no tiles still permits canonical coordinate lists and textual results;
- no geocoder still permits manual Location/address/coordinate entry;
- no routing pack/provider reports routing unavailable without weakening Location use;
- stale packs/results remain inspectable with age/version warnings where useful;
- partial regional coverage must not fabricate a complete route; it may use a configured online fallback only when that optional capability is enabled and the result discloses the provider transition;
- corrupt or incompatible packs remain inactive while last-known-good data stays available.

## Persistence, cache, audit and portability

Durable user-owned Locations, accepted geometry, overlays, profiles, policies and provider references belong in whole-platform portability. Reacquirable packs and disposable caches should be excluded by default but represented by enough manifest/configuration information to explain what must be reacquired. Locally built or non-redistributable packs need a deliberate backup story before users can rely on them.

Cache identity should include every input that can change meaning: resolved endpoints/access points, mode, depart/arrive intent, scenario time, profile/policy fingerprints, engine/provider configuration, spatial/timetable versions and relevant calculation options. Cache records need creation/access time, provenance, staleness reason and safe invalidation. A cache may accelerate a result but cannot be the sole record of a user-owned decision.

Canonical/configuration mutations and pack install/activate/remove actions require appropriate audit. Whether individual read-only spatial queries need a local privacy ledger is deferred to the threat model; indiscriminate query logging could create the sensitive history it is meant to explain.

Schema work must evolve forward through the migration ledger. Existing Location coordinates and source values require representative upgrade tests before richer provenance or geometry replaces their current shape. Development convenience does not justify maintaining two active spatial models.

## Data quality and operational visibility

Candidate deterministic findings include incomplete coordinate pairs, invalid geometry, implausible bounds, duplicate/promotable Locations, provider-link retirement, disagreement between accepted and provider geometry, missing routing access, uncovered Locations and unavailable/outdated pack dependencies. Findings must identify the affected fact and repair path; they must not rewrite canonical data.

Routine pack freshness or successful routing should not create Inbox noise. A future persistent spatial issue should use the platform's eventual deduplicated issue model rather than repeated notifications. Inbox travel attention requires a separately defined due condition and explicit authorisation.

## Delivery approach

### Evidence required before each implementation slice

An authorised slice should begin with a compact implementation packet containing:

1. the concrete user decision or workflow it improves;
2. current-code and current-data constraints, including representative upgrade state;
3. a small fictional or appropriately licensed representative dataset;
4. alternatives considered, including retaining current behaviour;
5. a time-boxed feasibility spike where performance, engine or format suitability is uncertain;
6. privacy/disclosure, licensing, storage, failure and recovery analysis;
7. the narrow product and service contract being committed;
8. migration, portability, audit and cache consequences;
9. behavioural, contract, migration, degraded-operation and accessible UI verification;
10. the fallback or rollback if the approach proves unsuitable.

The spike is evidence, not production architecture. Production work should choose the smallest reversible boundary that supports the proven workflow, remove superseded experiments and record material choices in the responsible current reference or ADR.

### Candidate workstreams and dependency shape

This is a likely dependency order, not a promised release sequence:

1. **Spatial foundations:** first workflow/region, richer Location semantics, provider references, provenance, service envelope and pack feasibility.
2. **Gold Coast pack/engine proof:** portable source-pack manifest, Gold Coast OSM extract, separate SEQ GTFS pack and Valhalla-first engine comparison with honest fallback.
3. **Map 2.0/save workflow:** canonical/provider search, inspection, geometry display and reviewed Location creation.
4. **Single-mode journey proof:** deliberate endpoints, walking first where practical, explanation and cache/version behaviour.
5. **Public transport and stage model:** timetable routing, access legs, services, waits/transfers and stable stage boundaries.
6. **Calendar materialisation:** reviewed atomic creation and coherent lifecycle of separate journey-stage Events.
7. **Live timetable enrichment:** automatic attributed delay status/alerts when available, plus cancellation/missed-connection suffix replacement and reminder reconciliation while Project E is running.
8. **Driving/cycling and profiles/policy:** complete the intended modes; named walking presets and one policy visibly alter an explained result.
9. **Decision tools:** matrix, reachability or comparison based on trusted route/search contracts.

An authorised slice may reorder these when it can prove a coherent alternative, but it should not build broad schema or pack machinery with no end-to-end useful consumer.

### Verification strategy

Each delivered capability should be tested at the boundaries it introduces:

- fresh schema and representative migration from current Location data;
- deterministic fictional geometry/network/timetable fixtures small enough for the repository and valid to redistribute;
- adapter contract tests independent of any one provider;
- pack integrity, incompatibility, interrupted update, rollback, overlap and removal;
- offline, refused-network, timeout, partial coverage, stale result and corrupt data behaviour;
- canonical mutation authority, duplicate prevention, audit and portability;
- route/profile/policy determinism and explanation;
- journey-stage schedule protection plus this-stage/this-and-following/all-scope replan and deletion;
- automatic mode-Calendar provisioning/mapping, per-Calendar default reminders and proof that manually created Events remain ordinary and outside journey automation;
- buffer/profile changes through previewed replan, truthful active-stage durations and expanded Wait stages rather than buffer blocks;
- partial route rendering across missing map packs plus adjacent-LGA/bordering-suburb install prompts and honest capability gaps;
- live-update idempotency, one-alert-per-delayed-service reconciliation, unchanged timetable Event times for ordinary delay, cancellation/missed-connection suffix replacement, reminder reconciliation, startup catch-up and past-stage exclusion;
- one-time-only journey materialisation, including multiple independently planned future dates, with no reusable template or recurring journey path;
- textual equivalence, keyboard operation and supported desktop visual QA;
- measured performance and storage against the chosen first-region workload rather than an invented global scale.

The full test and compile suites remain required. Spatial UI slices should also receive a temporary-port smoke test and human visual/keyboard verification.

## Deferred implementation decision register

These choices are deliberately deferred because the present plan lacks the concrete workflow or evidence needed to make them responsibly. Resolving one does not authorise its implementation.

| ID | Decision deferred | Evidence required to resolve it | Safe position until resolved |
| --- | --- | --- | --- |
| D01 | Exact first pack set, coverage boundaries and useful size for the accepted journey-to-Calendar workflow | Sample Brisbane/Gold Coast journeys, corridor dependencies, bordering-suburb cuts, storage budget and an acquisition/build spike | Start with Gold Coast LGA; support independently managed adjoining LGAs and smaller bordering-suburb coverage for route-edge gaps; do not assume endpoint LGAs alone form a routable region. |
| D02 | Rich Location field/provenance model and migration of current address, coordinates and `source` | Current-data audit plus create/edit/save-from-map workflows and upgrade fixtures | Preserve current valid fields; do not add parallel geometry truth. |
| D03 | Geometry representation, supported types, CRS, precision, validation and spatial index | Queries needed by the first slice, representative points/areas and measured SQLite/library options | Require explicit coordinates/units at boundaries; use current points only. |
| D04 | Access-point and Location-hierarchy persistence/cardinality | At least one building and one station/area workflow testing independent identity and reuse | Use a Location or temporary/provider point explicitly; no inferred hierarchy. |
| D05 | Provider-reference reconciliation across feature moves/splits/merges | Two real versions of the chosen source and reviewed mismatch cases | Store no supposedly universal external ID; never auto-relink. |
| D06 | Exact manifest/container transport, boundary buffer, retention of reacquirable raw inputs, LGA/suburb/corridor dependency closure and distribution | Gold Coast build using official LGA boundary, OSM PBF and separate SEQ GTFS; then bordering-suburb and Logan/Brisbane unions, size, update and rollback prototypes | Use the researched source-pack plus engine-derived-cache split; keep all pack data outside Git/entity data; make LGA and smaller suburb-group units compatible source packs; do not treat engine-native graphs as the portable contract. |
| D07 | Map renderer, local tile format and drawing/selection tooling | Accessibility, offline, performance, licence and maintenance spike in current server-rendered UI | Retain the current Map and textual fallback; no new broad client dependency. |
| D08 | Local/online geocoder choice, ranking, reverse geocoding and duplicate workflow | Representative Australian queries, current Nominatim behaviour, pack feasibility and privacy review | Manual entry remains authoritative; the online capability remains optional and provider use visible. |
| D09 | Final routing engine/runtime/process boundary | Valhalla-first Gold Coast/SEQ spike with MOTIS as challenger and OTP/GraphHopper comparators where needed; measure modes, transit legs, pace, policies, resources and Windows packaging | Keep a provider-independent adapter; prefer Valhalla provisionally; do not build a custom pathfinder or make network routing mandatory. |
| D10 | Exact journey-group/baseline persistence, cache schema and operational-history retention | One-time materialisation, scoped replan/delete, cancellation replacement, threat model, reproducibility need and measured calculation cost | Unsaved results remain transient; a materialised group retains the minimum confirmed baseline, provenance and audit needed to explain its Events and live replacements, not a reusable journey template or incidental route history. |
| D11 | Measured preset values, observation aggregation, distance/duration applicability, Sprint inclusion and broader policy precedence/conflicts | User measurements for regular/fast/run, candidate short sprint, engine controls and worked per-leg/cumulative/hard/soft cases | Record stable sourced presets; Regular walk is default; initially constrain each contiguous leg and warn on unusually high cumulative effort; only applicable faster presets are warned alternatives requiring selection; no silent learning or arbitrary speed. |
| D12 | Public-transport sources, static update cadence, station complexes and multimodal engine boundary | Brisbane/Gold Coast/corridor licence and coverage, static timetable samples, engine fit and update burden | Public transport is a required phase mode and uses an installed static timetable by default; exact source and engine wait for the spike. |
| D13 | Journey-group persistence, internal Calendar-role mapping/repair, initial colours/reminder timings, stage titles and scope implementation | Multi-stage commute and destination-Event journeys; unavailable/renamed Calendar repair, constrained this-stage replacement, middle-stage deletion, change-destination this-and-following and rollback cases | Automatically provision ordinary Walk, Bus, Train, Tram, Ferry, Cycle, Drive and Wait Calendars with editable settings/default reminders; every generated stage uses its Calendar policy; only explicit group membership locks generated Events; no direct edits; buffers shift active stages and expand real Wait stages without becoming Events. |
| D14 | Optional online-capability packaging, durable enable/disable consent, provider disclosure UI and query/privacy logging | Threat model covering tiles, search/routes, automatic out-of-coverage fallback and local alternatives | Online fallback is unavailable by default; once deliberately enabled it may be automatic, visible and limited to minimum provider inputs; avoid query logs. |
| D15 | Elevation, accessibility and environmental evidence model | Available first-region attributes, freshness/error analysis and user need | Present no unsupported safety/accessibility conclusion. |
| D16 | Coverage selection, route-edge pack recommendations and fallback across overlapping local/online providers | Multiple-pack prototype with gaps, LGA/suburb boundaries, transit shapes extending beyond map/street coverage and version conflicts | Draw available route coordinates across blank map space, distinguish missing visual from missing routing capability, offer the adjoining LGA or bordering-suburb pack and use online context only when enabled; never silently blend incompatible results. |
| D17 | Native/Java engine acquisition, loopback-versus-one-shot execution, upgrade compatibility and optional provider-plugin support | Valhalla/MOTIS packaging spike, signature/checksum, licence/security review, startup/failure handling and repeatable Windows setup | Keep runtime code outside data packs, use the standard-library adapter boundary and add no executable dependency merely for architectural neatness. |
| D18 | Performance/storage budgets, pruning and bulk-calculation limits | Measured first-region pack and representative device/workload | Bound each authorised slice and expose progress/cancellation where needed. |
| D19 | Durable overlays or saved-view ontology | Repeated workflow proving identity, editing, sharing across views and recovery needs | Keep viewport, selection and temporary points transient. Journey “save” is resolved as one-time Calendar materialisation; Phase 3 has no reusable saved-journey or recurring-journey model. |
| D20 | Location-derived timezone and cross-zone spatial time semantics | Cross-zone Event/journey cases and authoritative timezone-boundary source | Event/Calendar IANA timezone remains authoritative; do not infer silently. |
| D21 | Live-service feed/provider, provider-enable inheritance, in-process polling/active-window limits, delay-alert identity and predicted-status persistence | Representative one-minute/changing delays, cancellation, platform change, missed connection, unavailable/stale feed, startup catch-up, past stages and user deletion; provider licence/privacy/reliability evidence | Use available enabled-provider live data only while Project E runs; retain timetable Event times for ordinary delays and maintain one local alert per delayed service/journey; mutate only future stages for cancellation or missed connection; reconcile their reminders; on startup process only still-current/future state; never infer location, boarding or actual arrival. |

### Decision procedure

When implementation reaches one of these gates:

1. state the concrete workflow and the decision ID;
2. inspect current code/data and collect the required representative evidence;
3. compare viable options, including doing less;
4. test the riskiest assumption with a bounded spike if needed;
5. choose the narrowest reversible option that meets the workflow and accepted boundaries;
6. ask the user before a material product-direction or long-term convention change;
7. record the decision, evidence, trade-offs, migration and reconsideration trigger in this workspace and the responsible ADR/reference documentation when implemented.

“Decide during implementation” never means “leave accidental behaviour undocumented.” If evidence is still insufficient, the slice should retain the safe position, narrow scope or stop at the decision gate.

## Explicit deferrals outside the current commitment

Phase 3 does not presently commit to global offline completeness, commercial-map parity, live turn-by-turn navigation, continuous location tracking/history, a mobile application, any background journey process while Project E is closed, background current-location collection, reusable/recurring saved journeys, opaque/AI-selected routing, silent behavioural learning, realtime data as an offline/core dependency, public reviews, safety guarantees, automatic mutation outside cancellation/missed-connection handling in the provider-enabled live-journey contract, bulk provider-feature promotion, arbitrary executable extensions or any particular provider/engine/format before its decision gate is resolved.

Automatic use of available live-service data is now inside the desired journey workflow, but only as attributed network enrichment over a working static timetable with deterministic limits. External push/OS notification channels, vehicle navigation and personal-position tracking remain separate future decisions.

These items require separate product authorisation even if foundations built in Phase 3 later make them technically possible.

## Integrated completion signals

Phase 3 should be judged by a useful integrated spatial system, not a feature count. The current end-state signals are:

- canonical Locations retain personal identity independently of providers and installed data;
- richer Location geometry/provenance upgrades current data without duplicate truth;
- one useful regional pack can be inspected, installed, replaced, rolled back and removed safely;
- a transit route with coordinates remains visible across uninstalled map coverage, distinguishes missing visual/routing capabilities and offers an adjoining-LGA or bordering-suburb pack;
- a provider feature or deliberate point can be reviewed and saved as a Location with duplicate handling;
- Map/Location views explain canonical/provider geometry, coverage, provenance and degraded state accessibly;
- walking, driving, cycling and public-transport journeys work within their declared coverage and explain source, assumptions and uncertainty;
- Regular walk, Fast walk/jog and Run presets behave predictably, and a faster feasible alternative is warned rather than silently selected;
- measured pace provenance and applicability limits remain inspectable, including any short-distance Sprint profile;
- a routing policy visibly affects an explained result;
- a standalone or Event-linked multi-stage journey can be previewed and explicitly added as separate grouped Calendar Events whose calculated times are protected;
- this-stage, this-and-following and all-stage replan/delete preserve earlier stages, preview consequences and never silently retime the remainder;
- Walk, Bus, Train, Tram, Ferry, Cycle, Drive and Wait are automatically provisioned usable ordinary Calendars with editable default reminders, while explicit journey membership alone controls generated-stage locking and automation;
- buffers move active stages earlier without changing their truthful duration or creating buffer blocks, and scheduled-service slack appears as Wait;
- saving creates one date-specific journey group with no reusable/recurring journey model;
- a journey keeps scheduled timetable times by default and, while Project E runs, available live data produces one alert/status for any delay without retiming Events; only cancellation or a missed connection replaces future stages and reconciles their reminders, with startup catch-up limited to still-current/future journeys;
- a matrix, reachability or comparison workflow supports a meaningful personal decision from the same route/search contracts;
- export/recovery preserves user-owned spatial data while replaceable packs/caches retain honest reacquisition and staleness behaviour;
- privacy disclosure, offline refusal/failure and unsupported safety/accessibility claims remain controlled and understandable.

These are planning signals, not independent feature promises. Evidence may justify changing or removing a signal while preserving the phase objective and accepted boundaries.

## Phase 3 expansion workspace

**Planning only:** add dated numbered **Complete:** entries here only after explicitly authorised implementation is delivered and verified. Each entry should name the implemented slice and any deferred-decision IDs it resolved, then link or summarise the resulting durable contract.

> **Guiding principle:** Make location and movement first-class operational concepts without turning replaceable spatial data into competing personal truth.
