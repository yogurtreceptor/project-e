import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.spatial_pack import (
    activate_staged_spatial_pack,
    inspect_and_stage_spatial_pack,
    map_pack_payload,
    read_active_coverage,
    read_active_public_transport,
    read_active_tile,
    remove_spatial_pack,
    rollback_spatial_pack,
    search_active_spatial_pack,
    spatial_pack_status,
)
from tests.spatial_pack_test_support import fictional_spatial_pack, rewrite_bundle


class SpatialPackLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name) / "packs"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def stage_and_activate(self, version: str = "2026.08.01"):
        preview = inspect_and_stage_spatial_pack(
            fictional_spatial_pack(version), self.root
        )
        return preview, activate_staged_spatial_pack(preview.token, self.root)

    def test_inspect_activate_search_and_serve_local_resources(self) -> None:
        preview, active = self.stage_and_activate()

        self.assertEqual(preview.tile_count, 1)
        self.assertEqual(preview.search_feature_count, 3)
        self.assertEqual(active.manifest.pack_version, "2026.08.01")
        status = spatial_pack_status(self.root)
        self.assertEqual(status.active.activation_id, active.activation_id)
        self.assertEqual(len(status.installed), 1)
        self.assertEqual(
            search_active_spatial_pack(self.root, "Surfers")[0]["title"],
            "Surfers Paradise",
        )
        tile, gzipped = read_active_tile(self.root, active.activation_id, 0, 0, 0)
        self.assertTrue(gzipped)
        self.assertTrue(tile.startswith(b"\x1f\x8b"))
        self.assertEqual(
            read_active_tile(self.root, active.activation_id, 1, 0, 0),
            (b"", False),
        )
        coverage = json.loads(
            read_active_coverage(self.root, active.activation_id)
        )
        self.assertEqual(coverage["type"], "FeatureCollection")
        transit = json.loads(
            read_active_public_transport(self.root, active.activation_id)
        )
        self.assertEqual(len(transit["features"]), 2)
        self.assertEqual(
            transit["features"][0]["properties"]["name"],
            "Broadbeach South station",
        )
        self.assertEqual(
            len(search_active_spatial_pack(self.root, "Broadbeach")), 1
        )
        payload = map_pack_payload(self.root)
        self.assertEqual(payload["state"], "available")
        self.assertIn(active.activation_id, payload["tileUrl"])
        self.assertIn("public-transport.geojson", payload["publicTransportUrl"])

    def test_update_rollback_and_remove_keep_versions_coherent(self) -> None:
        _first_preview, first = self.stage_and_activate("2026.08.01")
        _second_preview, second = self.stage_and_activate("2026.08.02")
        self.assertNotEqual(first.activation_id, second.activation_id)
        self.assertTrue(spatial_pack_status(self.root).rollback_available)

        rolled_back = rollback_spatial_pack(self.root)
        self.assertEqual(rolled_back.manifest.pack_version, "2026.08.01")
        self.assertTrue(spatial_pack_status(self.root).rollback_available)

        removed = remove_spatial_pack(self.root)
        self.assertEqual(removed["versions"], 2)
        self.assertIsNone(spatial_pack_status(self.root).active)
        self.assertEqual(spatial_pack_status(self.root).installed, ())

    def test_failed_update_does_not_replace_last_known_good_pointer(self) -> None:
        _preview, first = self.stage_and_activate("2026.08.01")
        second_preview = inspect_and_stage_spatial_pack(
            fictional_spatial_pack("2026.08.02"), self.root
        )

        with patch(
            "app.spatial_pack._write_json_atomic",
            side_effect=OSError("simulated pointer failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated pointer failure"):
                activate_staged_spatial_pack(second_preview.token, self.root)

        status = spatial_pack_status(self.root)
        self.assertEqual(status.active.activation_id, first.activation_id)
        self.assertEqual(status.active.manifest.pack_version, "2026.08.01")
        self.assertEqual(len(status.installed), 2)

    def test_checksum_failure_is_rejected_before_active_state_changes(self) -> None:
        _preview, active = self.stage_and_activate()
        damaged = rewrite_bundle(
            fictional_spatial_pack("2026.08.02"),
            lambda values: values.__setitem__(
                "basemap.mbtiles", values["basemap.mbtiles"] + b"damage"
            ),
        )

        with self.assertRaisesRegex(ValueError, "size does not match"):
            inspect_and_stage_spatial_pack(damaged, self.root)

        def invalidate_production_date(values):
            manifest = json.loads(values["manifest.json"])
            manifest["produced_at"] = "sometime recently"
            values["manifest.json"] = json.dumps(manifest).encode()

        invalid_date = rewrite_bundle(
            fictional_spatial_pack("2026.08.02"), invalidate_production_date
        )
        with self.assertRaisesRegex(ValueError, "production date"):
            inspect_and_stage_spatial_pack(invalid_date, self.root)

        self.assertEqual(
            spatial_pack_status(self.root).active.activation_id,
            active.activation_id,
        )

    def test_different_region_requires_explicit_removal(self) -> None:
        self.stage_and_activate()
        preview = inspect_and_stage_spatial_pack(
            fictional_spatial_pack(
                pack_id="au-qld-other-region", title="Other Region local map"
            ),
            self.root,
        )
        with self.assertRaisesRegex(ValueError, "supports one region pack"):
            activate_staged_spatial_pack(preview.token, self.root)

    def test_insufficient_staging_space_is_reported_without_extraction(self) -> None:
        usage = shutil._ntuple_diskusage(total=100, used=99, free=1)
        with patch("app.spatial_pack.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(ValueError, "Insufficient disk space"):
                inspect_and_stage_spatial_pack(fictional_spatial_pack(), self.root)
        self.assertIsNone(spatial_pack_status(self.root).active)

    def test_archive_path_traversal_is_rejected(self) -> None:
        bundle = rewrite_bundle(
            fictional_spatial_pack(),
            lambda values: values.__setitem__("../outside.txt", b"no"),
        )
        with self.assertRaisesRegex(ValueError, "unsafe file path"):
            inspect_and_stage_spatial_pack(bundle, self.root)
        self.assertFalse((self.root.parent / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
