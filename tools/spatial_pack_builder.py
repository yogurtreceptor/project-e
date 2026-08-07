"""Build a deterministic Project E spatial pack from verified derived inputs."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import sqlite3
import struct
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path
from typing import Any, Iterable

from app.spatial_pack import (
    FORMAT_NAME,
    FORMAT_VERSION,
    SEARCH_APPLICATION_ID,
    SEARCH_USER_VERSION,
    inspect_and_stage_spatial_pack,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_MANIFEST = ROOT / "tools" / "spatial_evidence" / "manifest.json"
SEARCH_LAYERS = {
    "place",
    "poi",
    "transportation_name",
    "water_name",
    "aerodrome_label",
    "mountain_peak",
}


def build_spatial_pack(
    *,
    mbtiles_path: Path,
    boundary_path: Path,
    gtfs_path: Path,
    output_path: Path,
    pack_version: str = "2026.08.01",
    produced_at: str = "2026-08-07",
) -> dict[str, object]:
    evidence = json.loads(EVIDENCE_MANIFEST.read_text(encoding="utf-8"))
    boundary_content = boundary_path.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        search_path = Path(directory) / "search.sqlite3"
        bounds, minimum_zoom, maximum_zoom = mbtiles_definition(mbtiles_path)
        search_count = build_search_database(
            mbtiles_path, gtfs_path, search_path, bounds
        )
        members = {
            "basemap.mbtiles": mbtiles_path.read_bytes(),
            "search.sqlite3": search_path.read_bytes(),
            "coverage.geojson": boundary_content,
        }
        sources = evidence["sources"]
        manifest: dict[str, object] = {
            "format": FORMAT_NAME,
            "schema_version": FORMAT_VERSION,
            "pack_id": "au-qld-gold-coast",
            "title": "Gold Coast local map",
            "pack_version": pack_version,
            "produced_at": produced_at,
            "coverage": {
                "label": "Gold Coast LGA with 15 km map context",
                "bbox": list(bounds),
                "buffer_km": 15,
                "boundary_member": "coverage.geojson",
            },
            "capabilities": {
                "basemap": {
                    "format": "mvt-mbtiles",
                    "member": "basemap.mbtiles",
                    "profile": "project-e-openmaptiles-v1",
                    "minimum_zoom": minimum_zoom,
                    "maximum_zoom": maximum_zoom,
                },
                "search": {
                    "format": "project-e-search-sqlite-v1",
                    "member": "search.sqlite3",
                },
                "context_layers": ["general-places", "public-transport"],
            },
            "sources": [
                {
                    "label": "OpenStreetMap / Geofabrik Queensland",
                    "url": sources["queensland_osm"]["license_url"],
                    "version": sources["queensland_osm"]["version"],
                },
                {
                    "label": "City of Gold Coast boundary",
                    "url": sources["gold_coast_boundary"]["license_url"],
                    "version": sources["gold_coast_boundary"]["version"],
                },
                {
                    "label": "Translink SEQ GTFS",
                    "url": sources["seq_gtfs"]["license_url"],
                    "version": sources["seq_gtfs"]["version"],
                },
            ],
            "attribution": [
                {
                    "label": "© OpenStreetMap contributors",
                    "url": "https://www.openstreetmap.org/copyright",
                },
                {
                    "label": "City of Gold Coast",
                    "url": sources["gold_coast_boundary"]["license_url"],
                },
                {
                    "label": "Department of Transport and Main Roads – Translink Division",
                    "url": sources["seq_gtfs"]["license_url"],
                },
            ],
            "limitations": [
                "Basemap and installed search stop at the declared pack bounds; canonical coordinates remain visible outside them.",
                "Provider labels are derived from visible OSM vector features and static GTFS stops and are intentionally sparser than a commercial map.",
                "The official LGA geometry supplies the reviewed land/coverage outline; source route coordinates may extend into the 15 km context buffer.",
            ],
            "members": {
                name: {"sha256": _sha256(content), "bytes": len(content)}
                for name, content in members.items()
            },
        }
        bundle = _deterministic_zip(manifest, members, produced_at)
        with tempfile.TemporaryDirectory() as validation_directory:
            preview = inspect_and_stage_spatial_pack(
                bundle, Path(validation_directory) / "packs"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(bundle)
    return {
        "path": str(output_path),
        "bytes": len(bundle),
        "sha256": _sha256(bundle),
        "tiles": preview.tile_count,
        "search_features": search_count,
        "pack_id": preview.manifest.pack_id,
        "pack_version": preview.manifest.pack_version,
    }


def mbtiles_definition(path: Path) -> tuple[tuple[float, float, float, float], int, int]:
    uri = f"file:{path.resolve()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        metadata = dict(connection.execute("SELECT name, value FROM metadata"))
        minimum, maximum = connection.execute(
            "SELECT MIN(zoom_level), MAX(zoom_level) FROM tiles"
        ).fetchone()
    bounds = tuple(float(item) for item in metadata["bounds"].split(","))
    if len(bounds) != 4 or minimum is None or maximum is None:
        raise ValueError("MBTiles metadata is incomplete.")
    return bounds, int(minimum), int(maximum)  # type: ignore[return-value]


def build_search_database(
    mbtiles_path: Path,
    gtfs_path: Path,
    output_path: Path,
    bounds: tuple[float, float, float, float],
) -> int:
    features = list(vector_search_features(mbtiles_path))
    features.extend(gtfs_search_features(gtfs_path, bounds))
    deduplicated: dict[str, tuple[object, ...]] = {}
    west, south, east, north = bounds
    for feature in features:
        latitude = float(feature[5])
        longitude = float(feature[6])
        if not (west <= longitude <= east and south <= latitude <= north):
            continue
        source_layer = str(feature[4])
        location_key = (
            ""
            if source_layer in {"transportation_name", "water_name"}
            else f"{latitude:.3f}|{longitude:.3f}"
        )
        key = "|".join(
            (
                str(feature[1]).casefold(),
                str(feature[3]),
                source_layer,
                location_key,
            )
        )
        deduplicated.setdefault(key, feature)
    rows = []
    for key, feature in sorted(
        deduplicated.items(),
        key=lambda item: (str(item[1][1]).casefold(), item[0]),
    ):
        stable_id = f"{feature[4]}:" + hashlib.sha256(key.encode()).hexdigest()[:24]
        rows.append((stable_id, *feature[1:]))
    connection = sqlite3.connect(output_path)
    try:
        connection.execute(f"PRAGMA application_id={SEARCH_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={SEARCH_USER_VERSION}")
        connection.execute(
            """CREATE TABLE search_features (
                   feature_id TEXT PRIMARY KEY,
                   title TEXT NOT NULL,
                   subtitle TEXT NOT NULL,
                   feature_type TEXT NOT NULL,
                   source_layer TEXT NOT NULL,
                   latitude REAL NOT NULL,
                   longitude REAL NOT NULL,
                   search_text TEXT NOT NULL
               ) WITHOUT ROWID"""
        )
        connection.execute(
            "CREATE INDEX idx_search_features_title ON search_features(title)"
        )
        connection.executemany(
            "INSERT INTO search_features VALUES(?,?,?,?,?,?,?,?)", rows
        )
        connection.commit()
        connection.execute("VACUUM")
    finally:
        connection.close()
    return len(rows)


def vector_search_features(path: Path) -> Iterable[tuple[object, ...]]:
    uri = f"file:{path.resolve()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        maximum_zoom = connection.execute(
            "SELECT MAX(zoom_level) FROM tiles"
        ).fetchone()[0]
        rows = connection.execute(
            "SELECT tile_column, tile_row, tile_data FROM tiles WHERE zoom_level=?",
            (maximum_zoom,),
        )
        for tile_x, tms_y, raw_data in rows:
            tile_y = (2**maximum_zoom - 1) - tms_y
            data = bytes(raw_data)
            if data.startswith(b"\x1f\x8b"):
                data = gzip.decompress(data)
            for layer_name, feature_id, properties, points, extent in decode_mvt(data):
                if layer_name not in SEARCH_LAYERS or not points:
                    continue
                title = str(
                    properties.get("name:latin")
                    or properties.get("name")
                    or properties.get("ref")
                    or ""
                ).strip()
                if not title:
                    continue
                longitude, latitude = tile_point_to_lonlat(
                    maximum_zoom,
                    tile_x,
                    tile_y,
                    sum(item[0] for item in points) / len(points),
                    sum(item[1] for item in points) / len(points),
                    extent,
                )
                classification = str(
                    properties.get("subclass") or properties.get("class") or ""
                ).replace("_", " ").strip()
                type_label = feature_type_label(layer_name, classification)
                subtitle = classification.title() if classification else type_label
                identity = f"{layer_name}|{feature_id}|{title}|{latitude:.6f}|{longitude:.6f}"
                stable_id = "osm-vector:" + hashlib.sha256(identity.encode()).hexdigest()[:24]
                search_text = " ".join(
                    value
                    for value in (title, subtitle, type_label, layer_name.replace("_", " "))
                    if value
                ).casefold()
                yield (
                    stable_id,
                    title,
                    subtitle,
                    type_label,
                    layer_name,
                    latitude,
                    longitude,
                    search_text,
                )


def gtfs_search_features(
    path: Path, bounds: tuple[float, float, float, float]
) -> Iterable[tuple[object, ...]]:
    west, south, east, north = bounds
    with zipfile.ZipFile(path) as archive, archive.open("stops.txt") as source:
        rows = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig"))
        for row in rows:
            try:
                latitude = float(row["stop_lat"])
                longitude = float(row["stop_lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (west <= longitude <= east and south <= latitude <= north):
                continue
            title = row.get("stop_name", "").strip()
            stop_id = row.get("stop_id", "").strip()
            if not title or not stop_id:
                continue
            location_type = row.get("location_type", "").strip()
            type_label = "Transit station" if location_type == "1" else "Transit stop"
            subtitle = row.get("stop_desc", "").strip() or type_label
            search_text = " ".join(
                value
                for value in (
                    title,
                    subtitle,
                    row.get("stop_code", ""),
                    row.get("platform_code", ""),
                    type_label,
                )
                if value
            ).casefold()
            yield (
                f"translink-stop:{stop_id}",
                title,
                subtitle,
                type_label,
                "public_transport",
                latitude,
                longitude,
                search_text,
            )


def decode_mvt(
    data: bytes,
) -> Iterable[tuple[str, int, dict[str, object], list[tuple[int, int]], int]]:
    for field_number, wire_type, value in protobuf_fields(data):
        if field_number != 3 or wire_type != 2:
            continue
        layer_name = ""
        keys: list[str] = []
        values: list[object] = []
        features: list[bytes] = []
        extent = 4096
        for layer_field, layer_wire, layer_value in protobuf_fields(value):
            if layer_field == 1 and layer_wire == 2:
                layer_name = layer_value.decode("utf-8", errors="replace")
            elif layer_field == 2 and layer_wire == 2:
                features.append(layer_value)
            elif layer_field == 3 and layer_wire == 2:
                keys.append(layer_value.decode("utf-8", errors="replace"))
            elif layer_field == 4 and layer_wire == 2:
                values.append(decode_mvt_value(layer_value))
            elif layer_field == 5 and layer_wire == 0:
                extent = int(layer_value)
        if layer_name not in SEARCH_LAYERS:
            continue
        for feature in features:
            identity = 0
            tags: list[int] = []
            geometry: list[int] = []
            for feature_field, feature_wire, feature_value in protobuf_fields(feature):
                if feature_field == 1 and feature_wire == 0:
                    identity = int(feature_value)
                elif feature_field == 2 and feature_wire == 2:
                    tags = list(packed_varints(feature_value))
                elif feature_field == 4 and feature_wire == 2:
                    geometry = list(packed_varints(feature_value))
            properties = {
                keys[tags[index]]: values[tags[index + 1]]
                for index in range(0, len(tags) - 1, 2)
                if tags[index] < len(keys) and tags[index + 1] < len(values)
            }
            yield layer_name, identity, properties, decode_geometry(geometry), extent


def protobuf_fields(data: bytes):
    offset = 0
    while offset < len(data):
        key, offset = read_varint(data, offset)
        field_number, wire_type = key >> 3, key & 0x07
        if wire_type == 0:
            value, offset = read_varint(data, offset)
        elif wire_type == 1:
            if offset + 8 > len(data):
                raise ValueError("Truncated protobuf field.")
            value, offset = data[offset : offset + 8], offset + 8
        elif wire_type == 2:
            length, offset = read_varint(data, offset)
            if offset + length > len(data):
                raise ValueError("Truncated protobuf field.")
            value, offset = data[offset : offset + length], offset + length
        elif wire_type == 5:
            if offset + 4 > len(data):
                raise ValueError("Truncated protobuf field.")
            value, offset = data[offset : offset + 4], offset + 4
        else:
            raise ValueError("Unsupported protobuf wire type.")
        yield field_number, wire_type, value


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift < 70:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
    raise ValueError("Invalid protobuf varint.")


def packed_varints(data: bytes) -> Iterable[int]:
    offset = 0
    while offset < len(data):
        value, offset = read_varint(data, offset)
        yield value


def decode_mvt_value(data: bytes) -> object:
    for field_number, wire_type, value in protobuf_fields(data):
        if field_number == 1 and wire_type == 2:
            return value.decode("utf-8", errors="replace")
        if field_number == 2 and wire_type == 5:
            return struct.unpack("<f", value)[0]
        if field_number == 3 and wire_type == 1:
            return struct.unpack("<d", value)[0]
        if field_number in {4, 5} and wire_type == 0:
            return int(value)
        if field_number == 6 and wire_type == 0:
            return zigzag(int(value))
        if field_number == 7 and wire_type == 0:
            return bool(value)
    return ""


def decode_geometry(commands: list[int]) -> list[tuple[int, int]]:
    points = []
    cursor_x = 0
    cursor_y = 0
    offset = 0
    while offset < len(commands):
        command = commands[offset]
        offset += 1
        command_id = command & 0x7
        count = command >> 3
        if command_id in {1, 2}:
            for _index in range(count):
                if offset + 1 >= len(commands):
                    return points
                cursor_x += zigzag(commands[offset])
                cursor_y += zigzag(commands[offset + 1])
                offset += 2
                points.append((cursor_x, cursor_y))
        elif command_id == 7:
            continue
        else:
            break
    return points


def zigzag(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


def tile_point_to_lonlat(
    zoom: int,
    tile_x: int,
    tile_y: int,
    point_x: float,
    point_y: float,
    extent: int,
) -> tuple[float, float]:
    scale = 2**zoom
    world_x = (tile_x + point_x / extent) / scale
    world_y = (tile_y + point_y / extent) / scale
    longitude = world_x * 360 - 180
    latitude = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * world_y))))
    return longitude, latitude


def feature_type_label(layer_name: str, classification: str) -> str:
    if layer_name == "transportation_name":
        return "Road or path"
    if layer_name == "water_name":
        return "Water feature"
    if layer_name == "aerodrome_label":
        return "Airport"
    if layer_name == "mountain_peak":
        return "Peak"
    return classification.title() if classification else layer_name.replace("_", " ").title()


def _deterministic_zip(
    manifest: dict[str, object], members: dict[str, bytes], produced_at: str
) -> bytes:
    try:
        year, month, day = (int(item) for item in produced_at[:10].split("-"))
    except (TypeError, ValueError):
        year, month, day = 2026, 1, 1
    timestamp = (max(year, 1980), month, day, 0, 0, 0)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        values = {
            "manifest.json": (
                json.dumps(manifest, indent=2, sort_keys=True) + "\n"
            ).encode(),
            **members,
        }
        for name, content in values.items():
            info = zipfile.ZipInfo(name, timestamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--mbtiles", required=True, type=Path)
    command.add_argument("--boundary", required=True, type=Path)
    command.add_argument("--gtfs", required=True, type=Path)
    command.add_argument("--output", required=True, type=Path)
    command.add_argument("--pack-version", default="2026.08.01")
    command.add_argument("--produced-at", default="2026-08-07")
    return command


def main() -> None:
    arguments = parser().parse_args()
    result = build_spatial_pack(
        mbtiles_path=arguments.mbtiles,
        boundary_path=arguments.boundary,
        gtfs_path=arguments.gtfs,
        output_path=arguments.output,
        pack_version=arguments.pack_version,
        produced_at=arguments.produced_at,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
