"""Verified local spatial-pack lifecycle outside canonical Project E data."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import sqlite3
import time
import uuid
import zipfile
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


FORMAT_NAME = "project-e-spatial-pack"
FORMAT_VERSION = 1
SEARCH_APPLICATION_ID = 0x50455331
SEARCH_USER_VERSION = 1
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
STAGING_TTL_SECONDS = 30 * 60
PACK_MEMBERS = frozenset(
    {"basemap.mbtiles", "search.sqlite3", "coverage.geojson"}
)
PACK_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ACTIVATION_PATTERN = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*--[A-Za-z0-9][A-Za-z0-9._-]{0,63}--[0-9a-f]{12}$"
)
TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class SpatialPackManifest:
    pack_id: str
    title: str
    pack_version: str
    produced_at: str
    coverage_label: str
    coverage_bbox: tuple[float, float, float, float]
    buffer_km: float
    minimum_zoom: int
    maximum_zoom: int
    context_layers: tuple[str, ...]
    sources: tuple[dict[str, str], ...]
    attributions: tuple[dict[str, str], ...]
    limitations: tuple[str, ...]
    members: dict[str, dict[str, object]]
    raw: dict[str, object]

    @property
    def attribution_text(self) -> str:
        return " · ".join(item["label"] for item in self.attributions)

    @property
    def source_summary(self) -> str:
        return " · ".join(
            f"{item['label']} {item['version']}" for item in self.sources
        )


@dataclass(frozen=True)
class SpatialPackPreview:
    token: str
    manifest: SpatialPackManifest
    archive_bytes: int
    unpacked_bytes: int
    tile_count: int
    search_feature_count: int


@dataclass(frozen=True)
class InstalledSpatialPack:
    activation_id: str
    directory: Path
    manifest: SpatialPackManifest
    activated_at: str
    previous_activation_id: str


@dataclass(frozen=True)
class SpatialPackStatus:
    active: InstalledSpatialPack | None
    installed: tuple[InstalledSpatialPack, ...]
    error: str = ""

    @property
    def rollback_available(self) -> bool:
        if self.active is None or not self.active.previous_activation_id:
            return False
        return any(
            item.activation_id == self.active.previous_activation_id
            for item in self.installed
        )


def spatial_pack_status(root: Path) -> SpatialPackStatus:
    root = Path(root)
    try:
        pointer = _read_active_pointer(root)
        installed = tuple(_installed_versions(root, pointer))
        if pointer is None:
            return SpatialPackStatus(None, installed)
        active = next(
            (
                item
                for item in installed
                if item.activation_id == pointer["activation_id"]
            ),
            None,
        )
        if active is None:
            raise ValueError(
                "The active spatial-pack pointer does not name an installed version."
            )
        return SpatialPackStatus(active, installed)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return SpatialPackStatus(None, (), str(error))


def inspect_and_stage_spatial_pack(bundle: bytes, root: Path) -> SpatialPackPreview:
    if not bundle:
        raise ValueError("Choose a spatial-pack ZIP file to inspect.")
    if len(bundle) > MAX_ARCHIVE_BYTES:
        raise ValueError("Spatial-pack ZIP exceeds the 512 MB inspection limit.")
    root = Path(root)
    staging_root = root / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    _prune_expired_staging(staging_root)
    token = uuid.uuid4().hex
    building = staging_root / f".{token}.building"
    staged = staging_root / token
    building.mkdir()
    try:
        manifest, unpacked_bytes = _extract_archive(bundle, building)
        tile_count = _validate_mbtiles(building / "basemap.mbtiles", manifest)
        search_feature_count = _validate_search_database(
            building / "search.sqlite3", manifest.coverage_bbox
        )
        _validate_coverage(building / "coverage.geojson", manifest.coverage_bbox)
        _write_json(building / "preview.json", {
            "archive_bytes": len(bundle),
            "unpacked_bytes": unpacked_bytes,
            "tile_count": tile_count,
            "search_feature_count": search_feature_count,
        })
        os.replace(building, staged)
        return SpatialPackPreview(
            token,
            manifest,
            len(bundle),
            unpacked_bytes,
            tile_count,
            search_feature_count,
        )
    except (zipfile.BadZipFile, RuntimeError) as error:
        if building.exists():
            shutil.rmtree(building)
        raise ValueError("Spatial-pack ZIP members could not be read safely.") from error
    except Exception:
        if building.exists():
            shutil.rmtree(building)
        raise


def read_staged_spatial_pack(token: str, root: Path) -> SpatialPackPreview:
    if not TOKEN_PATTERN.fullmatch(token):
        raise ValueError("Spatial-pack preview token is invalid.")
    staged = Path(root) / "staging" / token
    if not staged.is_dir() or time.time() - staged.stat().st_mtime > STAGING_TTL_SECONDS:
        if staged.is_dir():
            shutil.rmtree(staged)
        raise ValueError("Spatial-pack preview has expired or does not exist.")
    manifest = _read_manifest(staged / "manifest.json")
    _validate_staged_members(staged, manifest)
    tile_count = _validate_mbtiles(staged / "basemap.mbtiles", manifest)
    search_feature_count = _validate_search_database(
        staged / "search.sqlite3", manifest.coverage_bbox
    )
    _validate_coverage(staged / "coverage.geojson", manifest.coverage_bbox)
    try:
        preview = json.loads((staged / "preview.json").read_text(encoding="utf-8"))
        if not isinstance(preview, dict) or set(preview) != {
            "archive_bytes",
            "unpacked_bytes",
            "tile_count",
            "search_feature_count",
        }:
            raise ValueError
        archive_bytes = _positive_integer(preview["archive_bytes"])
        unpacked_bytes = _positive_integer(preview["unpacked_bytes"])
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise ValueError("Spatial-pack preview metadata is invalid.") from error
    return SpatialPackPreview(
        token,
        manifest,
        archive_bytes,
        unpacked_bytes,
        tile_count,
        search_feature_count,
    )


def activate_staged_spatial_pack(token: str, root: Path) -> InstalledSpatialPack:
    root = Path(root)
    preview = read_staged_spatial_pack(token, root)
    current = spatial_pack_status(root)
    if current.error:
        raise ValueError(f"Current spatial-pack state is invalid: {current.error}")
    if (
        current.active is not None
        and current.active.manifest.pack_id != preview.manifest.pack_id
    ):
        raise ValueError(
            "This first installed-region slice supports one region pack. Remove the "
            "active pack before installing a different region."
        )
    activation_id = _activation_id(preview.manifest)
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    target = versions / activation_id
    staged = root / "staging" / token
    (staged / "preview.json").unlink(missing_ok=True)
    if target.exists():
        _validate_staged_members(target, preview.manifest)
        shutil.rmtree(staged)
    else:
        os.replace(staged, target)
    previous = (
        current.active.activation_id
        if current.active is not None and current.active.activation_id != activation_id
        else current.active.previous_activation_id
        if current.active is not None
        else ""
    )
    activated_at = _utc_now()
    _write_json_atomic(
        root / "active.json",
        {
            "schema_version": 1,
            "activation_id": activation_id,
            "activated_at": activated_at,
            "previous_activation_id": previous,
        },
    )
    return InstalledSpatialPack(
        activation_id, target, preview.manifest, activated_at, previous
    )


def rollback_spatial_pack(root: Path) -> InstalledSpatialPack:
    root = Path(root)
    status = spatial_pack_status(root)
    if status.error:
        raise ValueError(f"Current spatial-pack state is invalid: {status.error}")
    if status.active is None or not status.rollback_available:
        raise ValueError("No validated previous spatial-pack version is available.")
    previous = next(
        item
        for item in status.installed
        if item.activation_id == status.active.previous_activation_id
    )
    activated_at = _utc_now()
    _write_json_atomic(
        root / "active.json",
        {
            "schema_version": 1,
            "activation_id": previous.activation_id,
            "activated_at": activated_at,
            "previous_activation_id": status.active.activation_id,
        },
    )
    return InstalledSpatialPack(
        previous.activation_id,
        previous.directory,
        previous.manifest,
        activated_at,
        status.active.activation_id,
    )


def remove_spatial_pack(root: Path) -> dict[str, object]:
    root = Path(root)
    status = spatial_pack_status(root)
    if status.error:
        raise ValueError(f"Current spatial-pack state is invalid: {status.error}")
    if status.active is None:
        raise ValueError("No spatial pack is installed.")
    pack_id = status.active.manifest.pack_id
    removed_versions = [
        item for item in status.installed if item.manifest.pack_id == pack_id
    ]
    removed_bytes = sum(_tree_bytes(item.directory) for item in removed_versions)
    pointer = root / "active.json"
    if pointer.exists():
        pointer.unlink()
    for item in removed_versions:
        _safe_version_directory(root, item.activation_id)
        if item.directory.exists():
            shutil.rmtree(item.directory)
    return {
        "pack_id": pack_id,
        "title": status.active.manifest.title,
        "versions": len(removed_versions),
        "bytes": removed_bytes,
    }


def search_active_spatial_pack(
    root: Path, query: str, *, limit: int = 10
) -> list[dict[str, object]]:
    query = query.strip()
    if not query:
        return []
    status = spatial_pack_status(root)
    if status.active is None:
        return []
    database = status.active.directory / "search.sqlite3"
    uri = f"file:{database.resolve()}?mode=ro"
    escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    contains = f"%{escaped}%"
    prefix = f"{escaped}%"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        rows = connection.execute(
            """SELECT feature_id, title, subtitle, feature_type, source_layer,
                      latitude, longitude,
                      CASE
                        WHEN lower(title)=? THEN 0
                        WHEN lower(title) LIKE ? ESCAPE '\\' THEN 1
                        WHEN lower(title) LIKE ? ESCAPE '\\' THEN 2
                        ELSE 3
                      END AS match_rank
                 FROM search_features
                WHERE lower(search_text) LIKE ? ESCAPE '\\'
                ORDER BY match_rank, lower(title), feature_id
                LIMIT ?""",
            (
                query.casefold(),
                prefix,
                contains,
                contains,
                max(20, min(limit * 8, 200)),
            ),
        ).fetchall()
    manifest = status.active.manifest
    results = []
    seen = set()
    for row in rows:
        presentation_key = row["title"].casefold()
        if presentation_key in seen:
            continue
        seen.add(presentation_key)
        results.append({
            "feature_id": row["feature_id"],
            "title": row["title"],
            "subtitle": row["subtitle"],
            "feature_type": row["feature_type"],
            "source_layer": row["source_layer"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "source_label": f"{manifest.title} {manifest.pack_version} · Local",
            "coverage_label": manifest.coverage_label,
            "pack_id": manifest.pack_id,
            "pack_version": manifest.pack_version,
        })
        if len(results) >= max(1, min(limit, 50)):
            break
    return results


def read_active_search_feature(
    root: Path, provider_key: str, feature_id: str
) -> dict[str, object] | None:
    """Resolve one portable membership against the current replaceable index."""
    status = spatial_pack_status(root)
    if status.active is None:
        return None
    manifest = status.active.manifest
    if provider_key != f"spatial-pack:{manifest.pack_id}":
        return None
    database = status.active.directory / "search.sqlite3"
    uri = f"file:{database.resolve()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            row = connection.execute(
                """SELECT feature_id, title, subtitle, feature_type, source_layer,
                          latitude, longitude
                     FROM search_features WHERE feature_id=?""",
                (feature_id,),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return {
        "feature_id": row["feature_id"],
        "title": row["title"],
        "subtitle": row["subtitle"],
        "feature_type": row["feature_type"],
        "source_layer": row["source_layer"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "pack_id": manifest.pack_id,
        "pack_version": manifest.pack_version,
        "source_label": f"{manifest.title} {manifest.pack_version} · Local",
        "coverage_label": manifest.coverage_label,
    }


def read_active_tile(
    root: Path, activation_id: str, zoom: int, x: int, y: int
) -> tuple[bytes, bool] | None:
    active = _active_for_request(root, activation_id)
    if active is None or not _valid_tile_coordinate(zoom, x, y):
        return None
    tms_y = (2**zoom - 1) - y
    database = active.directory / "basemap.mbtiles"
    uri = f"file:{database.resolve()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            row = connection.execute(
                "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                (zoom, x, tms_y),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return b"", False
    content = bytes(row[0])
    return content, content.startswith(b"\x1f\x8b")


def read_active_coverage(root: Path, activation_id: str) -> bytes | None:
    active = _active_for_request(root, activation_id)
    if active is None:
        return None
    try:
        return (active.directory / "coverage.geojson").read_bytes()
    except OSError:
        return None


def read_active_public_transport(root: Path, activation_id: str) -> bytes | None:
    active = _active_for_request(root, activation_id)
    if active is None:
        return None
    database = active.directory / "search.sqlite3"
    uri = f"file:{database.resolve()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            rows = connection.execute(
                """SELECT feature_id, title, subtitle, feature_type,
                          latitude, longitude
                     FROM search_features
                    WHERE source_layer='public_transport'
                    ORDER BY feature_id"""
            ).fetchall()
    except sqlite3.Error:
        return None
    content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": row[0],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row[5], row[4]],
                },
                "properties": {
                    "feature_id": row[0],
                    "name": row[1],
                    "subtitle": row[2],
                    "feature_type": row[3],
                    "source_layer": "public_transport",
                },
            }
            for row in rows
        ],
    }
    return json.dumps(content, separators=(",", ":")).encode("utf-8")


def map_pack_payload(root: Path) -> dict[str, object]:
    status = spatial_pack_status(root)
    if status.active is None:
        return {
            "state": "error" if status.error else "unavailable",
            "error": status.error,
            "manageUrl": "/map/packs",
        }
    active = status.active
    manifest = active.manifest
    return {
        "state": "available",
        "manageUrl": "/map/packs",
        "activationId": active.activation_id,
        "packId": manifest.pack_id,
        "title": manifest.title,
        "version": manifest.pack_version,
        "producedAt": manifest.produced_at,
        "coverageLabel": manifest.coverage_label,
        "coverageBbox": list(manifest.coverage_bbox),
        "minimumZoom": manifest.minimum_zoom,
        "maximumZoom": manifest.maximum_zoom,
        "tileUrl": f"/map/tiles/{active.activation_id}/{{z}}/{{x}}/{{y}}.pbf",
        "coverageUrl": f"/map/packs/{active.activation_id}/coverage.geojson",
        "publicTransportUrl": (
            f"/map/packs/{active.activation_id}/public-transport.geojson"
        ),
        "contextLayers": list(manifest.context_layers),
        "attribution": manifest.attribution_text,
        "sourceSummary": manifest.source_summary,
        "limitations": list(manifest.limitations),
    }


def _extract_archive(
    bundle: bytes, directory: Path
) -> tuple[SpatialPackManifest, int]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(bundle))
    except zipfile.BadZipFile as error:
        raise ValueError("Spatial pack is not a valid ZIP archive.") from error
    with archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(infos) != len(set(names)):
            raise ValueError("Spatial pack contains duplicate member names.")
        if any(_unsafe_member(item) for item in infos):
            raise ValueError("Spatial pack contains an unsafe file path or link.")
        if set(names) != {"manifest.json", *PACK_MEMBERS}:
            raise ValueError("Spatial pack contains missing or unsupported members.")
        manifest_info = archive.getinfo("manifest.json")
        if manifest_info.file_size > MAX_MANIFEST_BYTES:
            raise ValueError("Spatial-pack manifest exceeds 256 KB.")
        unpacked_bytes = sum(item.file_size for item in infos)
        if unpacked_bytes > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Spatial pack exceeds the 2 GiB extracted safety limit.")
        _ensure_free_space(directory.parent, unpacked_bytes)
        try:
            manifest = _manifest_from_value(json.loads(archive.read("manifest.json")))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Spatial-pack manifest is invalid JSON.") from error
        if set(manifest.members) != PACK_MEMBERS:
            raise ValueError("Spatial-pack member list does not match its format.")
        for info in infos:
            if info.filename == "manifest.json":
                continue
            definition = manifest.members[info.filename]
            if info.file_size != definition["bytes"]:
                raise ValueError(
                    f"Spatial-pack size does not match for {info.filename}."
                )
            digest = hashlib.sha256()
            target = directory / info.filename
            with archive.open(info) as source, target.open("wb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    output.write(chunk)
            if digest.hexdigest() != definition["sha256"]:
                raise ValueError(
                    f"Spatial-pack checksum failed for {info.filename}."
                )
        (directory / "manifest.json").write_text(
            json.dumps(manifest.raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return manifest, unpacked_bytes


def _manifest_from_value(value: object) -> SpatialPackManifest:
    if not isinstance(value, dict):
        raise ValueError("Spatial-pack manifest must be a JSON object.")
    required = {
        "format",
        "schema_version",
        "pack_id",
        "title",
        "pack_version",
        "produced_at",
        "coverage",
        "capabilities",
        "sources",
        "attribution",
        "limitations",
        "members",
    }
    if set(value) != required:
        raise ValueError("Spatial-pack manifest fields do not match schema version 1.")
    if value["format"] != FORMAT_NAME or value["schema_version"] != FORMAT_VERSION:
        raise ValueError("Spatial-pack format or schema version is unsupported.")
    pack_id = _text(value["pack_id"], "pack ID", maximum=64)
    if not PACK_ID_PATTERN.fullmatch(pack_id):
        raise ValueError("Spatial-pack ID must be lowercase words joined by hyphens.")
    title = _text(value["title"], "title", maximum=120)
    pack_version = _text(value["pack_version"], "version", maximum=64)
    if not VERSION_PATTERN.fullmatch(pack_version):
        raise ValueError("Spatial-pack version is invalid.")
    produced_at = _production_date(value["produced_at"])
    coverage = value["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != {
        "label",
        "bbox",
        "buffer_km",
        "boundary_member",
    }:
        raise ValueError("Spatial-pack coverage definition is invalid.")
    coverage_label = _text(coverage["label"], "coverage label", maximum=160)
    bbox = _bbox(coverage["bbox"])
    buffer_km = _number(coverage["buffer_km"], "coverage buffer")
    if not 0 <= buffer_km <= 500:
        raise ValueError("Spatial-pack coverage buffer is invalid.")
    if coverage["boundary_member"] != "coverage.geojson":
        raise ValueError("Spatial-pack coverage member is unsupported.")
    capabilities = value["capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != {
        "basemap",
        "search",
        "context_layers",
    }:
        raise ValueError("Spatial-pack capabilities are invalid.")
    basemap = capabilities["basemap"]
    if not isinstance(basemap, dict) or set(basemap) != {
        "format",
        "member",
        "profile",
        "minimum_zoom",
        "maximum_zoom",
    }:
        raise ValueError("Spatial-pack basemap capability is unsupported.")
    if (
        basemap["format"] != "mvt-mbtiles"
        or basemap["member"] != "basemap.mbtiles"
        or basemap["profile"] != "project-e-openmaptiles-v1"
    ):
        raise ValueError("Spatial-pack basemap capability is unsupported.")
    minimum_zoom = _integer(basemap["minimum_zoom"], "minimum zoom")
    maximum_zoom = _integer(basemap["maximum_zoom"], "maximum zoom")
    if not 0 <= minimum_zoom <= maximum_zoom <= 18:
        raise ValueError("Spatial-pack zoom range is invalid.")
    search = capabilities["search"]
    if search != {
        "format": "project-e-search-sqlite-v1",
        "member": "search.sqlite3",
    }:
        raise ValueError("Spatial-pack search capability is unsupported.")
    context_layers = capabilities["context_layers"]
    if (
        not isinstance(context_layers, list)
        or not context_layers
        or any(item not in {"general-places", "public-transport"} for item in context_layers)
        or len(set(context_layers)) != len(context_layers)
    ):
        raise ValueError("Spatial-pack context layers are invalid.")
    sources = _labelled_links(value["sources"], include_version=True)
    attributions = _labelled_links(value["attribution"], include_version=False)
    limitations_value = value["limitations"]
    if not isinstance(limitations_value, list) or any(
        not isinstance(item, str) or not item.strip() or len(item) > 300
        for item in limitations_value
    ):
        raise ValueError("Spatial-pack limitations are invalid.")
    members_value = value["members"]
    if not isinstance(members_value, dict):
        raise ValueError("Spatial-pack members are invalid.")
    members: dict[str, dict[str, object]] = {}
    for name, definition in members_value.items():
        if name not in PACK_MEMBERS or not isinstance(definition, dict):
            raise ValueError("Spatial-pack member definition is invalid.")
        if set(definition) != {"sha256", "bytes"}:
            raise ValueError("Spatial-pack member metadata is invalid.")
        sha256 = definition["sha256"]
        byte_count = definition["bytes"]
        if (
            not isinstance(sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
            or isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count <= 0
        ):
            raise ValueError("Spatial-pack member digest or size is invalid.")
        members[name] = {"sha256": sha256, "bytes": byte_count}
    return SpatialPackManifest(
        pack_id,
        title,
        pack_version,
        produced_at,
        coverage_label,
        bbox,
        buffer_km,
        minimum_zoom,
        maximum_zoom,
        tuple(context_layers),
        tuple(sources),
        tuple(attributions),
        tuple(item.strip() for item in limitations_value),
        members,
        value,
    )


def _read_manifest(path: Path) -> SpatialPackManifest:
    try:
        return _manifest_from_value(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Installed spatial-pack manifest is unavailable or invalid.") from error


def _validate_staged_members(directory: Path, manifest: SpatialPackManifest) -> None:
    expected = {"manifest.json", "preview.json", *PACK_MEMBERS}
    names = {item.name for item in directory.iterdir()}
    if names not in (expected, expected - {"preview.json"}):
        raise ValueError("Staged spatial-pack files do not match the manifest.")
    for name, definition in manifest.members.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size != definition["bytes"]:
            raise ValueError(f"Staged spatial-pack member is missing or changed: {name}.")
        if _sha256_file(path) != definition["sha256"]:
            raise ValueError(f"Staged spatial-pack checksum failed for {name}.")


def _validate_installed_members(
    directory: Path, manifest: SpatialPackManifest
) -> None:
    if {item.name for item in directory.iterdir()} != {"manifest.json", *PACK_MEMBERS}:
        raise ValueError("Installed spatial-pack files do not match the manifest.")
    for name, definition in manifest.members.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size != definition["bytes"]:
            raise ValueError(f"Installed spatial-pack member is missing or changed: {name}.")


def _validate_mbtiles(path: Path, manifest: SpatialPackManifest) -> int:
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Spatial-pack MBTiles integrity check failed.")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            unsupported_objects = connection.execute(
                """SELECT COUNT(*) FROM sqlite_master
                    WHERE name NOT LIKE 'sqlite_%'
                      AND NOT (type='table' AND name IN ('metadata', 'tiles'))
                      AND type!='index'"""
            ).fetchone()[0]
            if tables != {"metadata", "tiles"} or unsupported_objects:
                raise ValueError("Spatial-pack MBTiles tables are incomplete.")
            metadata_columns = [
                row[1] for row in connection.execute("PRAGMA table_info(metadata)")
            ]
            tile_columns = [
                row[1] for row in connection.execute("PRAGMA table_info(tiles)")
            ]
            if metadata_columns != ["name", "value"] or tile_columns != [
                "zoom_level",
                "tile_column",
                "tile_row",
                "tile_data",
            ]:
                raise ValueError("Spatial-pack MBTiles columns are unsupported.")
            metadata_counts = connection.execute(
                "SELECT COUNT(*), COUNT(DISTINCT name) FROM metadata"
            ).fetchone()
            if metadata_counts[0] != metadata_counts[1]:
                raise ValueError("Spatial-pack MBTiles metadata names are duplicated.")
            metadata = dict(connection.execute("SELECT name, value FROM metadata"))
            if metadata.get("format") != "pbf":
                raise ValueError("Spatial-pack basemap must contain vector PBF tiles.")
            minimum, maximum, count = connection.execute(
                "SELECT MIN(zoom_level), MAX(zoom_level), COUNT(*) FROM tiles"
            ).fetchone()
            if (
                count <= 0
                or minimum != manifest.minimum_zoom
                or maximum != manifest.maximum_zoom
            ):
                raise ValueError("Spatial-pack tile count or zoom range is invalid.")
            invalid_coordinates = connection.execute(
                """SELECT COUNT(*) FROM tiles
                    WHERE zoom_level < 0 OR zoom_level > 18
                       OR tile_column < 0 OR tile_row < 0
                       OR tile_column >= (1 << zoom_level)
                       OR tile_row >= (1 << zoom_level)"""
            ).fetchone()[0]
            duplicate_coordinates = connection.execute(
                """SELECT 1 FROM tiles
                    GROUP BY zoom_level, tile_column, tile_row
                    HAVING COUNT(*) > 1 LIMIT 1"""
            ).fetchone()
            if invalid_coordinates or duplicate_coordinates:
                raise ValueError("Spatial-pack tile coordinates are invalid or duplicated.")
            bounds = _bbox(
                [float(item) for item in metadata.get("bounds", "").split(",")]
            )
            if any(
                not math.isclose(item, expected, abs_tol=0.00001)
                for item, expected in zip(bounds, manifest.coverage_bbox)
            ):
                raise ValueError("Spatial-pack MBTiles bounds do not match coverage.")
            for row in connection.execute("SELECT tile_data FROM tiles"):
                content = bytes(row[0])
                if not content:
                    raise ValueError("Spatial-pack MBTiles contains an empty tile blob.")
                if content.startswith(b"\x1f\x8b"):
                    try:
                        content = gzip.decompress(content)
                    except gzip.BadGzipFile as error:
                        raise ValueError("Spatial-pack contains a corrupt gzip tile.") from error
                if not _valid_protobuf_wire(content):
                    raise ValueError("Spatial-pack contains an invalid vector-tile message.")
            return int(count)
    except sqlite3.Error as error:
        raise ValueError("Spatial-pack MBTiles database is invalid.") from error


def _validate_search_database(
    path: Path, coverage_bbox: tuple[float, float, float, float]
) -> int:
    uri = f"file:{path.resolve()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Spatial-pack search integrity check failed.")
            if connection.execute("PRAGMA application_id").fetchone()[0] != SEARCH_APPLICATION_ID:
                raise ValueError("Spatial-pack search database identity is invalid.")
            if connection.execute("PRAGMA user_version").fetchone()[0] != SEARCH_USER_VERSION:
                raise ValueError("Spatial-pack search database version is unsupported.")
            objects = {
                (row[0], row[1])
                for row in connection.execute(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE name NOT LIKE 'sqlite_%'"
                )
            }
            if objects != {
                ("table", "search_features"),
                ("index", "idx_search_features_title"),
            }:
                raise ValueError("Spatial-pack search schema contains unsupported objects.")
            columns = [
                row[1]
                for row in connection.execute("PRAGMA table_info(search_features)")
            ]
            if columns != [
                "feature_id",
                "title",
                "subtitle",
                "feature_type",
                "source_layer",
                "latitude",
                "longitude",
                "search_text",
            ]:
                raise ValueError("Spatial-pack search columns are invalid.")
            count, invalid = connection.execute(
                """SELECT COUNT(*), SUM(CASE WHEN
                       title='' OR feature_id='' OR search_text='' OR
                       latitude<? OR latitude>? OR longitude<? OR longitude>?
                       THEN 1 ELSE 0 END)
                     FROM search_features""",
                (
                    coverage_bbox[1],
                    coverage_bbox[3],
                    coverage_bbox[0],
                    coverage_bbox[2],
                ),
            ).fetchone()
            if count <= 0 or invalid:
                raise ValueError("Spatial-pack search features are empty or outside coverage.")
            return int(count)
    except sqlite3.Error as error:
        raise ValueError("Spatial-pack search database is invalid.") from error


def _validate_coverage(
    path: Path, coverage_bbox: tuple[float, float, float, float]
) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Spatial-pack coverage GeoJSON is invalid.") from error
    features = value.get("features") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("type") != "FeatureCollection"
        or not isinstance(features, list)
        or not features
    ):
        raise ValueError("Spatial-pack coverage must contain GeoJSON features.")
    if any(
        not isinstance(feature, dict)
        or feature.get("type") != "Feature"
        or not isinstance(feature.get("geometry"), dict)
        or feature["geometry"].get("type") not in {"Polygon", "MultiPolygon"}
        for feature in features
    ):
        raise ValueError("Spatial-pack coverage features must be polygons.")
    coordinates = list(_geojson_coordinates(value))
    if not coordinates:
        raise ValueError("Spatial-pack coverage contains no coordinates.")
    west, south, east, north = coverage_bbox
    if any(
        not (west <= longitude <= east and south <= latitude <= north)
        for longitude, latitude in coordinates
    ):
        raise ValueError("Spatial-pack coverage geometry extends outside its bounds.")


def _active_for_request(root: Path, activation_id: str) -> InstalledSpatialPack | None:
    if not ACTIVATION_PATTERN.fullmatch(activation_id):
        return None
    status = spatial_pack_status(root)
    if status.active is None or status.active.activation_id != activation_id:
        return None
    return status.active


def _installed_versions(
    root: Path, pointer: dict[str, str] | None
) -> list[InstalledSpatialPack]:
    versions = root / "versions"
    if not versions.is_dir():
        return []
    items = []
    for directory in sorted(versions.iterdir(), key=lambda item: item.name):
        if not directory.is_dir() or not ACTIVATION_PATTERN.fullmatch(directory.name):
            continue
        try:
            manifest = _read_manifest(directory / "manifest.json")
            _validate_installed_members(directory, manifest)
        except ValueError:
            if pointer and pointer["activation_id"] == directory.name:
                raise
            continue
        items.append(
            InstalledSpatialPack(
                directory.name,
                directory,
                manifest,
                pointer["activated_at"]
                if pointer and pointer["activation_id"] == directory.name
                else "",
                pointer["previous_activation_id"]
                if pointer and pointer["activation_id"] == directory.name
                else "",
            )
        )
    return items


def _read_active_pointer(root: Path) -> dict[str, str] | None:
    path = root / "active.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "activation_id",
        "activated_at",
        "previous_activation_id",
    }:
        raise ValueError("Spatial-pack active pointer is invalid.")
    if value["schema_version"] != 1 or not ACTIVATION_PATTERN.fullmatch(
        value["activation_id"]
    ):
        raise ValueError("Spatial-pack active pointer is unsupported.")
    previous = value["previous_activation_id"]
    if previous and not ACTIVATION_PATTERN.fullmatch(previous):
        raise ValueError("Spatial-pack rollback pointer is invalid.")
    if not isinstance(value["activated_at"], str):
        raise ValueError("Spatial-pack activation time is invalid.")
    return value


def _activation_id(manifest: SpatialPackManifest) -> str:
    digest = hashlib.sha256(
        json.dumps(manifest.raw, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:12]
    return f"{manifest.pack_id}--{manifest.pack_version}--{digest}"


def _safe_version_directory(root: Path, activation_id: str) -> Path:
    if not ACTIVATION_PATTERN.fullmatch(activation_id):
        raise ValueError("Spatial-pack activation ID is unsafe.")
    directory = root / "versions" / activation_id
    if directory.parent.resolve() != (root / "versions").resolve():
        raise ValueError("Spatial-pack directory is unsafe.")
    return directory


def _write_json_atomic(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ensure_free_space(root: Path, unpacked_bytes: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    reserve = max(64 * 1024 * 1024, unpacked_bytes // 10)
    if shutil.disk_usage(root).free < unpacked_bytes + reserve:
        raise ValueError(
            "Insufficient disk space to stage and validate this spatial pack safely."
        )


def _prune_expired_staging(staging_root: Path) -> None:
    cutoff = time.time() - STAGING_TTL_SECONDS
    for item in staging_root.iterdir():
        try:
            if item.is_symlink() or item.stat().st_mtime >= cutoff:
                continue
            if item.is_dir() and (
                TOKEN_PATTERN.fullmatch(item.name)
                or (item.name.startswith(".") and item.name.endswith(".building"))
            ):
                shutil.rmtree(item)
        except OSError:
            continue


def _unsafe_member(info: zipfile.ZipInfo) -> bool:
    path = PurePosixPath(info.filename)
    mode = info.external_attr >> 16
    return (
        info.is_dir()
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in info.filename
        or (mode & 0o170000) == 0o120000
    )


def _labelled_links(value: object, *, include_version: bool) -> list[dict[str, str]]:
    required = {"label", "url", "version"} if include_version else {"label", "url"}
    if not isinstance(value, list) or not value:
        raise ValueError("Spatial-pack source/attribution list is invalid.")
    result = []
    for item in value:
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("Spatial-pack source/attribution entry is invalid.")
        label = _text(item["label"], "source label", maximum=200)
        url = _text(item["url"], "source URL", maximum=500)
        if not url.startswith("https://"):
            raise ValueError("Spatial-pack source/attribution URLs must use HTTPS.")
        output = {"label": label, "url": url}
        if include_version:
            output["version"] = _text(item["version"], "source version", maximum=200)
        result.append(output)
    return result


def _bbox(value: object) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("Spatial-pack bounding box is invalid.")
    west, south, east, north = (
        _number(item, "bounding-box coordinate") for item in value
    )
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Spatial-pack bounding box is invalid.")
    return west, south, east, north


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Spatial-pack {label} must be numeric.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Spatial-pack {label} must be finite.")
    return number


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Spatial-pack {label} must be a whole number.")
    return value


def _positive_integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError
    return value


def _text(value: object, label: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"Spatial-pack {label} is invalid.")
    return value.strip()


def _production_date(value: object) -> str:
    text = _text(value, "production date", maximum=40)
    try:
        if len(text) == 10:
            date.fromisoformat(text)
        else:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
    except ValueError as error:
        raise ValueError(
            "Spatial-pack production date must be an ISO date or timezone-aware timestamp."
        ) from error
    return text


def _geojson_coordinates(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "coordinates":
                yield from _coordinate_array(child)
            elif key in {"features", "geometry", "geometries"}:
                yield from _geojson_coordinates(child)
    elif isinstance(value, list):
        for child in value:
            yield from _geojson_coordinates(child)


def _coordinate_array(value: object):
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value[:2])
    ):
        longitude, latitude = float(value[0]), float(value[1])
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise ValueError("Spatial-pack coverage coordinate is invalid.")
        yield longitude, latitude
    elif isinstance(value, list):
        for child in value:
            yield from _coordinate_array(child)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _valid_tile_coordinate(zoom: int, x: int, y: int) -> bool:
    return (
        isinstance(zoom, int)
        and isinstance(x, int)
        and isinstance(y, int)
        and 0 <= zoom <= 18
        and 0 <= x < 2**zoom
        and 0 <= y < 2**zoom
    )


def _valid_protobuf_wire(content: bytes) -> bool:
    offset = 0
    try:
        while offset < len(content):
            key, offset = _read_varint(content, offset)
            if key >> 3 <= 0:
                return False
            wire_type = key & 0x07
            if wire_type == 0:
                _value, offset = _read_varint(content, offset)
            elif wire_type == 1:
                offset += 8
            elif wire_type == 2:
                length, offset = _read_varint(content, offset)
                offset += length
            elif wire_type == 5:
                offset += 4
            else:
                return False
            if offset > len(content):
                return False
        return True
    except ValueError:
        return False


def _read_varint(content: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(content) and shift < 70:
        byte = content[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("Invalid protobuf varint.")


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(microsecond=0).isoformat()
