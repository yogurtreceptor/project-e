# Phase 3 X1 spatial evidence package

This package reproduces the evidence behind the X1 Gold Coast decision. It is
not application runtime code: it creates no pack record, provider adapter,
canonical fact or production data. Public inputs, third-party executables,
derived builds and generated reports belong under the already ignored
`instance/spatial-evidence/` directory.

## Fixed inputs and host

`manifest.json` fixes the source URLs, versions, licences, attributions and
SHA-256 digests used on 2026-08-07. The measured host was Ubuntu 24.04 under
WSL2 with Python 3.12.3, 8 logical CPUs, 3.7 GiB RAM and 1 GiB swap. Exact tool
artifact digests are also recorded because current-feed and package URLs can
otherwise drift.

From the repository root:

```sh
python3 -m tools.spatial_evidence acquire queensland_osm
python3 -m tools.spatial_evidence acquire gold_coast_boundary
python3 -m tools.spatial_evidence acquire seq_gtfs
python3 -m tools.spatial_evidence inventory
```

Acquisition downloads to a `.part` file, verifies the committed digest and only
then replaces the named source. The boundary inspector derives the 15 km WGS84
working envelope used below:

```text
153.0163213725073,-28.399946676248653,153.7043786274927,-27.555653323751347
```

## Disposable builds

The following are the measured command shapes. Resolve each tool from its
verified staged artifact; do not add it to Project E's Python runtime.

1. Extract OSM with osmium 1.16.0 using reference-complete ways:

   ```sh
   /usr/bin/time -v osmium extract \
     --strategy complete_ways \
     --bbox 153.0163213725073,-28.399946676248653,153.7043786274927,-27.555653323751347 \
     --overwrite \
     --output instance/spatial-evidence/builds/gold-coast-buffer15km-260801.osm.pbf \
     instance/spatial-evidence/sources/queensland-260801.osm.pbf
   ```

2. Build vector tiles with tilemaker 2.4.0 and its shipped OpenMapTiles profile.
   The evidence config is the shipped `config-openmaptiles.json` with the four
   external-shapefile layers `ocean`, `urban_areas`, `ice_shelf` and `glacier`
   removed. That intentional omission isolates the OSM-only build but means the
   archive is not a complete production basemap.

   ```sh
   /usr/bin/time -v tilemaker \
     --input instance/spatial-evidence/builds/gold-coast-buffer15km-260801.osm.pbf \
     --output instance/spatial-evidence/builds/gold-coast-buffer15km-tilemaker-v2.4.0.mbtiles \
     --config instance/spatial-evidence/tools/tilemaker-config-v2.4.0.json \
     --process instance/spatial-evidence/tools/tilemaker-process-v2.4.0.lua
   ```

3. Import MOTIS 2.11.0 from the same OSM extract and the verified SEQ GTFS. The
   working `config.yml` binds `server.host` to `127.0.0.1`, names both absolute
   source paths, enables tiles, street routing, geocoding and reverse geocoding,
   and disables live/realtime input. Run `motis import` in that directory, then
   run `motis server` there for probes. The generated data config was also bound
   to loopback and its maximum direct-street duration was made explicit at
   21,600 seconds for the bounded-route comparison.

4. Install the fixed pyvalhalla 3.8.3 wheel in an isolated virtual environment.
   Generate a config with its `valhalla_build_config`, setting the tile directory,
   tile extract and `httpd.service.listen` to `tcp://127.0.0.1:18081`. Run the
   wheel's native `valhalla_build_tiles -c CONFIG OSM_PBF`, followed by
   `valhalla_build_extract -c CONFIG`. The wheel did not supply Australian admin
   or timezone databases; the resulting warnings and timed-route limitation are
   part of the evidence, not something to hide.

The [decision record](../../docs/reviews/phase_3_x1_spatial_evidence.md) records
the observed sizes, elapsed time and peak memory. Re-running `inventory` verifies
the two deterministic file-build digests and inventories directory builds.

## Provider and tile probes

`scenarios.json` is the provider-independent comparison set. With the services
running on the loopback addresses above:

```sh
python3 -m tools.spatial_evidence probe motis http://127.0.0.1:18080
python3 -m tools.spatial_evidence probe valhalla http://127.0.0.1:18081
python3 -m tools.spatial_evidence cold-start motis MOTIS_BINARY MOTIS_BUILD_DIR http://127.0.0.1:18080
python3 -m tools.spatial_evidence cold-start valhalla VALHALLA_SERVICE . http://127.0.0.1:18081 --config VALHALLA_CONFIG
python3 -m tools.spatial_evidence serve-mbtiles \
  instance/spatial-evidence/builds/gold-coast-buffer15km-tilemaker-v2.4.0.mbtiles
```

The MBTiles server binds only to `127.0.0.1`, translates XYZ requests to TMS
rows, preserves gzip encoding and exposes `/health`. The probes summarize only
contract-relevant output; generated raw responses and reports stay ignored.

Run the package regression checks with:

```sh
python3 -m unittest tests.test_spatial_evidence
```
