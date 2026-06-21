import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.db import list_entities, list_relationships
from app.entities import DEFINITIONS_BY_SLUG, EntityRecord


DEFAULT_CENTER = {"latitude": -27.4698, "longitude": 153.0251, "zoom": 11}


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
)


def build_map_payload(connection) -> dict[str, object]:
    markers = []
    locations_by_id = {}
    location_definition = DEFINITIONS_BY_SLUG["locations"]

    for location in list_entities(connection, location_definition):
        coordinates = entity_coordinates(location)
        locations_by_id[location.id] = (location, coordinates)
        if coordinates is None:
            continue
        markers.append(marker_payload(location, location, coordinates, "locations"))

    asset_definition = DEFINITIONS_BY_SLUG["assets"]
    for asset in list_entities(connection, asset_definition):
        coordinates = entity_coordinates(asset)
        if coordinates is None:
            continue
        markers.append(marker_payload(asset, asset, coordinates, "assets"))

    for relationship in list_relationships(connection):
        if relationship.type_key != "located_at":
            continue
        linked_entity, location = relationship_location_pair(relationship.source, relationship.target)
        if linked_entity is None or location is None:
            continue
        location_record, coordinates = locations_by_id.get(location.id, (location, entity_coordinates(location)))
        if coordinates is None:
            continue
        layer_id = layer_id_for_entity_type(linked_entity.type)
        if layer_id:
            markers.append(marker_payload(linked_entity, location_record, coordinates, layer_id))

    return {
        "defaultCenter": DEFAULT_CENTER,
        "layers": [layer.__dict__ for layer in MAP_LAYERS],
        "markers": markers,
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


def marker_payload(
    entity: EntityRecord,
    location: EntityRecord,
    coordinates: tuple[float, float],
    layer_id: str,
) -> dict[str, object]:
    latitude, longitude = coordinates
    address = location.metadata.get("formatted_address") or ", ".join(
        part
        for part in (
            location.metadata.get("address_line_1", ""),
            location.metadata.get("locality", ""),
            location.metadata.get("region", ""),
            location.metadata.get("country", ""),
        )
        if part
    )
    return {
        "id": f"{layer_id}-{entity.id}",
        "layerId": layer_id,
        "entityId": entity.id,
        "entityType": entity.type,
        "title": entity.title,
        "entityLabel": entity.definition.singular,
        "locationTitle": location.title,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "url": f"/{entity.slug}/{entity.id}",
    }


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
    locality = str(
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("suburb")
        or ""
    )
    return {
        "label": str(result.get("display_name", "")),
        "formatted_address": str(result.get("display_name", "")),
        "address_line_1": address_line_1,
        "address_line_2": str(address.get("neighbourhood", "")),
        "locality": locality,
        "region": str(address.get("state") or address.get("region") or ""),
        "postal_code": str(address.get("postcode", "")),
        "country": str(address.get("country", "")),
        "latitude": str(result.get("lat", "")),
        "longitude": str(result.get("lon", "")),
        "geocoding_source": "OpenStreetMap Nominatim",
    }


def geocoder() -> Geocoder:
    return NominatimGeocoder()
