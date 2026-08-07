"""Standard-library evidence collection for disposable spatial providers.

This module is deliberately outside the application runtime. It inventories public
source snapshots and disposable builds, probes loopback provider APIs and can serve
one MBTiles archive for renderer experiments. It does not install a pack, create a
provider adapter or mutate canonical Project E data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import time
import zipfile
from collections import Counter
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


PACKAGE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = PACKAGE_DIR / "manifest.json"
SCENARIOS_PATH = PACKAGE_DIR / "scenarios.json"
TILE_PATH = re.compile(r"^/tiles/(\d+)/(\d+)/(\d+)\.pbf$")


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _coordinates(value: object) -> Iterable[tuple[float, float]]:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(item, (int, float)) for item in value[:2])
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, list):
        for child in value:
            yield from _coordinates(child)


def buffered_bbox(
    bbox: tuple[float, float, float, float], buffer_km: float
) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    latitude = (south + north) / 2
    latitude_delta = buffer_km / 111.32
    longitude_delta = buffer_km / (
        111.32 * max(math.cos(math.radians(latitude)), 0.01)
    )
    return (
        west - longitude_delta,
        south - latitude_delta,
        east + longitude_delta,
        north + latitude_delta,
    )


def inspect_boundary(path: Path, *, buffer_km: float) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    features = document.get("features", [])
    coordinates = [
        coordinate
        for feature in features
        for coordinate in _coordinates(feature.get("geometry", {}).get("coordinates"))
    ]
    if not coordinates:
        raise ValueError("Boundary GeoJSON contains no coordinates.")
    bbox = (
        min(item[0] for item in coordinates),
        min(item[1] for item in coordinates),
        max(item[0] for item in coordinates),
        max(item[1] for item in coordinates),
    )
    return {
        "feature_count": len(features),
        "geometry_types": sorted(
            {
                str(feature.get("geometry", {}).get("type", ""))
                for feature in features
            }
        ),
        "vertex_count": len(coordinates),
        "bbox": list(bbox),
        "buffer_km": buffer_km,
        "buffered_bbox": list(buffered_bbox(bbox, buffer_km)),
    }


def _zip_rows(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with archive.open(name) as source:
        lines = (line.decode("utf-8-sig") for line in source)
        return list(csv.DictReader(lines))


def _zip_row_count(archive: zipfile.ZipFile, name: str) -> int:
    with archive.open(name) as source:
        return max(sum(1 for _line in source) - 1, 0)


def inspect_gtfs(path: Path) -> dict[str, Any]:
    required = {
        "agency.txt",
        "calendar.txt",
        "feed_info.txt",
        "routes.txt",
        "stops.txt",
        "stop_times.txt",
        "trips.txt",
    }
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"GTFS archive is missing {', '.join(missing)}.")
        feed = _zip_rows(archive, "feed_info.txt")
        agencies = _zip_rows(archive, "agency.txt")
        routes = _zip_rows(archive, "routes.txt")
        stops = _zip_rows(archive, "stops.txt")
        points = [
            (float(row["stop_lon"]), float(row["stop_lat"]))
            for row in stops
            if row.get("stop_lon") and row.get("stop_lat")
        ]
        entries = {
            info.filename: {
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "rows": _zip_row_count(archive, info.filename),
            }
            for info in archive.infolist()
            if info.filename.endswith(".txt")
        }
    return {
        "feed": feed[0] if feed else {},
        "agencies": agencies,
        "route_type_counts": dict(sorted(Counter(row.get("route_type", "") for row in routes).items())),
        "stop_count": len(stops),
        "stop_bbox": (
            [
                min(item[0] for item in points),
                min(item[1] for item in points),
                max(item[0] for item in points),
                max(item[1] for item in points),
            ]
            if points
            else None
        ),
        "entries": entries,
        "uncompressed_bytes": sum(item["uncompressed_bytes"] for item in entries.values()),
    }


def inspect_mbtiles(path: Path) -> dict[str, Any]:
    uri = f"file:{path.resolve()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        metadata = dict(connection.execute("SELECT name, value FROM metadata"))
        tile_count, tile_bytes, minimum, maximum = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(tile_data)), 0), "
            "COALESCE(MIN(LENGTH(tile_data)), 0), COALESCE(MAX(LENGTH(tile_data)), 0) "
            "FROM tiles"
        ).fetchone()
        zooms = [
            {"zoom": row[0], "tiles": row[1], "bytes": row[2]}
            for row in connection.execute(
                "SELECT zoom_level, COUNT(*), SUM(LENGTH(tile_data)) "
                "FROM tiles GROUP BY zoom_level ORDER BY zoom_level"
            )
        ]
    return {
        "metadata": metadata,
        "tile_count": tile_count,
        "tile_bytes": tile_bytes,
        "minimum_tile_bytes": minimum,
        "maximum_tile_bytes": maximum,
        "zooms": zooms,
    }


def _tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _memory_total_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def inventory(staging_root: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "snapshot_id": manifest["snapshot_id"],
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory_bytes": _memory_total_bytes(),
        },
        "sources": {},
        "builds": {},
    }
    source_root = staging_root / "sources"
    for key, definition in manifest["sources"].items():
        path = source_root / definition["filename"]
        item: dict[str, Any] = {
            "path": str(path),
            "present": path.is_file(),
            "expected_sha256": definition["sha256"],
        }
        if path.is_file():
            actual_sha256 = sha256_file(path)
            item.update(
                {
                    "bytes": path.stat().st_size,
                    "sha256": actual_sha256,
                    "verified": actual_sha256 == definition["sha256"],
                }
            )
            if definition["kind"] == "boundary":
                item["content"] = inspect_boundary(
                    path, buffer_km=float(manifest["buffer_km"])
                )
            elif definition["kind"] == "gtfs":
                item["content"] = inspect_gtfs(path)
        result["sources"][key] = item
    build_root = staging_root / "builds"
    for key, definition in manifest["builds"].items():
        path = build_root / definition["path"]
        item = {"path": str(path), "present": path.exists()}
        if path.is_file():
            actual_sha256 = sha256_file(path)
            item.update({"bytes": path.stat().st_size, "sha256": actual_sha256})
            if expected_sha256 := definition.get("sha256"):
                item["expected_sha256"] = expected_sha256
                item["verified"] = actual_sha256 == expected_sha256
            if definition["kind"] == "mbtiles":
                item["content"] = inspect_mbtiles(path)
        elif path.is_dir():
            item["bytes"] = _tree_bytes(path)
            item["file_count"] = sum(1 for child in path.rglob("*") if child.is_file())
        result["builds"][key] = item
    return result


def acquire_source(
    source_key: str, staging_root: Path, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        definition = manifest["sources"][source_key]
    except KeyError as error:
        raise ValueError(f"Unknown source {source_key!r}.") from error
    filename = Path(definition["filename"])
    if filename.name != definition["filename"]:
        raise ValueError("Source filename must not contain directories.")
    target = staging_root / "sources" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    byte_count = 0
    request = Request(definition["url"], headers={"User-Agent": "Project-E-X1/1.0"})
    try:
        with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                byte_count += len(chunk)
        actual = digest.hexdigest()
        if actual != definition["sha256"]:
            raise ValueError(
                f"Checksum mismatch for {source_key}: expected "
                f"{definition['sha256']}, received {actual}."
            )
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {"path": str(target), "bytes": byte_count, "sha256": digest.hexdigest()}


def _request_json(request: Request, *, timeout: float = 30) -> tuple[int, Any]:
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return error.code, {"error": "non_json_provider_error"}


def _motis_summary(operation: str, body: Any) -> dict[str, Any]:
    if operation == "geocode":
        results = body if isinstance(body, list) else []
        return {
            "result_count": len(results),
            "types": [item.get("type") for item in results],
            "names": [item.get("name") for item in results],
        }
    direct = body.get("direct", []) if isinstance(body, dict) else []
    itineraries = body.get("itineraries", []) if isinstance(body, dict) else []
    alternatives = direct or itineraries
    first = alternatives[0] if alternatives else {}
    return {
        "empty": not alternatives,
        "direct_count": len(direct),
        "itinerary_count": len(itineraries),
        "duration_seconds": first.get("duration"),
        "stage_modes": [leg.get("mode") for leg in first.get("legs", [])],
        "stage_distances_metres": [leg.get("distance") for leg in first.get("legs", [])],
    }


def _valhalla_summary(body: Any) -> dict[str, Any]:
    trip = body.get("trip", {}) if isinstance(body, dict) else {}
    summary = trip.get("summary", {})
    return {
        "error_code": body.get("error_code") if isinstance(body, dict) else None,
        "error": body.get("error") if isinstance(body, dict) else None,
        "duration_seconds": summary.get("time"),
        "distance_kilometres": summary.get("length"),
        "leg_count": len(trip.get("legs", [])),
        "shape_bounds": [
            summary.get("min_lon"),
            summary.get("min_lat"),
            summary.get("max_lon"),
            summary.get("max_lat"),
        ],
    }


def probe_provider(
    provider: str,
    base_url: str,
    scenarios_path: Path = SCENARIOS_PATH,
    *,
    repetitions: int = 3,
) -> dict[str, Any]:
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))[provider]
    results = []
    for scenario in scenarios:
        latencies = []
        status = 0
        summary: dict[str, Any] = {}
        for _index in range(repetitions):
            started = time.perf_counter()
            if provider == "motis":
                path = scenario["path"]
                query = urlencode(scenario.get("query", {}))
                url = f"{base_url.rstrip('/')}{path}{'?' + query if query else ''}"
                request = Request(url, headers={"Accept": "application/json"})
            elif provider == "valhalla":
                url = f"{base_url.rstrip('/')}{scenario['path']}"
                request = Request(
                    url,
                    data=json.dumps(scenario["payload"]).encode("utf-8"),
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                )
            else:
                raise ValueError(f"Unknown provider {provider!r}.")
            status, body = _request_json(request)
            latencies.append((time.perf_counter() - started) * 1000)
            summary = (
                _motis_summary(scenario["operation"], body)
                if provider == "motis"
                else _valhalla_summary(body)
            )
        results.append(
            {
                "key": scenario["key"],
                "contract_case": scenario["contract_case"],
                "status": status,
                "latency_ms": {
                    "samples": [round(item, 3) for item in latencies],
                    "median": round(statistics.median(latencies), 3),
                },
                "summary": summary,
            }
        )
    return {"provider": provider, "base_url": base_url, "results": results}


def _process_rss_bytes(process: subprocess.Popen[bytes]) -> int | None:
    try:
        for line in Path(f"/proc/{process.pid}/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def cold_start_probe(
    provider: str,
    binary: Path,
    *,
    working_directory: Path,
    base_url: str,
    config: Path | None = None,
    timeout: float = 30,
) -> dict[str, Any]:
    if provider == "motis":
        command = [str(binary.resolve()), "server"]
        health_path = "/api/v1/health"
    elif provider == "valhalla":
        if config is None:
            raise ValueError("Valhalla cold-start probing requires --config.")
        command = [str(binary.resolve()), str(config.resolve()), "1"]
        health_path = "/status"
    else:
        raise ValueError(f"Unknown provider {provider!r}.")
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        cwd=working_directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    status = 0
    try:
        deadline = started + timeout
        while time.perf_counter() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"{provider} exited before its health endpoint was ready.")
            try:
                request = Request(f"{base_url.rstrip('/')}{health_path}")
                status, _body = _request_json(request, timeout=1)
                if 200 <= status < 300:
                    break
            except OSError:
                pass
            time.sleep(0.025)
        else:
            raise TimeoutError(f"{provider} was not ready within {timeout} seconds.")
        ready_ms = (time.perf_counter() - started) * 1000
        time.sleep(0.1)
        return {
            "provider": provider,
            "status": status,
            "ready_ms": round(ready_ms, 3),
            "rss_bytes": _process_rss_bytes(process),
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def mbtiles_tile(path: Path, zoom: int, x: int, y: int) -> bytes | None:
    if zoom < 0 or x < 0 or y < 0 or x >= 2**zoom or y >= 2**zoom:
        return None
    tms_y = (2**zoom - 1) - y
    uri = f"file:{path.resolve()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        row = connection.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
            (zoom, x, tms_y),
        ).fetchone()
    return bytes(row[0]) if row else None


def mbtiles_handler(archive: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            path = urlsplit(self.path).path
            if path == "/health":
                body = json.dumps({"status": "ok", "execution": "local"}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            match = TILE_PATH.fullmatch(path)
            if not match:
                self.send_error(404)
                return
            tile = mbtiles_tile(archive, *(int(item) for item in match.groups()))
            if tile is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.mapbox-vector-tile")
            if tile.startswith(b"\x1f\x8b"):
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(tile)))
            self.end_headers()
            self.wfile.write(tile)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def serve_mbtiles(archive: Path, port: int) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), mbtiles_handler(archive))
    server.serve_forever()
