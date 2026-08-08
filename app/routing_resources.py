"""Validated ignored local-routing capability configuration.

Routing engines and graphs are replaceable executable/derived resources.  This
module keeps their activation separate from canonical data and only permits the
exact Valhalla artifact already verified by the Phase 3 X1 evidence spike.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from app.journey_contract import JourneySource
from app.spatial_pack import spatial_pack_status


ROUTING_CAPABILITY_FORMAT = "project-e-local-routing"
ROUTING_CAPABILITY_SCHEMA_VERSION = 1
VALHALLA_PROVIDER_VERSION = "3.8.3"
VALHALLA_SERVICE_SHA256 = (
    "c5024ba8d68221382702008607dc0b15b77c919de5ca0924f52e591e6456addc"
)
VALHALLA_CONFIG_SHA256 = (
    "7df3f36d1747b3dfb555ec6e70c32e70a4c43ebb8188472e668886daef188017"
)
GOLD_COAST_GRAPH_SHA256 = (
    "816176149143d9cea01970148104d07992533482104c56990c16b42c3a58e44b"
)
GOLD_COAST_GRAPH_BYTES = 46_018_560
GOLD_COAST_COVERAGE_KEY = "au-qld-gold-coast-osm-buffer15km-2026.08.01"
GOLD_COAST_COVERAGE_BBOX = (
    153.016321,
    -28.399947,
    153.704379,
    -27.555653,
)
GOLD_COAST_SPATIAL_PACK = ("au-qld-gold-coast", "2026.08.01")
GOLD_COAST_MAXIMUM_SNAP_METRES = 100.0
WALKING_CACHE_MAXIMUM_ENTRIES = 128
WALKING_CACHE_FRESH_SECONDS = 86_400
REVIEWED_SOURCE_VALUES = (
    (
        "openstreetmap-geofabrik-queensland",
        "2026-08-01; data through 2026-08-01T10:46:22Z",
        "Static X1 graph source snapshot",
    ),
    (
        "valhalla-graph",
        "3.8.3; sha256:816176149143d9cea01970148104d07992533482104c56990c16b42c3a58e44b",
        "Immutable local derived graph",
    ),
)
ACTIVE_ROUTING_FILE = "active.json"


@dataclass(frozen=True)
class LocalValhallaCapability:
    base_url: str
    provider_version: str
    service_binary: Path
    service_config: Path
    service_binary_sha256: str
    service_config_sha256: str
    graph_path: Path
    graph_sha256: str
    graph_bytes: int
    coverage_key: str
    coverage_bbox: tuple[float, float, float, float]
    coverage_timezone: str
    maximum_snap_distance_metres: float
    compatible_spatial_pack_id: str
    compatible_spatial_pack_version: str
    maximum_cache_entries: int
    cache_fresh_seconds: int
    sources: tuple[JourneySource, ...]

    @property
    def adapter_version(self) -> str:
        return f"valhalla-{self.provider_version}-project-e-walk-v1"


@dataclass(frozen=True)
class RoutingCapabilityStatus:
    state: str
    explanation: str
    capability: LocalValhallaCapability | None = None


def routing_capability_status(
    routing_root: Path,
    spatial_pack_root: Path,
) -> RoutingCapabilityStatus:
    path = Path(routing_root) / ACTIVE_ROUTING_FILE
    if not path.is_file():
        return RoutingCapabilityStatus(
            "unavailable",
            "No local walking-routing capability is activated. Map and canonical Locations remain available.",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        capability = _parse_capability(value, verify_files=False)
        _validate_spatial_pack_compatibility(capability, spatial_pack_root)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        return RoutingCapabilityStatus(
            "error",
            f"The active local walking-routing capability is invalid: {error}",
        )
    return RoutingCapabilityStatus(
        "available",
        (
            f"Valhalla {capability.provider_version} is configured as a local-only "
            f"walking calculator for {capability.coverage_key}."
        ),
        capability,
    )


def load_active_valhalla_capability(
    routing_root: Path,
    spatial_pack_root: Path,
) -> LocalValhallaCapability:
    status = routing_capability_status(routing_root, spatial_pack_root)
    if status.capability is None:
        raise ValueError(status.explanation)
    return status.capability


def activate_local_valhalla_capability(
    manifest_path: Path,
    routing_root: Path,
    spatial_pack_root: Path,
) -> LocalValhallaCapability:
    """Verify and atomically activate one exact local Valhalla declaration."""
    manifest_path = Path(manifest_path)
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Routing capability manifest could not be read: {error}") from error
    capability = _parse_capability(value, verify_files=True)
    _validate_spatial_pack_compatibility(capability, spatial_pack_root)
    root = Path(routing_root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / ACTIVE_ROUTING_FILE
    temporary = root / f".{ACTIVE_ROUTING_FILE}.tmp"
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return capability


def verify_local_valhalla_resources(capability: LocalValhallaCapability) -> None:
    """Recheck ignored executable/config/graph bytes before a local launch."""
    _verify_resource(
        capability.service_binary,
        capability.service_binary_sha256,
        "Routing service executable",
    )
    _verify_resource(
        capability.service_config,
        capability.service_config_sha256,
        "Routing service config",
    )
    _verify_resource(
        capability.graph_path,
        capability.graph_sha256,
        "Routing graph",
    )
    if capability.graph_path.stat().st_size != capability.graph_bytes:
        raise ValueError("Routing graph byte count does not match its manifest.")
    _validate_valhalla_config(capability)


def _parse_capability(
    value: Mapping[str, Any],
    *,
    verify_files: bool,
) -> LocalValhallaCapability:
    if not isinstance(value, Mapping):
        raise ValueError("Routing capability manifest must be a JSON object.")
    if value.get("format") != ROUTING_CAPABILITY_FORMAT:
        raise ValueError("Routing capability format is unsupported.")
    if value.get("schema_version") != ROUTING_CAPABILITY_SCHEMA_VERSION:
        raise ValueError("Routing capability schema version is unsupported.")
    if value.get("provider") != "valhalla":
        raise ValueError("Only the reviewed Valhalla walking provider is supported.")
    if value.get("execution") != "local-subprocess":
        raise ValueError("Routing execution must be the reviewed local subprocess boundary.")
    provider_version = _required_text(value.get("provider_version"), "Provider version")
    if provider_version != VALHALLA_PROVIDER_VERSION:
        raise ValueError("Routing provider version has not been reviewed for this adapter.")

    base_url = _normalise_loopback_url(value.get("base_url"))
    service = _required_mapping(value.get("service"), "Service")
    graph = _required_mapping(value.get("graph"), "Graph")
    coverage = _required_mapping(value.get("coverage"), "Coverage")
    compatibility = _required_mapping(
        value.get("compatible_spatial_pack"), "Compatible spatial pack"
    )
    cache = _required_mapping(value.get("cache"), "Cache")
    service_binary = _absolute_file_path(service.get("binary"), "Service binary")
    service_config = _absolute_file_path(service.get("config"), "Service config")
    graph_path = _absolute_file_path(graph.get("path"), "Routing graph")
    binary_sha = _sha256_text(service.get("binary_sha256"), "Service binary SHA-256")
    config_sha = _sha256_text(service.get("config_sha256"), "Service config SHA-256")
    graph_sha = _sha256_text(graph.get("sha256"), "Routing graph SHA-256")
    graph_bytes = _bounded_int(graph.get("bytes"), "Routing graph bytes", 1, 2_000_000_000)
    if binary_sha != VALHALLA_SERVICE_SHA256:
        raise ValueError("Routing service executable is not the reviewed Valhalla artifact.")
    if config_sha != VALHALLA_CONFIG_SHA256:
        raise ValueError("Routing service config is not the reviewed Valhalla configuration.")
    if graph_sha != GOLD_COAST_GRAPH_SHA256 or graph_bytes != GOLD_COAST_GRAPH_BYTES:
        raise ValueError("Routing graph is not the reviewed Gold Coast artifact.")

    bbox_value = coverage.get("bbox")
    if not isinstance(bbox_value, list) or len(bbox_value) != 4:
        raise ValueError("Routing coverage bbox must contain west, south, east and north.")
    try:
        west, south, east, north = (float(item) for item in bbox_value)
    except (TypeError, ValueError) as error:
        raise ValueError("Routing coverage bbox must contain finite coordinates.") from error
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Routing coverage bbox is invalid.")
    maximum_snap = _bounded_float(
        coverage.get("maximum_snap_distance_metres"),
        "Maximum snap distance",
        1,
        500,
    )

    raw_sources = value.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("Routing sources must be a non-empty list.")
    sources: list[JourneySource] = []
    for raw_source in raw_sources:
        source = _required_mapping(raw_source, "Routing source")
        sources.append(
            JourneySource(
                source_key=_required_text(source.get("key"), "Routing source key"),
                version=_required_text(source.get("version"), "Routing source version"),
                freshness=_required_text(
                    source.get("freshness"), "Routing source freshness"
                ),
            )
        )
    if len({source.source_key for source in sources}) != len(sources):
        raise ValueError("Routing source keys must be unique.")

    capability = LocalValhallaCapability(
        base_url=base_url,
        provider_version=provider_version,
        service_binary=service_binary,
        service_config=service_config,
        service_binary_sha256=binary_sha,
        service_config_sha256=config_sha,
        graph_path=graph_path,
        graph_sha256=graph_sha,
        graph_bytes=graph_bytes,
        coverage_key=_required_text(coverage.get("key"), "Coverage key"),
        coverage_bbox=(west, south, east, north),
        coverage_timezone=_required_text(coverage.get("timezone"), "Coverage timezone"),
        maximum_snap_distance_metres=maximum_snap,
        compatible_spatial_pack_id=_required_text(
            compatibility.get("pack_id"), "Compatible spatial-pack ID"
        ),
        compatible_spatial_pack_version=_required_text(
            compatibility.get("pack_version"), "Compatible spatial-pack version"
        ),
        maximum_cache_entries=_bounded_int(
            cache.get("maximum_entries"), "Cache maximum entries", 1, 10_000
        ),
        cache_fresh_seconds=_bounded_int(
            cache.get("fresh_seconds"), "Cache freshness", 60, 31_536_000
        ),
        sources=tuple(sources),
    )
    if (
        capability.coverage_key != GOLD_COAST_COVERAGE_KEY
        or capability.coverage_bbox != GOLD_COAST_COVERAGE_BBOX
        or capability.coverage_timezone != "Australia/Brisbane"
        or capability.maximum_snap_distance_metres
        != GOLD_COAST_MAXIMUM_SNAP_METRES
        or (
            capability.compatible_spatial_pack_id,
            capability.compatible_spatial_pack_version,
        )
        != GOLD_COAST_SPATIAL_PACK
    ):
        raise ValueError("Routing coverage is not the reviewed Gold Coast declaration.")
    if (
        capability.maximum_cache_entries != WALKING_CACHE_MAXIMUM_ENTRIES
        or capability.cache_fresh_seconds != WALKING_CACHE_FRESH_SECONDS
    ):
        raise ValueError("Routing cache bounds are not the reviewed N6 values.")
    if tuple(
        (source.source_key, source.version, source.freshness)
        for source in capability.sources
    ) != REVIEWED_SOURCE_VALUES:
        raise ValueError("Routing source provenance is not the reviewed X1 declaration.")
    if verify_files:
        verify_local_valhalla_resources(capability)
    return capability


def _validate_spatial_pack_compatibility(
    capability: LocalValhallaCapability,
    spatial_pack_root: Path,
) -> None:
    active = spatial_pack_status(spatial_pack_root).active
    if active is None:
        raise ValueError("A compatible active Spatial Pack is required for walking routes.")
    if (
        active.manifest.pack_id != capability.compatible_spatial_pack_id
        or active.manifest.pack_version != capability.compatible_spatial_pack_version
    ):
        raise ValueError(
            "The active Spatial Pack does not match the reviewed routing source snapshot."
        )


def _validate_valhalla_config(capability: LocalValhallaCapability) -> None:
    try:
        config = json.loads(capability.service_config.read_text(encoding="utf-8"))
        tile_extract = Path(config["mjolnir"]["tile_extract"]).resolve()
        listen = str(config["httpd"]["service"]["listen"])
        actions = set(config["loki"]["actions"])
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        raise ValueError("Valhalla service config is incomplete or invalid.") from error
    if tile_extract != capability.graph_path.resolve():
        raise ValueError("Valhalla service config does not reference the declared graph.")
    parsed = urlparse(capability.base_url)
    expected_listen = f"tcp://127.0.0.1:{parsed.port}"
    if listen != expected_listen:
        raise ValueError("Valhalla service config is not bound to the declared loopback port.")
    if not {"route", "locate", "status"} <= actions:
        raise ValueError("Valhalla service config lacks required walking actions.")


def _verify_resource(path: Path, expected_sha: str, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} does not exist.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha:
        raise ValueError(f"{label} SHA-256 does not match its manifest.")


def _normalise_loopback_url(value: object) -> str:
    text = _required_text(value, "Routing base URL").rstrip("/")
    parsed = urlparse(text)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port is None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Routing base URL must be an explicit 127.0.0.1 HTTP port.")
    return f"http://127.0.0.1:{parsed.port}"


def _absolute_file_path(value: object, label: str) -> Path:
    path = Path(_required_text(value, label))
    if not path.is_absolute():
        raise ValueError(f"{label} must be an absolute path.")
    return path.resolve()


def _required_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required.")
    return value.strip()


def _sha256_text(value: object, label: str) -> str:
    text = _required_text(value, label).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest.")
    return text


def _bounded_int(value: object, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return value


def _bounded_float(value: object, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number.")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return number
