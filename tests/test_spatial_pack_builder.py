import json
import zipfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.spatial_pack import inspect_and_stage_spatial_pack
from tests.spatial_pack_test_support import TEST_BOUNDS, _write_mbtiles
from tools.spatial_pack_builder import build_spatial_pack, decode_geometry


class SpatialPackBuilderTests(unittest.TestCase):
    def test_builder_is_deterministic_and_indexes_static_transit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            mbtiles = root / "map.mbtiles"
            boundary = root / "boundary.geojson"
            gtfs = root / "gtfs.zip"
            first = root / "first.zip"
            second = root / "second.zip"
            _write_mbtiles(mbtiles)
            boundary.write_text(
                json.dumps(
                    {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {},
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": [
                                        [
                                            [153.1, -28.4],
                                            [153.9, -28.4],
                                            [153.9, -27.6],
                                            [153.1, -27.6],
                                            [153.1, -28.4],
                                        ]
                                    ],
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with zipfile.ZipFile(gtfs, "w") as archive:
                archive.writestr(
                    "stops.txt",
                    "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
                    "station-1,Fictional Exchange,-28.02,153.42,1\n"
                    "outside,Outside Stop,-30.0,153.42,0\n",
                )

            first_result = build_spatial_pack(
                mbtiles_path=mbtiles,
                boundary_path=boundary,
                gtfs_path=gtfs,
                output_path=first,
                pack_version="2026.08.test",
                produced_at="2026-08-07",
            )
            second_result = build_spatial_pack(
                mbtiles_path=mbtiles,
                boundary_path=boundary,
                gtfs_path=gtfs,
                output_path=second,
                pack_version="2026.08.test",
                produced_at="2026-08-07",
            )

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_result["sha256"], second_result["sha256"])
            self.assertEqual(first_result["search_features"], 1)
            preview = inspect_and_stage_spatial_pack(
                first.read_bytes(), root / "installed"
            )
            self.assertEqual(preview.search_feature_count, 1)
            self.assertEqual(list(preview.manifest.coverage_bbox), TEST_BOUNDS)

    def test_vector_geometry_decoder_tracks_delta_encoded_points(self) -> None:
        self.assertEqual(decode_geometry([9, 2, 4, 10, 2, 1]), [(1, 2), (2, 1)])


if __name__ == "__main__":
    unittest.main()
