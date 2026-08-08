"""Activate the exact local Valhalla resources reviewed by the X1 evidence spike."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

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
    activate_local_valhalla_capability,
)
from app.spatial_pack import spatial_pack_status


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "instance" / "spatial-evidence"
BUILD_ROOT = EVIDENCE_ROOT / "builds" / "valhalla-v3.8.3"
SERVICE_BINARY = (
    EVIDENCE_ROOT
    / "tools"
    / "valhalla-venv"
    / "lib"
    / "python3.12"
    / "site-packages"
    / "valhalla"
    / "bin"
    / "valhalla_service"
)
SERVICE_CONFIG = BUILD_ROOT / "valhalla.json"
GRAPH_PATH = BUILD_ROOT / "valhalla_tiles.tar"


def reviewed_manifest(spatial_pack_root: Path) -> dict[str, object]:
    active_pack = spatial_pack_status(spatial_pack_root).active
    if active_pack is None:
        raise ValueError("Activate the reviewed Gold Coast Spatial Pack first.")
    manifest = active_pack.manifest
    if (
        manifest.pack_id != "au-qld-gold-coast"
        or manifest.pack_version != "2026.08.01"
        or manifest.coverage_bbox
        != GOLD_COAST_COVERAGE_BBOX
    ):
        raise ValueError(
            "The active Spatial Pack is not the snapshot reviewed with the X1 graph."
        )
    return {
        "format": "project-e-local-routing",
        "schema_version": 1,
        "provider": "valhalla",
        "provider_version": VALHALLA_PROVIDER_VERSION,
        "execution": "local-subprocess",
        "base_url": "http://127.0.0.1:18081",
        "service": {
            "binary": str(SERVICE_BINARY),
            "binary_sha256": VALHALLA_SERVICE_SHA256,
            "config": str(SERVICE_CONFIG),
            "config_sha256": VALHALLA_CONFIG_SHA256,
        },
        "graph": {
            "path": str(GRAPH_PATH),
            "sha256": GOLD_COAST_GRAPH_SHA256,
            "bytes": GOLD_COAST_GRAPH_BYTES,
        },
        "coverage": {
            "key": GOLD_COAST_COVERAGE_KEY,
            "bbox": list(manifest.coverage_bbox),
            "timezone": "Australia/Brisbane",
            "maximum_snap_distance_metres": GOLD_COAST_MAXIMUM_SNAP_METRES,
        },
        "compatible_spatial_pack": {
            "pack_id": manifest.pack_id,
            "pack_version": manifest.pack_version,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify and activate the reviewed X1 local walking router."
    )
    parser.add_argument(
        "--routing-root", type=Path, default=ROOT / "instance" / "routing"
    )
    parser.add_argument(
        "--spatial-pack-root", type=Path, default=ROOT / "instance" / "spatial-packs"
    )
    arguments = parser.parse_args()
    value = reviewed_manifest(arguments.spatial_pack_root)
    with tempfile.TemporaryDirectory(prefix="project-e-routing-activation-") as directory:
        candidate = Path(directory) / "routing.json"
        candidate.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        capability = activate_local_valhalla_capability(
            candidate, arguments.routing_root, arguments.spatial_pack_root
        )
    print(
        json.dumps(
            {
                "provider": f"Valhalla {capability.provider_version}",
                "execution": "local-subprocess",
                "coverage": capability.coverage_key,
                "graph_bytes": capability.graph_bytes,
                "maximum_snap_distance_metres": capability.maximum_snap_distance_metres,
                "cache_maximum_entries": capability.maximum_cache_entries,
                "cache_fresh_seconds": capability.cache_fresh_seconds,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
