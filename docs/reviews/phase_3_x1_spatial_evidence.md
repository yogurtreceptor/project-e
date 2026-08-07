# Phase 3 X1 Gold Coast Spatial Evidence

Date: 2026-08-07

Status: Complete evidence spike; no production provider, pack, adapter or regional
data has been installed.

## Outcome

X1 clears the evidence prerequisite for N4. One verified Gold Coast source set
was carried through a buffered OSM extract, local vector-tile build, local search,
street graphs and a static SEQ timetable. The result changes the earlier
single-engine assumption into capability-specific front-runners:

| Capability | N4/later front-runner | Challenger and reconsideration trigger |
| --- | --- | --- |
| Local normal map | tilemaker-derived vector tiles in MBTiles, rendered by vendored MapLibre GL JS | MOTIS tiles, or PMTiles as a storage alternative, if N4's visual/accessibility review, coastline completion, atomic activation or same-origin serving exposes a concrete problem. |
| Installed search | MOTIS geocoding over the same OSM/GTFS build | A small derived SQLite/FTS index if MOTIS cannot be packaged or updated independently within the measured memory envelope. The existing explicit network Nominatim option remains an optional fallback, not installed-pack search. |
| Walk/cycle/drive routing | Valhalla | MOTIS if Windows packaging, snap validation, policy translation, admin/timezone packaging or graph lifecycle cannot meet N3. |
| Static public transport | MOTIS | OpenTripPlanner only if N7 finds a concrete station/service-day/wait-stage defect that cannot be normalized. The measured Valhalla wheel route did not provide a repeatable direct import of the supplied current GTFS. |

These are evidence-led starting positions, not production adoption. N4 must still
implement the manifest/lifecycle boundary and prove a usable local map/search
slice. N6 and N7 remain separately authorised implementation slices.

## Reproducibility and isolation

The committed [`tools/spatial_evidence`](../../tools/spatial_evidence/README.md)
package owns the fixed source/tool manifest, provider-neutral scenarios,
checksum/inventory code, cold-start and loopback probes, and a minimal read-only
MBTiles server. Generated inputs, executables, builds, configs, raw responses and
reports stayed under ignored `instance/spatial-evidence/`. No private endpoint,
canonical record, Event, profile/policy value, provider identity or database
change was made.

The measured host was Ubuntu 24.04 under WSL2, Linux 6.6.87.2, Python 3.12.3,
8 logical CPUs, 3.7 GiB RAM, 1 GiB swap and approximately 951 GiB free disk.
The helpers use only the Python standard library. Candidate engines remain native
executables reached through controlled subprocesses or HTTP bound to
`127.0.0.1`; none becomes a Python application dependency.

## Fixed source set, licence and recovery

| Input | Verified snapshot | Size | Licence, attribution and recovery |
| --- | --- | ---: | --- |
| Queensland OSM PBF | Geofabrik `queensland-260801.osm.pbf`; OSM data through `2026-08-01T10:46:22Z`; SHA-256 `9bd9e05f…768752` | 196,505,786 B | [ODbL 1.0 / OpenStreetMap attribution](https://www.openstreetmap.org/copyright): “Map data © OpenStreetMap contributors”. The dated Geofabrik object is the reacquisition route; retain its digest with every build. |
| Gold Coast LGA boundary | City of Gold Coast WFS acquired 2026-08-07; metadata modified 2026-08-02; SHA-256 `6d61be2c…23eac` | 104,517 B | [CC BY 3.0 Australia](https://data.gov.au/data/dataset/gold-coast-local-government-authority-boundary), attributed to City of Gold Coast. The WFS is mutable, so rollback requires retaining the exact verified input until an immutable archive exists. |
| Translink SEQ GTFS | Feed period 2026-08-07–2026-10-06; SHA-256 `e1c63cbf…a87b` | 28,970,475 B compressed; 210,269,969 B text | [CC BY 4.0 plus Translink open-data terms](https://translink.com.au/about-translink/open-data/terms-and-conditions), attributed to Department of Transport and Main Roads – Translink Division. The current-feed URL is mutable; retain the verified ZIP or an authorised immutable archive reference per activated build. |

The boundary is one WGS84 MultiPolygon with 5,261 vertices and extent
`153.1689,-28.2652,153.5518,-27.6904`. The deterministic 15 km evidence envelope
is `153.0163213725073,-28.399946676248653,153.7043786274927,-27.555653323751347`.
The GTFS contains 13,096 stops and 921 routes: 2 tram, 418 rail, 492 bus and
9 ferry routes. Its stop extent reaches well beyond the street/map envelope;
therefore timetable coverage and street/map coverage must remain separate
capabilities in every manifest and result.

Rollback never means relying on today's mutable URL. A production activation
needs source and derived digests, tool/build-policy versions, coverage metadata,
licence/notices and a pointer to the last-known-good activation. Raw OSM/boundary/
GTFS retention versus authorised immutable reacquisition remains an N4 D16 choice,
but an activation without either is invalid. Removing all derived data must still
leave canonical Locations, profiles, policies and Events untouched.

## Build route and resource evidence

All rows use the same buffered OSM extract and fixed tool versions. Times are
single evidence-build wall times; peak RSS comes from `/usr/bin/time -v`.

| Stage | Derived result | Elapsed | Peak RSS | Material finding |
| --- | ---: | ---: | ---: | --- |
| osmium 1.16 `complete_ways` extract | 19,950,577 B; 2,385,290 nodes, 253,651 ways, 8,850 relations; SHA-256 `74330500…643b9` | 12.12 s | 3,383,904 KiB | Reference completion peaked at about 3.23 GiB and pulled nodes from long ways as far as latitude -20.455. A bounding header is not proof that all referenced objects are spatially local. |
| tilemaker 2.4 OpenMapTiles-like build | 15,937,536 B MBTiles; 1,431 gzip vector tiles at z0–14; SHA-256 `1c871a1b…f667a` | 6.90 s | 413,084 KiB | Place, boundary, POI, address, road, building, water, park and land layers were produced. External coastline/urban/ice/glacier shapefiles were deliberately absent, so this is not yet a complete normal basemap. |
| Valhalla 3.8.3 graph and extract | 45,985,768 B across 17 graph tiles; 197,358 graph nodes and 521,170 directed edges | 7.69 s; tar read 0.21 s | 485,304 KiB | Fast and compact, but the wheel build warned that admin and timezone databases were absent. N6 may not claim complete timed/admin-aware behaviour until those inputs are packaged and versioned. |
| MOTIS 2.11 OSM+GTFS import | 231,364,051 B across 69 files; about 82 MB tiles, 39 MB street routing, 20 MB address index and 79 MB timetable/shapes/matches | 21.02 s | 3,311,356 KiB | One build supplied local search, tiles, street routing and multimodal static transit, but its import peak is about 3.16 GiB and capabilities are operationally coupled. |

The two roughly 3.2 GiB peaks leave little headroom on the measured host. N4's
front-runner is therefore a verified prebuilt derived archive with an optional
developer rebuild path, not an unannounced local build during ordinary use.
This is not yet a permanent resource budget: N4 must measure staged validation,
atomic activation, disk duplication and interrupted update before fixing one.

The extract closure behaviour is also a boundary warning. N4 should compare a
more selective reference-complete extract/build route and record actual feature
coverage rather than treating a rectangular header or LGA polygon as proof of a
hard routing seam. Compatible neighbouring source packs still rebuild one
common-snapshot union graph; separately built graphs are not overlaid.

## Map, search and accessibility evidence

The tile archive contains the expected general-map layers and can be read through
the evidence package's same-origin, loopback-only XYZ-to-TMS server. MapLibre GL
JS 6.2.0 was acquired as a fixed BSD-3-Clause artifact with no CDN requirement.
This pair is smaller and less coupled than using MOTIS's approximately 82 MB tile
store as the N4 base view. MBTiles also fits Project E's existing SQLite and
atomic-file handling experience; PMTiles remains worth reconsidering only if its
single-file range access materially simplifies N4 serving or activation.

This evidence does **not** certify the tile output as a production visual. Ocean/
coastline side inputs, a reviewed local style, labels, high-DPI rendering,
attribution placement and browser behaviour remain N4 acceptance work. The
available desktop browser-control bridge could not attach to the WSL workspace,
so no visual/browser claim is carried forward from X1. That limitation is
deliberately recorded rather than inferred away.

MapLibre's essential map is WebGL/canvas, so it cannot replace N2's semantic DOM
search results, selected-place details, keyboard controls, focus/status messages,
non-colour selection cues or complete text alternative. N4 must retain those N2
contracts as the authoritative accessibility layer and then add a wide,
constrained, keyboard and screen-reader-oriented browser review. Failure of that
integration is a renderer reconsideration trigger.

MOTIS geocoding returned five typed local candidates for “Surfers Paradise” in a
5.25 ms warm median, including `STOP` and `PLACE` results. These can sit in N2's
installed-provider group only after Project E's canonical-first ranking; provider
results never become canonical by selection. The address index is an implementation
component of the disposable build, not a new source of truth. Reconsider a small
SQLite/FTS derivative if N4 cannot independently validate/update geocoding or if
MOTIS's coupled import/storage cost dominates the first map slice.

## Routing and N3 semantic fit

Cold starts on loopback were 308.519 ms and 127,315,968 B RSS for MOTIS, and
209.241 ms and 57,409,536 B RSS for Valhalla. The table reports the median of each
three-call probe; the first call is shown where it exposes cold-cache cost.

| Case | Result | Latency evidence |
| --- | --- | --- |
| Valhalla Walk | 3.384 km, 2,425.823 s, one leg | 142.005 ms first; 9.49 ms median |
| Valhalla Cycle | 11.585 km, 2,534.827 s | 63.195 ms first; 21.215 ms median |
| Valhalla Drive | 12.154 km, 746.994 s | 24.713 ms first; 17.888 ms median |
| Valhalla northern boundary drive | 45.871 km, 1,857.833 s and geometry crossing the buffered area | 75.132 ms first; 24.599 ms median |
| MOTIS Walk at 1.4 m/s | 3,495 m, 2,542 s | 95.700 ms first; 10.667 ms median |
| MOTIS Walk at 2.0 / 2.8 m/s | 3,497 m / 3,504 m; 1,794 s / 1,260 s | 9.666 ms / 8.339 ms median |
| MOTIS depart-at static transit | 3 alternatives; first 2,640 s with Walk–Tram–Walk–Bus–Walk legs | 68.254 ms first; 14.103 ms median |
| MOTIS arrive-by static transit | 3 alternatives; first 2,640 s with the same normalized mode sequence | 19.677 ms median |

Walking speed is therefore representable as an explicit adapter input without
letting either engine own the profile's stable identity. Project E must still
enforce the requested profile's contiguous distance/duration applicability before
and after the call. X1 did not establish personal Regular/Fast/Run values.

The following mappings are not safe to imply:

- MOTIS's default `maxDirectTime=1800` returned an empty result for the same real
  3.5 km walk that succeeded with an explicit 21,600-second search bound. Empty
  means “outside this provider search bound”, not `NO_ROUTE`. The adapter must
  explicitly set/name the bound and retain coverage/no-route/provider failure as
  different outcomes.
- A Brisbane-to-Surfers Valhalla request outside the street graph returned HTTP
  200 and a 70.77 km route after silently snapping the northern input south to
  latitude -27.55125. The adapter must independently test endpoint-to-snap distance
  against declared coverage and reject or warn before normalisation.
- MOTIS returned transit mode legs but no explicit Wait legs. N7 may derive a
  scheduled Wait only from stable adjacent timetable timestamps and must explain
  that derivation. If those meanings cannot be reconstructed deterministically,
  the adapter is unsupported.
- Candidate-specific avoidance, wheelchair/accessibility, vehicle, cycle,
  environmental, lighting, traffic and safety controls were not proven against
  N3 policy semantics. They remain unsupported requirements, not silently ignored
  flags. Coarse provider wheelchair data cannot support a general accessible-route
  promise.
- Corrupt/malformed GTFS, service-day edge cases and source-update activation were
  not promoted into runtime behaviour. N4/N7 must reject them during staged
  validation and retain the last-known-good timetable. A successful X1 import is
  not evidence that arbitrary future feeds are valid.
- The Valhalla wheel's missing admin/timezone side data prevents an honest timed
  street-routing claim. MOTIS's full-SEQ timetable over a smaller street graph is
  labelled partial whenever access legs exceed installed street coverage.

No N3 request/result/fingerprint type needs to change. The observed problems fit
its existing explicit capability, coverage, snap, warning, profile/policy,
unsupported, no-route and provider-failure fields. Provider defaults are exactly
why that seam remains Project E-owned.

## Windows and operational boundary

The verified MOTIS 2.11.0 Windows archive started natively under PowerShell and
`motis.exe --help` reported `MOTIS v2.11.0` with exit status 0. Its archive
SHA-256 `29b53df1…00a4` matches the release asset; the Linux archive SHA-256 is
`508505d3…6dfa`. Full Windows import/server routing was not repeated because it
would duplicate the source build, but N4/N7 still need a Windows install/update/
restart smoke test before production use.

Valhalla was proven only through its manylinux wheel under WSL2. There is no X1
evidence for a native Windows artifact. This is its most important challenger
trigger even though its street graph, latency and memory measurements are better.
Both services were bound only to loopback and shut down after each probe. Docker
was present on Windows but WSL integration was unavailable, and interactive
system package installation was not assumed; verified staged binaries kept the
experiment disposable.

## N4 hand-off and reconsideration triggers

N4 may start from this bounded route:

1. Define a declarative source/derived manifest that names independent map,
   search, street and timetable coverage, exact digests, licences, attribution,
   build policy and compatible versions.
2. Stage a **prebuilt** Gold Coast MBTiles archive and MOTIS address component
   under ignored storage; validate structure, coverage, attribution and semantic
   search before atomic activation. Do not import at application startup.
3. Complete the vector tiles with licensed coastline/ocean input, add a reviewed
   local style and integrate vendored MapLibre through a same-origin endpoint.
4. Preserve N2's canonical-first search, DOM/text equivalent, selected state and
   unavailable/degraded mode. A provider feature remains external context.
5. Exercise corrupt/incompatible archives, interrupted install/update, insufficient
   disk, overlap, boundary selection, offline restart, removal and last-known-good
   rollback. Measure peak disk while old, staged and new copies coexist before
   fixing archive/retention budgets.
6. Keep Valhalla and the complete MOTIS transit build outside N4 production unless
   the slice needs their graph lifecycle to prove the common manifest. They are
   N6/N7 front-runners, not reasons to broaden the first installed-map slice.

Reconsider tilemaker/MBTiles when coastline/style completion is disproportionate,
MapLibre cannot meet the N2 UI/accessibility boundary, or PMTiles/MOTIS materially
improves atomic activation and serving. Reconsider MOTIS search when capability
separation or the roughly 3.16 GiB import peak makes a map/search-only install
unsafe. Reconsider Valhalla for streets when native Windows operation, admin/
timezone packaging, bounded snapping or N3 policy translation fails. Reconsider
MOTIS for transit when N7 cannot derive explicit waits, distinguish empty/coverage/
no-route, or validate update/service-day semantics. Only then promote the named
challenger; do not add a second production source of truth.

## Verification record

- All three public source digests and both deterministic file-build digests were
  rechecked by the committed inventory command.
- Provider scenarios were run three times each against fresh loopback services;
  reports remained ignored because they contain disposable measurements.
- The native Windows MOTIS startup check passed; the browser-control limitation
  is recorded above and becomes an explicit N4 visual acceptance item.
- Five focused evidence-package tests cover boundary buffering, GTFS identity/
  extent, MBTiles inventory and XYZ/TMS reads, source verification, and committed
  scenario/manifest completeness.
- The loopback MBTiles `/health` smoke passed, all 330 repository tests passed,
  and `app`, `run.py`, `tests` and the evidence package compiled successfully.
- X1 changed no application runtime, schema, canonical data or Event lifecycle.
