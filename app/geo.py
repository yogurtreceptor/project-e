import json
import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.db import (
    list_entities,
    list_relationships,
    location_place_context,
    search_entities,
)
from app.entities import DEFINITIONS_BY_SLUG, EntityRecord
from app.relationships import RELATIONSHIP_TYPES_BY_KEY


DEFAULT_CENTER = {"latitude": -28.0167, "longitude": 153.4000, "zoom": 9}
MAX_VIEWPORT_PLACES = 500


@dataclass(frozen=True)
class MapLayerDefinition:
    id: str
    label: str
    entity_type: str
    enabled: bool = True


MAP_LAYERS: tuple[MapLayerDefinition, ...] = (
    MapLayerDefinition("locations", "Locations", "location", enabled=True),
    MapLayerDefinition("organisations", "Organisations", "organisation", enabled=False),
    MapLayerDefinition("people", "People", "person", enabled=False),
    MapLayerDefinition("assets", "Assets", "asset", enabled=False),
    MapLayerDefinition("events", "Events", "event", enabled=False),
    MapLayerDefinition("projects", "Projects", "project", enabled=False),
    MapLayerDefinition("documents", "Documents", "document", enabled=False),
)


MAP_BASE_VIEWS: tuple[dict[str, object], ...] = (
    {
        "id": "normal",
        "label": "Normal map",
        "available": False,
        "explanation": "No local basemap pack is installed. The canonical coordinate canvas remains available offline.",
    },
    {
        "id": "satellite",
        "label": "Satellite",
        "available": False,
        "explanation": "No reviewed satellite source is configured.",
    },
    {
        "id": "terrain",
        "label": "Terrain",
        "available": False,
        "explanation": "No reviewed terrain source is configured.",
    },
)


MAP_CONTEXT_LAYERS: tuple[dict[str, object], ...] = (
    {
        "id": "general-places",
        "label": "General places",
        "available": False,
        "enabled": False,
        "explanation": "Install a future reviewed region pack or explicitly enable a bounded provider capability.",
    },
    {
        "id": "public-transport",
        "label": "Public transport and stops",
        "available": False,
        "enabled": False,
        "explanation": "No timetable or transport feature source is installed.",
    },
    {
        "id": "journey-routes",
        "label": "Journey routes",
        "available": False,
        "enabled": False,
        "explanation": "Journey routing is not yet available.",
    },
)


def build_map_payload(
    connection,
    query: str = "",
    *,
    provider_results: list[dict[str, str]] | None = None,
    provider_requested: bool = False,
    provider_error: str = "",
) -> dict[str, object]:
    places = canonical_map_places(connection)
    search_results, selections = map_search_results(
        connection, query, places, provider_results or []
    )
    provider_state = "disabled"
    provider_explanation = (
        "Online place search is off. No search text was transmitted."
    )
    if provider_requested and provider_error:
        provider_state = "error"
        provider_explanation = (
            "OpenStreetMap Nominatim could not be reached. Canonical results remain available."
        )
    elif provider_requested:
        provider_state = "available"
        provider_explanation = (
            "This search text was sent to OpenStreetMap Nominatim; canonical names, notes and relationships were not added."
        )
    return {
        "defaultCenter": DEFAULT_CENTER,
        "baseViews": list(MAP_BASE_VIEWS),
        "layers": [layer.__dict__ for layer in MAP_LAYERS],
        "contextLayers": list(MAP_CONTEXT_LAYERS),
        "places": places,
        "query": query.strip(),
        "searchResults": search_results,
        "selections": selections,
        "providerStatus": {
            "requested": provider_requested,
            "state": provider_state,
            "name": "OpenStreetMap Nominatim",
            "execution": "Online",
            "attribution": "© OpenStreetMap contributors",
            "explanation": provider_explanation,
        },
        "viewportUrl": "/map/viewport",
        "viewportLimit": MAX_VIEWPORT_PLACES,
    }


def canonical_map_places(connection) -> list[dict[str, object]]:
    places_by_id: dict[str, dict[str, object]] = {}
    locations_by_id: dict[int, tuple[EntityRecord, tuple[float, float] | None, object]] = {}
    location_definition = DEFINITIONS_BY_SLUG["locations"]

    for location in list_entities(connection, location_definition):
        place = location_place_context(connection, location.id)
        coordinates = (
            place.representative_point.point
            if place.representative_point is not None
            else None
        )
        locations_by_id[location.id] = (location, coordinates, place)
        if coordinates is None:
            continue
        place_payload = canonical_place_payload(location, coordinates, place)
        place_payload["records"].append(
            canonical_record_payload(location, "locations")
        )
        places_by_id[place_payload["id"]] = place_payload

    asset_definition = DEFINITIONS_BY_SLUG["assets"]
    for asset in list_entities(connection, asset_definition):
        coordinates = entity_coordinates(asset)
        if coordinates is None:
            continue
        latitude, longitude = coordinates
        place_id = f"asset-coordinate:{asset.id}"
        places_by_id[place_id] = {
            "id": place_id,
            "kind": "canonical",
            "locationId": None,
            "title": f"{asset.title} coordinates",
            "address": "",
            "latitude": latitude,
            "longitude": longitude,
            "geometryConfidence": "Current Asset coordinates",
            "geometrySource": "Project E",
            "addressInheritedFrom": None,
            "sourceLabel": "Project E · Local",
            "coverageState": "Canonical Asset coordinates",
            "records": [canonical_record_payload(asset, "assets")],
        }

    for relationship in list_relationships(connection):
        relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(relationship.type_key)
        if (
            relationship.status != "active"
            or relationship_type is None
            or relationship_type.category != "Location"
        ):
            continue
        linked_entity, location = relationship_location_pair(relationship.source, relationship.target)
        if linked_entity is None or location is None:
            continue
        stored = locations_by_id.get(location.id)
        if stored is None:
            place = location_place_context(connection, location.id)
            coordinates = (
                place.representative_point.point
                if place.representative_point is not None
                else None
            )
            location_record = location
        else:
            location_record, coordinates, place = stored
        if coordinates is None:
            continue
        layer_id = layer_id_for_entity_type(linked_entity.type)
        if layer_id:
            place_id = f"location:{location_record.id}"
            place_payload = places_by_id.setdefault(
                place_id,
                canonical_place_payload(location_record, coordinates, place),
            )
            existing_ids = {
                int(record["entityId"]) for record in place_payload["records"]
            }
            if linked_entity.id not in existing_ids:
                place_payload["records"].append(
                    canonical_record_payload(linked_entity, layer_id)
                )

    places = sorted(
        places_by_id.values(), key=lambda item: (str(item["title"]).casefold(), str(item["id"]))
    )
    place_counts: dict[int, int] = {}
    for place in places:
        unique_ids = {int(record["entityId"]) for record in place["records"]}
        for entity_id in unique_ids:
            place_counts[entity_id] = place_counts.get(entity_id, 0) + 1
    layer_order = {layer.id: index for index, layer in enumerate(MAP_LAYERS)}
    for place in places:
        place["records"].sort(
            key=lambda record: (
                layer_order.get(str(record["layerId"]), len(layer_order)),
                str(record["title"]).casefold(),
                int(record["entityId"]),
            )
        )
        for record in place["records"]:
            record["placeCount"] = place_counts[int(record["entityId"])]
        place["recordCount"] = len(place["records"])
        place["layerIds"] = sorted(
            {str(record["layerId"]) for record in place["records"]},
            key=lambda layer_id: layer_order.get(layer_id, len(layer_order)),
        )
    return places


def canonical_place_payload(
    location: EntityRecord, coordinates: tuple[float, float], place_context
) -> dict[str, object]:
    latitude, longitude = coordinates
    address = (
        place_context.display_address.display_text
        if place_context.display_address is not None
        else ""
    )
    representative_point = place_context.representative_point
    return {
        "id": f"location:{location.id}",
        "kind": "canonical",
        "locationId": location.id,
        "title": location.title,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "geometryConfidence": representative_point.confidence if representative_point else "",
        "geometrySource": representative_point.source_name if representative_point else "",
        "addressInheritedFrom": place_context.inherited_address_location_id,
        "sourceLabel": "Project E · Local",
        "coverageState": "Canonical Location",
        "records": [],
    }


def canonical_record_payload(entity: EntityRecord, layer_id: str) -> dict[str, object]:
    return {
        "entityId": entity.id,
        "entityType": entity.type,
        "entityLabel": entity.definition.singular,
        "title": entity.title,
        "layerId": layer_id,
        "url": f"/{entity.slug}/{entity.id}",
    }


def map_search_results(
    connection,
    query: str,
    places: list[dict[str, object]],
    provider_results: list[dict[str, str]],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    query = query.strip()
    selections = {str(place["id"]): place for place in places}
    if not query:
        return [], selections

    places_by_entity: dict[int, list[dict[str, object]]] = {}
    for place in places:
        for record in place["records"]:
            places_by_entity.setdefault(int(record["entityId"]), []).append(place)

    canonical_results = []
    for result in search_entities(connection, query):
        entity = result["entity"]
        matched_places = places_by_entity.get(entity.id, [])
        selection_key = str(matched_places[0]["id"]) if matched_places else f"entity:{entity.id}"
        if not matched_places:
            selections[selection_key] = {
                "id": selection_key,
                "kind": "canonical-unmapped",
                "title": entity.title,
                "address": "",
                "latitude": None,
                "longitude": None,
                "geometryConfidence": "",
                "geometrySource": "",
                "sourceLabel": "Project E · Local",
                "coverageState": "Canonical record without a mapped Location",
                "records": [canonical_record_payload(entity, layer_id_for_entity_type(entity.type) or "")],
                "recordCount": 1,
                "layerIds": [layer_id_for_entity_type(entity.type) or ""],
            }
        lowered_title = entity.title.casefold()
        lowered_query = query.casefold()
        if lowered_title == lowered_query:
            rank = 0
        elif lowered_title.startswith(lowered_query):
            rank = 1
        elif lowered_query in lowered_title:
            rank = 2
        else:
            rank = 3
        canonical_results.append(
            {
                "id": f"canonical:{entity.id}",
                "group": "canonical",
                "kind": "canonical",
                "title": entity.title,
                "typeLabel": entity.definition.singular,
                "sourceLabel": "Project E · Local",
                "coverageState": (
                    f"Mapped at {len(matched_places)} canonical place{'s' if len(matched_places) != 1 else ''}"
                    if matched_places
                    else "No mapped Location"
                ),
                "selectionKey": selection_key,
                "latitude": matched_places[0]["latitude"] if matched_places else None,
                "longitude": matched_places[0]["longitude"] if matched_places else None,
                "url": f"/{entity.slug}/{entity.id}",
                "rank": rank,
            }
        )
    canonical_results.sort(
        key=lambda item: (int(item["rank"]), str(item["title"]).casefold(), str(item["id"]))
    )

    coordinate_results: list[dict[str, object]] = []
    coordinate = parse_coordinate_query(query)
    if coordinate is not None:
        latitude, longitude = coordinate
        selection_key = f"coordinate:{latitude:.6f},{longitude:.6f}"
        selection = {
            "id": selection_key,
            "kind": "coordinate",
            "title": "Entered coordinates",
            "address": "",
            "latitude": latitude,
            "longitude": longitude,
            "geometryConfidence": "Deliberately entered",
            "geometrySource": "Current search",
            "sourceLabel": "Entered coordinates · Local",
            "coverageState": "No basemap or provider coverage implied",
            "records": [],
            "recordCount": 0,
            "layerIds": [],
        }
        selections[selection_key] = selection
        coordinate_results.append(
            {
                "id": selection_key,
                "group": "coordinates",
                "kind": "coordinate",
                "title": f"{latitude:.6f}, {longitude:.6f}",
                "typeLabel": "Coordinates",
                "sourceLabel": "Current search · Local",
                "coverageState": "Coordinate only",
                "selectionKey": selection_key,
                "latitude": latitude,
                "longitude": longitude,
                "url": "",
                "rank": 0,
            }
        )

    online_results: list[dict[str, object]] = []
    for index, provider_result in enumerate(provider_results[:5]):
        latitude = parse_coordinate(provider_result.get("latitude", ""))
        longitude = parse_coordinate(provider_result.get("longitude", ""))
        if latitude is None or longitude is None:
            continue
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            continue
        label = provider_result.get("label", "").strip() or "Online place result"
        identity = provider_result.get("provider_reference", "") or f"{label}|{latitude}|{longitude}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        selection_key = f"provider:nominatim:{digest}"
        selection = {
            "id": selection_key,
            "kind": "provider",
            "title": label,
            "address": provider_result.get("formatted_address", label),
            "latitude": latitude,
            "longitude": longitude,
            "geometryConfidence": "Source reported",
            "geometrySource": "OpenStreetMap Nominatim",
            "sourceLabel": "OpenStreetMap Nominatim · Online",
            "coverageState": "External result; inspected only and not saved",
            "records": [],
            "recordCount": 0,
            "layerIds": [],
        }
        selections[selection_key] = selection
        online_results.append(
            {
                "id": f"online:{index}:{digest}",
                "group": "online",
                "kind": "provider",
                "title": label,
                "typeLabel": provider_result.get("feature_type", "Place") or "Place",
                "sourceLabel": "OpenStreetMap Nominatim · Online",
                "coverageState": "External result; not saved",
                "selectionKey": selection_key,
                "latitude": latitude,
                "longitude": longitude,
                "url": "",
                "rank": index,
            }
        )

    return canonical_results + coordinate_results + online_results, selections


def parse_coordinate_query(query: str) -> tuple[float, float] | None:
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*[, ]\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*",
        query,
    )
    if match is None:
        return None
    latitude = parse_coordinate(match.group(1))
    longitude = parse_coordinate(match.group(2))
    if latitude is None or longitude is None:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def build_map_viewport_payload(
    connection,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    layer_ids: set[str] | None = None,
    request_token: str = "",
) -> dict[str, object]:
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Viewport bounds are invalid.")
    enabled_layers = (
        {layer.id for layer in MAP_LAYERS if layer.enabled}
        if layer_ids is None
        else layer_ids
    )
    valid_layers = {layer.id for layer in MAP_LAYERS}
    enabled_layers = enabled_layers & valid_layers
    places = [
        place
        for place in canonical_map_places(connection)
        if west <= float(place["longitude"]) <= east
        and south <= float(place["latitude"]) <= north
        and enabled_layers.intersection(set(place["layerIds"]))
    ]
    total = len(places)
    return {
        "requestToken": request_token[:80],
        "source": "Project E canonical records",
        "execution": "Local",
        "places": places[:MAX_VIEWPORT_PLACES],
        "total": total,
        "truncated": total > MAX_VIEWPORT_PLACES,
        "limit": MAX_VIEWPORT_PLACES,
    }


def entity_coordinates(record: EntityRecord) -> tuple[float, float] | None:
    latitude = parse_coordinate(record.metadata.get("latitude", ""))
    longitude = parse_coordinate(record.metadata.get("longitude", ""))
    if latitude is None or longitude is None:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def relationship_location_pair(source: EntityRecord, target: EntityRecord) -> tuple[EntityRecord | None, EntityRecord | None]:
    if source.type == "location" and target.type != "location":
        return target, source
    if target.type == "location" and source.type != "location":
        return source, target
    return None, None


def layer_id_for_entity_type(entity_type: str) -> str | None:
    for layer in MAP_LAYERS:
        if layer.entity_type == entity_type:
            return layer.id
    return None


def parse_coordinate(value: str) -> float | None:
    try:
        if value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class Geocoder:
    name = "none"

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        return []


class NominatimGeocoder(Geocoder):
    name = "OpenStreetMap Nominatim"
    endpoint = "https://nominatim.openstreetmap.org/search"

    def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        if not query.strip():
            return []
        params = urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "addressdetails": "1",
                "limit": str(limit),
            }
        )
        request = Request(
            f"{self.endpoint}?{params}",
            headers={"User-Agent": "OperationEddy/0.1 local-first address lookup"},
        )
        with urlopen(request, timeout=5) as response:
            raw_results = json.loads(response.read().decode("utf-8"))
        return [normalise_nominatim_result(result) for result in raw_results]


def normalise_nominatim_result(result: dict[str, object]) -> dict[str, str]:
    address = result.get("address") if isinstance(result.get("address"), dict) else {}
    road_parts = [
        str(address.get("house_number", "")).strip(),
        str(address.get("road") or address.get("pedestrian") or address.get("footway") or "").strip(),
    ]
    address_line_1 = " ".join(part for part in road_parts if part)
    suburb = str(
        address.get("suburb")
        or address.get("city_district")
        or address.get("neighbourhood")
        or ""
    )
    city = str(
        address.get("city")
        or address.get("town")
        or address.get("village")
        or ""
    )
    return {
        "label": str(result.get("display_name", "")),
        "formatted_address": str(result.get("display_name", "")),
        "address_line_1": address_line_1,
        "address_line_2": "",
        "suburb": suburb,
        "city": city,
        "state": str(address.get("state") or address.get("region") or ""),
        "post_code": str(address.get("postcode", "")),
        "country": str(address.get("country", "")),
        "latitude": str(result.get("lat", "")),
        "longitude": str(result.get("lon", "")),
        "feature_type": str(result.get("type") or result.get("category") or "Place"),
        "provider_reference": (
            f"{result.get('osm_type', '')}:{result.get('osm_id', '')}"
            if result.get("osm_id")
            else ""
        ),
        "address_confidence": "Source reported",
        "address_source_name": "OpenStreetMap Nominatim",
        "address_source_reference": "",
        "address_source_version": "",
        "geometry_confidence": "Source reported",
        "geometry_source_name": "OpenStreetMap Nominatim",
        "geometry_source_reference": "",
        "geometry_source_version": "",
    }


def geocoder() -> Geocoder:
    return NominatimGeocoder()
