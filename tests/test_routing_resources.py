import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from app.routing_resources import (
    GOLD_COAST_COVERAGE_BBOX,
    GOLD_COAST_COVERAGE_KEY,
    GOLD_COAST_GRAPH_BYTES,
    GOLD_COAST_GRAPH_SHA256,
    GOLD_COAST_MAXIMUM_SNAP_METRES,
    REVIEWED_SOURCE_VALUES,
    VALHALLA_CONFIG_SHA256,
    VALHALLA_PROVIDER_VERSION,
    VALHALLA_SERVICE_SHA256,
    WALKING_CACHE_FRESH_SECONDS,
    WALKING_CACHE_MAXIMUM_ENTRIES,
    routing_capability_status,
)


class RoutingResourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.routing_root = self.root / "routing"
        self.routing_root.mkdir()
        self.spatial_root = self.root / "packs"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def manifest(self) -> dict[str, object]:
        return {
            "format": "project-e-local-routing",
            "schema_version": 1,
            "provider": "valhalla",
            "provider_version": VALHALLA_PROVIDER_VERSION,
            "execution": "local-subprocess",
            "base_url": "http://127.0.0.1:18081",
            "service": {
                "binary": str(self.root / "valhalla_service"),
                "binary_sha256": VALHALLA_SERVICE_SHA256,
                "config": str(self.root / "valhalla.json"),
                "config_sha256": VALHALLA_CONFIG_SHA256,
            },
            "graph": {
                "path": str(self.root / "tiles.tar"),
                "sha256": GOLD_COAST_GRAPH_SHA256,
                "bytes": GOLD_COAST_GRAPH_BYTES,
            },
            "coverage": {
                "key": GOLD_COAST_COVERAGE_KEY,
                "bbox": list(GOLD_COAST_COVERAGE_BBOX),
                "timezone": "Australia/Brisbane",
                "maximum_snap_distance_metres": GOLD_COAST_MAXIMUM_SNAP_METRES,
            },
            "compatible_spatial_pack": {
                "pack_id": "au-qld-gold-coast",
                "pack_version": "2026.08.01",
            },
            "cache": {
                "maximum_entries": WALKING_CACHE_MAXIMUM_ENTRIES,
                "fresh_seconds": WALKING_CACHE_FRESH_SECONDS,
            },
            "sources": [
                {"key": key, "version": version, "freshness": freshness}
                for key, version, freshness in REVIEWED_SOURCE_VALUES
            ],
        }

    @staticmethod
    def active_pack(pack_id="au-qld-gold-coast", version="2026.08.01"):
        return SimpleNamespace(
            active=SimpleNamespace(
                manifest=SimpleNamespace(pack_id=pack_id, pack_version=version)
            )
        )

    def write_active(self, value: dict[str, object]) -> None:
        (self.routing_root / "active.json").write_text(
            json.dumps(value), encoding="utf-8"
        )

    def test_missing_activation_is_honestly_unavailable(self) -> None:
        status = routing_capability_status(self.routing_root, self.spatial_root)

        self.assertEqual("unavailable", status.state)
        self.assertIsNone(status.capability)

    def test_exact_reviewed_declaration_and_matching_pack_are_available(self) -> None:
        self.write_active(self.manifest())
        with patch(
            "app.routing_resources.spatial_pack_status",
            return_value=self.active_pack(),
        ):
            status = routing_capability_status(self.routing_root, self.spatial_root)

        self.assertEqual("available", status.state)
        self.assertEqual(GOLD_COAST_COVERAGE_KEY, status.capability.coverage_key)

    def test_edited_bounds_or_pack_version_cannot_expand_trust(self) -> None:
        value = self.manifest()
        value["coverage"]["maximum_snap_distance_metres"] = 101
        self.write_active(value)
        with patch(
            "app.routing_resources.spatial_pack_status",
            return_value=self.active_pack(),
        ):
            edited = routing_capability_status(
                self.routing_root, self.spatial_root
            )
        self.write_active(self.manifest())
        with patch(
            "app.routing_resources.spatial_pack_status",
            return_value=self.active_pack(version="2026.09.01"),
        ):
            mismatched = routing_capability_status(
                self.routing_root, self.spatial_root
            )

        self.assertEqual("error", edited.state)
        self.assertIn("reviewed Gold Coast declaration", edited.explanation)
        self.assertEqual("error", mismatched.state)
        self.assertIn("does not match", mismatched.explanation)


if __name__ == "__main__":
    unittest.main()
