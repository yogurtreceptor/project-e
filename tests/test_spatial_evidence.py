import gzip
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.spatial_evidence.evidence import (
    buffered_bbox,
    inspect_boundary,
    inspect_gtfs,
    inspect_mbtiles,
    inventory,
    load_manifest,
    mbtiles_tile,
)


class SpatialEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_buffered_bbox_and_boundary_inventory_are_deterministic(self):
        boundary = self.root / "boundary.geojson"
        boundary.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[153.0, -28.0], [153.2, -28.0], [153.2, -27.8], [153.0, -28.0]]
                                ],
                            },
                            "properties": {},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = inspect_boundary(boundary, buffer_km=15)

        self.assertEqual(result["bbox"], [153.0, -28.0, 153.2, -27.8])
        self.assertEqual(result["vertex_count"], 4)
        self.assertEqual(result["geometry_types"], ["Polygon"])
        self.assertEqual(
            result["buffered_bbox"], list(buffered_bbox((153.0, -28.0, 153.2, -27.8), 15))
        )

    def test_gtfs_inspection_reports_identity_modes_extent_and_sizes(self):
        feed = self.root / "feed.zip"
        files = {
            "agency.txt": "agency_id,agency_name,agency_timezone\nA,Example,Australia/Brisbane\n",
            "calendar.txt": "service_id,monday\nWK,1\n",
            "feed_info.txt": (
                "feed_publisher_name,feed_start_date,feed_end_date\n"
                "Example,20260807,20261006\n"
            ),
            "routes.txt": "route_id,route_type\nR1,0\nR2,3\n",
            "stops.txt": (
                "stop_id,stop_name,stop_lat,stop_lon\n"
                "S1,North,-27.8,153.0\nS2,South,-28.1,153.4\n"
            ),
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,S1,1\n",
            "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\n",
        }
        with zipfile.ZipFile(feed, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)

        result = inspect_gtfs(feed)

        self.assertEqual(result["feed"]["feed_start_date"], "20260807")
        self.assertEqual(result["agencies"][0]["agency_name"], "Example")
        self.assertEqual(result["route_type_counts"], {"0": 1, "3": 1})
        self.assertEqual(result["stop_count"], 2)
        self.assertEqual(result["stop_bbox"], [153.0, -28.1, 153.4, -27.8])
        self.assertEqual(result["entries"]["stop_times.txt"]["rows"], 1)

    def test_mbtiles_inspection_and_xyz_to_tms_read(self):
        archive = self.root / "map.mbtiles"
        connection = sqlite3.connect(archive)
        connection.executescript(
            "CREATE TABLE metadata (name TEXT, value TEXT);"
            "CREATE TABLE tiles (zoom_level INTEGER, tile_column INTEGER, "
            "tile_row INTEGER, tile_data BLOB);"
        )
        connection.execute("INSERT INTO metadata VALUES ('format', 'pbf')")
        payload = gzip.compress(b"test-vector-tile")
        connection.execute("INSERT INTO tiles VALUES (2, 1, 2, ?)", (payload,))
        connection.commit()
        connection.close()

        result = inspect_mbtiles(archive)

        self.assertEqual(result["metadata"]["format"], "pbf")
        self.assertEqual(result["tile_count"], 1)
        self.assertEqual(result["tile_bytes"], len(payload))
        self.assertEqual(mbtiles_tile(archive, 2, 1, 1), payload)
        self.assertIsNone(mbtiles_tile(archive, 2, 4, 1))

    def test_inventory_verifies_sources_and_keeps_builds_disposable(self):
        source_root = self.root / "sources"
        source_root.mkdir()
        source = source_root / "source.pbf"
        source.write_bytes(b"public-source")
        manifest = {
            "snapshot_id": "test-snapshot",
            "buffer_km": 15,
            "sources": {
                "osm": {
                    "kind": "osm",
                    "filename": "source.pbf",
                    "sha256": (
                        "cf602528f34f4e5c31e630e9d4912cbecc6de1cefddd1cd5f2475d409108f159"
                    ),
                }
            },
            "builds": {
                "missing": {"kind": "directory", "path": "not-built"}
            },
        }

        result = inventory(self.root, manifest)

        self.assertTrue(result["sources"]["osm"]["verified"])
        self.assertFalse(result["builds"]["missing"]["present"])

    def test_committed_manifest_and_scenarios_define_the_x1_contract(self):
        manifest = load_manifest()
        scenarios = json.loads(
            (Path(__file__).parents[1] / "tools/spatial_evidence/scenarios.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(manifest["snapshot_id"], "x1-gold-coast-20260807")
        self.assertEqual(
            set(manifest["sources"]),
            {"queensland_osm", "gold_coast_boundary", "seq_gtfs"},
        )
        self.assertEqual(set(scenarios), {"motis", "valhalla"})
        self.assertIn(
            "outside_coverage_snap", {item["key"] for item in scenarios["valhalla"]}
        )
        self.assertIn(
            "walk_default_bound_empty", {item["key"] for item in scenarios["motis"]}
        )


if __name__ == "__main__":
    unittest.main()
