"""Fictional, deterministic spatial-pack fixtures for N4 tests."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from app.spatial_pack import (
    FORMAT_NAME,
    FORMAT_VERSION,
    SEARCH_APPLICATION_ID,
    SEARCH_USER_VERSION,
)


TEST_BOUNDS = [153.0, -28.5, 154.0, -27.5]


def fictional_spatial_pack(
    version: str = "2026.08.01",
    *,
    pack_id: str = "au-qld-fictional-coast",
    title: str = "Fictional Coast local map",
) -> bytes:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        mbtiles = root / "basemap.mbtiles"
        search = root / "search.sqlite3"
        _write_mbtiles(mbtiles)
        _write_search(search, version)
        coverage = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "Fictional Coast"},
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
            },
            separators=(",", ":"),
        ).encode()
        members = {
            "basemap.mbtiles": mbtiles.read_bytes(),
            "search.sqlite3": search.read_bytes(),
            "coverage.geojson": coverage,
        }
        manifest = {
            "format": FORMAT_NAME,
            "schema_version": FORMAT_VERSION,
            "pack_id": pack_id,
            "title": title,
            "pack_version": version,
            "produced_at": "2026-08-07",
            "coverage": {
                "label": "Fictional Coast test bounds",
                "bbox": TEST_BOUNDS,
                "buffer_km": 10,
                "boundary_member": "coverage.geojson",
            },
            "capabilities": {
                "basemap": {
                    "format": "mvt-mbtiles",
                    "member": "basemap.mbtiles",
                    "profile": "project-e-openmaptiles-v1",
                    "minimum_zoom": 0,
                    "maximum_zoom": 0,
                },
                "search": {
                    "format": "project-e-search-sqlite-v1",
                    "member": "search.sqlite3",
                },
                "context_layers": ["general-places", "public-transport"],
            },
            "sources": [
                {
                    "label": "Fictional open map source",
                    "url": "https://example.test/map-license",
                    "version": version,
                },
                {
                    "label": "Fictional transit source",
                    "url": "https://example.test/transit-license",
                    "version": version,
                },
            ],
            "attribution": [
                {
                    "label": "Fictional map contributors",
                    "url": "https://example.test/attribution",
                }
            ],
            "limitations": ["Fictional test coverage only."],
            "members": {
                name: {
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                }
                for name, content in members.items()
            },
        }
        return _zip(manifest, members)


def rewrite_bundle(bundle: bytes, transform) -> bytes:
    with zipfile.ZipFile(io.BytesIO(bundle)) as source:
        values = {item.filename: source.read(item) for item in source.infolist()}
    transform(values)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in values.items():
            archive.writestr(name, content)
    return output.getvalue()


def _write_mbtiles(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """CREATE TABLE metadata (name TEXT, value TEXT);
               CREATE TABLE tiles (
                   zoom_level INTEGER,
                   tile_column INTEGER,
                   tile_row INTEGER,
                   tile_data BLOB
               );"""
        )
        connection.executemany(
            "INSERT INTO metadata VALUES(?, ?)",
            (
                ("name", "Fictional Coast"),
                ("format", "pbf"),
                ("bounds", ",".join(str(item) for item in TEST_BOUNDS)),
                ("minzoom", "0"),
                ("maxzoom", "0"),
            ),
        )
        connection.execute(
            "INSERT INTO tiles VALUES(0, 0, 0, ?)", (gzip.compress(b""),)
        )
        connection.commit()
    finally:
        connection.close()


def _write_search(path: Path, version: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(f"PRAGMA application_id={SEARCH_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version={SEARCH_USER_VERSION}")
        connection.executescript(
            """CREATE TABLE search_features (
                   feature_id TEXT PRIMARY KEY,
                   title TEXT NOT NULL,
                   subtitle TEXT NOT NULL,
                   feature_type TEXT NOT NULL,
                   source_layer TEXT NOT NULL,
                   latitude REAL NOT NULL,
                   longitude REAL NOT NULL,
                   search_text TEXT NOT NULL
               ) WITHOUT ROWID;
               CREATE INDEX idx_search_features_title
                   ON search_features(title);"""
        )
        connection.executemany(
            "INSERT INTO search_features VALUES(?,?,?,?,?,?,?,?)",
            (
                (
                    f"place:surfers:{version}",
                    "Surfers Paradise",
                    "Fictional suburb",
                    "Suburb",
                    "place",
                    -28.002,
                    153.43,
                    "surfers paradise fictional suburb suburb place",
                ),
                (
                    f"stop:broadbeach:{version}",
                    "Broadbeach South station",
                    "Fictional transit stop",
                    "Transit station",
                    "public_transport",
                    -28.03,
                    153.43,
                    "broadbeach south station fictional transit stop",
                ),
                (
                    f"stop:broadbeach-platform:{version}",
                    "Broadbeach South station",
                    "Fictional transit stop",
                    "Transit station",
                    "public_transport",
                    -28.031,
                    153.431,
                    "broadbeach south station fictional transit stop platform",
                ),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _zip(manifest: dict[str, object], members: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json", json.dumps(manifest, sort_keys=True).encode()
        )
        for name, content in members.items():
            archive.writestr(name, content)
    return output.getvalue()
