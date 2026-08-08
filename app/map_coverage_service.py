"""Contextual, non-mutating recommendations for improving Map coverage."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.spatial_pack import MAX_ARCHIVE_BYTES, spatial_pack_status


MAX_SELECTION_TITLE = 300


@dataclass(frozen=True)
class MapCoverageRecommendation:
    selection_title: str
    latitude: float
    longitude: float
    state: str
    state_label: str
    summary: str
    scope_label: str
    scope_explanation: str
    size_explanation: str
    network_explanation: str
    source_explanation: str
    pack_title: str = ""
    pack_version: str = ""
    coverage_label: str = ""
    buffer_km: float = 0.0
    installed_bytes: int = 0
    bounds_area_km2: float = 0.0
    distance_to_core_km: float | None = None
    distance_to_bounds_km: float | None = None
    sources: tuple[dict[str, str], ...] = ()
    limitations: tuple[str, ...] = ()


def assess_map_coverage(
    root: Path,
    *,
    selection_title: str,
    latitude: str | float,
    longitude: str | float,
) -> MapCoverageRecommendation:
    """Assess one selected point without fetching or mutating provider state."""
    title = " ".join(str(selection_title).strip().split()) or "Selected map point"
    if len(title) > MAX_SELECTION_TITLE:
        raise ValueError("The selected place name is too long for coverage review.")
    latitude_value = _coordinate(latitude, "Latitude", -90, 90)
    longitude_value = _coordinate(longitude, "Longitude", -180, 180)
    status = spatial_pack_status(root)
    if status.active is None:
        summary = (
            "Installed pack state is invalid, so no current coverage can be trusted."
            if status.error
            else "No spatial pack is active for this selected point."
        )
        return MapCoverageRecommendation(
            title,
            latitude_value,
            longitude_value,
            "unavailable",
            "No trusted installed coverage",
            summary,
            "Initial regional candidate",
            "Choose a bounded administrative region or explicit local extent containing the selected point. Review its boundary, capabilities and sources before acquiring an archive.",
            f"No installed baseline is available. A candidate must report archive and unpacked bytes during preview and remain below the {MAX_ARCHIVE_BYTES // (1024 * 1024)} MB inspection limit.",
            "This review made no network request. Acquiring a candidate is a separate explicit action and may require network access; activation remains a local reviewed step.",
            "No source is implied by the selected coordinate. A candidate must declare dated map, boundary and any transport sources before activation.",
            limitations=((status.error,) if status.error else ()),
        )

    active = status.active
    manifest = active.manifest
    try:
        coverage_bytes = (active.directory / "coverage.geojson").read_bytes()
        coverage_definition = manifest.members["coverage.geojson"]
        if (
            len(coverage_bytes) != int(coverage_definition["bytes"])
            or hashlib.sha256(coverage_bytes).hexdigest()
            != coverage_definition["sha256"]
        ):
            raise ValueError
        coverage = json.loads(coverage_bytes.decode("utf-8"))
        polygons = tuple(_coverage_polygons(coverage))
        if not polygons:
            raise ValueError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return MapCoverageRecommendation(
            title,
            latitude_value,
            longitude_value,
            "error",
            "Coverage geometry unavailable",
            "The active pack remains installed, but its reviewed coverage geometry could not be assessed.",
            "Repair or replace the current pack",
            "Do not infer an adjoining region while the active coverage boundary is unreadable. Inspect Spatial Packs and retain the selected point for a later review.",
            _size_explanation(manifest.members, manifest.coverage_bbox),
            "This review made no network request and did not repair, remove or replace the pack.",
            "Only the active manifest source declarations remain visible; coverage must not be claimed from them without valid boundary geometry.",
            pack_title=manifest.title,
            pack_version=manifest.pack_version,
            coverage_label=manifest.coverage_label,
            buffer_km=manifest.buffer_km,
            installed_bytes=_installed_bytes(manifest.members),
            bounds_area_km2=_bbox_area_km2(manifest.coverage_bbox),
            sources=manifest.sources,
            limitations=manifest.limitations,
        )

    point = (longitude_value, latitude_value)
    in_core = any(_point_in_polygon(point, polygon) for polygon in polygons)
    distance_to_core = _distance_to_polygons_km(point, polygons)
    west, south, east, north = manifest.coverage_bbox
    in_bounds = west <= longitude_value <= east and south <= latitude_value <= north
    installed_bytes = _installed_bytes(manifest.members)
    common = {
        "pack_title": manifest.title,
        "pack_version": manifest.pack_version,
        "coverage_label": manifest.coverage_label,
        "buffer_km": manifest.buffer_km,
        "installed_bytes": installed_bytes,
        "bounds_area_km2": _bbox_area_km2(manifest.coverage_bbox),
        "sources": manifest.sources,
        "limitations": manifest.limitations,
        "size_explanation": _size_explanation(
            manifest.members, manifest.coverage_bbox
        ),
        "network_explanation": "This review made no network request. Building or downloading a candidate is a separate explicit action; Project E will inspect its scope, size and sources before any activation.",
    }

    if in_core:
        return MapCoverageRecommendation(
            title,
            latitude_value,
            longitude_value,
            "core",
            "Inside reviewed core coverage",
            f"{title} is already inside the active pack's reviewed coverage geometry.",
            "Refresh the current region only if needed",
            "A missing or stale feature here is not evidence for a larger region. Prefer a same-scope refresh from newer compatible sources and keep the current selection while comparing the candidate preview.",
            source_explanation="Reuse the active region's declared source families only when their dates, licences and scope remain compatible. Transport coverage remains separate from map coverage.",
            distance_to_core_km=0.0,
            **common,
        )

    if in_bounds:
        distance_text = _distance_text(distance_to_core)
        return MapCoverageRecommendation(
            title,
            latitude_value,
            longitude_value,
            "context",
            "Inside map context, outside reviewed core",
            f"{title} is {distance_text} beyond the reviewed core but remains inside the pack's declared {manifest.buffer_km:g} km context bounds.",
            "Adjoining-area candidate",
            "Keep this point as the acceptance case. If it belongs to a bordering suburb or adjoining authority, build that named region or a common-snapshot union; do not relabel context tiles as reviewed administrative coverage.",
            source_explanation="The active map sources are a useful compatibility baseline, but a new administrative area needs its own reviewed boundary source. Continuous future routing would require one compatible common-snapshot graph rather than overlaid regional graphs.",
            distance_to_core_km=distance_to_core,
            **common,
        )

    distance_to_bounds = _distance_to_bbox_km(point, manifest.coverage_bbox)
    return MapCoverageRecommendation(
        title,
        latitude_value,
        longitude_value,
        "outside",
        "Outside declared pack coverage",
        f"{title} is {_distance_text(distance_to_bounds)} beyond the active pack bounds and {_distance_text(distance_to_core)} from its reviewed core.",
        "Separate region or measured union candidate",
        "Define a bounded region around this selection. Use a separate pack for independent browsing, or justify a common-snapshot union only when a cross-boundary feature or future route requires continuity.",
        source_explanation="Do not assume the active pack's boundary or transport source covers this point. A candidate must identify a suitable official boundary plus dated map and capability-specific transport or routing sources.",
        distance_to_core_km=distance_to_core,
        distance_to_bounds_km=distance_to_bounds,
        **common,
    )


def _size_explanation(
    members: dict[str, dict[str, object]],
    bbox: tuple[float, float, float, float],
) -> str:
    installed_size = _format_bytes(_installed_bytes(members))
    bounds_area = _bbox_area_km2(bbox)
    return (
        f"The current pack is {installed_size} installed across declared members "
        f"for about {bounds_area:,.0f} km² of rectangular bounds. This is a baseline, not "
        "a linear estimate: feature density and capabilities vary. Candidate archive and "
        "unpacked sizes must be measured during preview."
    )


def _installed_bytes(members: dict[str, dict[str, object]]) -> int:
    return sum(int(item["bytes"]) for item in members.values())


def _format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} bytes"


def _coverage_polygons(value: object):
    if not isinstance(value, dict) or value.get("type") != "FeatureCollection":
        return
    features = value.get("features")
    if not isinstance(features, list):
        return
    for feature in features:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            continue
        coordinates = geometry.get("coordinates")
        if geometry.get("type") == "Polygon" and isinstance(coordinates, list):
            polygon = _polygon(coordinates)
            if polygon:
                yield polygon
        elif geometry.get("type") == "MultiPolygon" and isinstance(coordinates, list):
            for item in coordinates:
                polygon = _polygon(item)
                if polygon:
                    yield polygon


def _polygon(value: object) -> tuple[tuple[tuple[float, float], ...], ...] | None:
    if not isinstance(value, list) or not value:
        return None
    rings = []
    for raw_ring in value:
        if not isinstance(raw_ring, list) or len(raw_ring) < 4:
            return None
        ring = []
        for coordinate in raw_ring:
            if (
                not isinstance(coordinate, list)
                or len(coordinate) < 2
                or isinstance(coordinate[0], bool)
                or isinstance(coordinate[1], bool)
                or not isinstance(coordinate[0], (int, float))
                or not isinstance(coordinate[1], (int, float))
            ):
                return None
            longitude, latitude = float(coordinate[0]), float(coordinate[1])
            if (
                not math.isfinite(longitude)
                or not math.isfinite(latitude)
                or not -180 <= longitude <= 180
                or not -90 <= latitude <= 90
            ):
                return None
            ring.append((longitude, latitude))
        rings.append(tuple(ring))
    return tuple(rings)


def _point_in_polygon(
    point: tuple[float, float],
    polygon: tuple[tuple[tuple[float, float], ...], ...],
) -> bool:
    if not _point_in_ring(point, polygon[0]):
        return False
    return not any(_point_in_ring(point, ring) for ring in polygon[1:])


def _point_in_ring(
    point: tuple[float, float], ring: tuple[tuple[float, float], ...]
) -> bool:
    longitude, latitude = point
    inside = False
    for first, second in zip(ring, (*ring[1:], ring[0])):
        if _point_on_segment(point, first, second):
            return True
        first_lon, first_lat = first
        second_lon, second_lat = second
        if (first_lat > latitude) != (second_lat > latitude):
            crossing = first_lon + (latitude - first_lat) * (
                second_lon - first_lon
            ) / (second_lat - first_lat)
            if longitude < crossing:
                inside = not inside
    return inside


def _point_on_segment(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> bool:
    longitude, latitude = point
    first_lon, first_lat = first
    second_lon, second_lat = second
    cross = (longitude - first_lon) * (second_lat - first_lat) - (
        latitude - first_lat
    ) * (second_lon - first_lon)
    if abs(cross) > 1e-10:
        return False
    return (
        min(first_lon, second_lon) - 1e-10
        <= longitude
        <= max(first_lon, second_lon) + 1e-10
        and min(first_lat, second_lat) - 1e-10
        <= latitude
        <= max(first_lat, second_lat) + 1e-10
    )


def _distance_to_polygons_km(
    point: tuple[float, float],
    polygons: tuple[tuple[tuple[tuple[float, float], ...], ...], ...],
) -> float:
    distances = [
        _distance_to_segment_km(point, first, second)
        for polygon in polygons
        for ring in polygon
        for first, second in zip(ring, (*ring[1:], ring[0]))
    ]
    return min(distances) if distances else 0.0


def _distance_to_bbox_km(
    point: tuple[float, float], bbox: tuple[float, float, float, float]
) -> float:
    longitude, latitude = point
    west, south, east, north = bbox
    nearest = (
        min(max(longitude, west), east),
        min(max(latitude, south), north),
    )
    return _haversine_km(latitude, longitude, nearest[1], nearest[0])


def _distance_to_segment_km(
    point: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    longitude, latitude = point
    longitude_scale = 111.320 * max(0.01, math.cos(math.radians(latitude)))
    latitude_scale = 110.574
    first_x = (first[0] - longitude) * longitude_scale
    first_y = (first[1] - latitude) * latitude_scale
    second_x = (second[0] - longitude) * longitude_scale
    second_y = (second[1] - latitude) * latitude_scale
    delta_x = second_x - first_x
    delta_y = second_y - first_y
    denominator = delta_x * delta_x + delta_y * delta_y
    position = 0.0 if denominator == 0 else -(first_x * delta_x + first_y * delta_y) / denominator
    position = min(1.0, max(0.0, position))
    return math.hypot(first_x + position * delta_x, first_y + position * delta_y)


def _bbox_area_km2(bbox: tuple[float, float, float, float]) -> float:
    west, south, east, north = bbox
    middle_latitude = (south + north) / 2
    width = _haversine_km(middle_latitude, west, middle_latitude, east)
    height = _haversine_km(south, west, north, west)
    return width * height


def _haversine_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    radius = 6371.0
    first_latitude_radians = math.radians(first_latitude)
    second_latitude_radians = math.radians(second_latitude)
    latitude_delta = math.radians(second_latitude - first_latitude)
    longitude_delta = math.radians(second_longitude - first_longitude)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_latitude_radians)
        * math.cos(second_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _coordinate(value: str | float, label: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} is invalid for coverage review.") from error
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"{label} is invalid for coverage review.")
    return number


def _distance_text(value: float) -> str:
    if value < 0.05:
        return "less than 50 m"
    if value < 1:
        return f"{value * 1000:.0f} m"
    return f"{value:.1f} km"
