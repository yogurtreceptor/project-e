import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app import views
from app.db import connect, create_entity, create_relationship, count_entities
from app.entities import DEFINITIONS_BY_TYPE
from app.geo import build_map_payload, build_map_viewport_payload
from tests.database_test_support import initialise_test_database
from tests.web_test_support import make_test_server, read_application_css


class MapWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "map-workspace.sqlite3"
        initialise_test_database(self.database_path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_location(
        self, connection, name: str, latitude: float, longitude: float
    ) -> int:
        return create_entity(
            connection,
            DEFINITIONS_BY_TYPE["location"],
            {
                "display_name": name,
                "formatted_address": f"{name}, Fiction QLD 4999",
                "latitude": str(latitude),
                "longitude": str(longitude),
                "address_confidence": "User confirmed",
                "geometry_confidence": "User confirmed",
            },
        )

    def create_person(self, connection, name: str) -> int:
        first, last = name.split(" ", 1)
        return create_entity(
            connection,
            DEFINITIONS_BY_TYPE["person"],
            {"display_name": name, "given_name": first, "family_name": last},
        )

    def link_to_location(self, connection, entity_id: int, location_id: int) -> None:
        create_relationship(
            connection,
            {
                "source_entity_id": str(entity_id),
                "target_entity_id": str(location_id),
                "type": "located_at",
                "status": "active",
            },
        )

    def create_dense_shared_place_fixture(self) -> tuple[int, int]:
        with connect(self.database_path) as connection:
            first_location_id = 0
            repeated_person_id = 0
            for place_index in range(24):
                location_id = self.create_location(
                    connection,
                    f"Fictional shared place {place_index:02d}",
                    -28.20 + (place_index // 8) * 0.03,
                    153.20 + (place_index % 8) * 0.03,
                )
                if place_index == 0:
                    first_location_id = location_id
                for record_index in range(6):
                    if record_index % 2:
                        entity_id = create_entity(
                            connection,
                            DEFINITIONS_BY_TYPE["organisation"],
                            {
                                "display_name": f"Fictional organisation {place_index:02d}-{record_index}",
                                "organisation_type": "Community group",
                            },
                        )
                    else:
                        entity_id = self.create_person(
                            connection,
                            f"Fictional{place_index:02d}{record_index} Example",
                        )
                    self.link_to_location(connection, entity_id, location_id)
                    if place_index == 0 and record_index == 0:
                        repeated_person_id = entity_id
                if place_index == 1:
                    self.link_to_location(connection, repeated_person_id, location_id)
        return first_location_id, repeated_person_id

    def test_dense_shared_places_use_one_group_and_explain_multi_place_records(self) -> None:
        first_location_id, repeated_person_id = self.create_dense_shared_place_fixture()

        with connect(self.database_path) as connection:
            payload = build_map_payload(connection)

        self.assertEqual(24, len(payload["places"]))
        first = next(
            place for place in payload["places"]
            if place["locationId"] == first_location_id
        )
        self.assertEqual(7, first["recordCount"])
        self.assertEqual(
            {"locations", "organisations", "people"}, set(first["layerIds"])
        )
        repeated = next(
            record
            for record in first["records"]
            if record["entityId"] == repeated_person_id
        )
        self.assertEqual(2, repeated["placeCount"])
        self.assertEqual(
            2,
            sum(
                any(record["entityId"] == repeated_person_id for record in place["records"])
                for place in payload["places"]
            ),
        )

    def test_canonical_coordinate_and_enabled_online_results_have_stable_order(self) -> None:
        with connect(self.database_path) as connection:
            self.create_location(
                connection, "Coordinate -28.0, 153.4 example", -28.0, 153.4
            )
            before_counts = count_entities(connection)
            payload = build_map_payload(
                connection,
                "-28.0, 153.4",
                provider_results=[
                    {
                        "label": "Fictional provider result",
                        "formatted_address": "Provider Avenue, Fiction",
                        "latitude": "-28.01",
                        "longitude": "153.41",
                        "feature_type": "library",
                        "provider_reference": "node:12345",
                    }
                ],
                provider_requested=True,
            )
            search_snapshot = tuple(
                (result["group"], result["title"])
                for result in payload["searchResults"]
            )
            build_map_viewport_payload(
                connection,
                west=153.35,
                south=-28.05,
                east=153.45,
                north=-27.95,
                layer_ids={"locations"},
                request_token="pan-9",
            )
            after_counts = count_entities(connection)

        self.assertEqual(
            ["canonical", "coordinates", "online"],
            [result["group"] for result in payload["searchResults"]],
        )
        self.assertEqual(search_snapshot, tuple(
            (result["group"], result["title"])
            for result in payload["searchResults"]
        ))
        self.assertEqual(before_counts, after_counts)
        self.assertEqual("available", payload["providerStatus"]["state"])
        self.assertIn("not saved", payload["searchResults"][-1]["coverageState"])

    def test_viewport_is_bounded_local_layer_filtered_and_echoes_request_token(self) -> None:
        with connect(self.database_path) as connection:
            location_id = self.create_location(
                connection, "Fictional viewport place", -28.0, 153.4
            )
            person_id = self.create_person(connection, "Viewport Example")
            self.link_to_location(connection, person_id, location_id)
            local = build_map_viewport_payload(
                connection,
                west=153.3,
                south=-28.1,
                east=153.5,
                north=-27.9,
                layer_ids={"people"},
                request_token="newest",
            )
            empty = build_map_viewport_payload(
                connection,
                west=153.3,
                south=-28.1,
                east=153.5,
                north=-27.9,
                layer_ids=set(),
            )

        self.assertEqual("Local", local["execution"])
        self.assertEqual("newest", local["requestToken"])
        self.assertEqual(1, local["total"])
        self.assertEqual([], empty["places"])
        with connect(self.database_path) as connection:
            with self.assertRaisesRegex(ValueError, "bounds"):
                build_map_viewport_payload(
                    connection,
                    west=154,
                    south=-28,
                    east=153,
                    north=-27,
                )

    def test_page_and_client_remove_automatic_wan_and_expose_accessible_state(self) -> None:
        with connect(self.database_path) as connection:
            self.create_location(
                connection, "Fictional accessible place", -28.0, 153.4
            )
            payload = build_map_payload(connection)
        html = views.map_page(payload)
        script = (Path(__file__).parents[1] / "app" / "static" / "map-workspace.js").read_text()
        css = read_application_css()

        self.assertNotIn("https://", html)
        self.assertNotIn("leaflet", html.lower())
        self.assertNotIn("tile.openstreetmap", html)
        self.assertIn('name="online" value="1">', html)
        self.assertIn("No search text was transmitted", html)
        self.assertIn('tabindex="0" aria-label="Pan and zoom canonical coordinate map"', html)
        self.assertIn("Canonical place</span>", html)
        self.assertIn("Selected place</span>", html)
        self.assertIn("Multiple nearby places</span>", html)
        self.assertIn("Text alternative to every canonical pin", html)
        self.assertIn("Blank map space never creates a pin", html)
        self.assertNotIn("Search this area", html)
        self.assertNotIn("Save as Location", html)
        self.assertIn("new AbortController()", script)
        self.assertIn("viewportController.abort()", script)
        self.assertIn("sequence !== requestSequence", script)
        self.assertIn("ArrowLeft", script)
        self.assertIn("payload.viewportUrl", script)
        self.assertNotIn("payload.query", script)
        self.assertIn(".map-pin.is-selected", css)
        self.assertIn("border-width: 4px", css)
        self.assertIn("@media (max-width: 1040px)", css)
        self.assertIn(".map-sidebar-collapsed", css)

    def test_provider_error_is_honest_and_preserves_canonical_results(self) -> None:
        with connect(self.database_path) as connection:
            self.create_location(
                connection, "Fictional offline library", -28.0, 153.4
            )
            payload = build_map_payload(
                connection,
                "Fictional offline library",
                provider_requested=True,
                provider_error="unavailable",
            )
        html = views.map_page(payload)

        self.assertEqual("error", payload["providerStatus"]["state"])
        self.assertEqual("canonical", payload["searchResults"][0]["group"])
        self.assertIn("could not be reached", html)
        self.assertIn("Canonical results remain available", html)
        self.assertIn("Basemap unavailable", html)


class MapWorkspaceHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "map-http.sqlite3"
        initialise_test_database(self.database_path)
        with connect(self.database_path) as connection:
            create_entity(
                connection,
                DEFINITIONS_BY_TYPE["location"],
                {
                    "display_name": "Fictional HTTP place",
                    "formatted_address": "1 HTTP Road, Fiction",
                    "latitude": "-28.0",
                    "longitude": "153.4",
                    "address_confidence": "User confirmed",
                    "geometry_confidence": "User confirmed",
                },
            )
        self.server = make_test_server(self.database_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def test_local_viewport_route_and_static_renderer_need_no_wan(self) -> None:
        query = urlencode(
            {
                "west": "153.3",
                "south": "-28.1",
                "east": "153.5",
                "north": "-27.9",
                "layers": "locations",
                "request": "17",
            }
        )
        with urlopen(f"{self.base_url}/map/viewport?{query}") as response:
            payload = json.loads(response.read())
        with urlopen(f"{self.base_url}/static/map-workspace.js") as response:
            script = response.read().decode("utf-8")

        self.assertEqual("17", payload["requestToken"])
        self.assertEqual("Local", payload["execution"])
        self.assertEqual("Fictional HTTP place", payload["places"][0]["title"])
        self.assertIn("AbortController", script)

    def test_map_does_not_call_provider_until_explicitly_requested_and_degrades(self) -> None:
        with patch("app.web.geocoder", side_effect=AssertionError("unexpected provider call")):
            with urlopen(f"{self.base_url}/map?q=Fictional+HTTP") as response:
                local_html = response.read().decode("utf-8")
        self.assertIn("No search text was transmitted", local_html)
        self.assertIn("Fictional HTTP place", local_html)

        class FailingProvider:
            def search(self, _query: str, limit: int = 5):
                raise URLError("fictional offline")

        with patch("app.web.geocoder", return_value=FailingProvider()):
            with urlopen(f"{self.base_url}/map?q=Fictional+HTTP&online=1") as response:
                degraded_html = response.read().decode("utf-8")
        self.assertIn("could not be reached", degraded_html)
        self.assertIn("Fictional HTTP place", degraded_html)

    def test_invalid_viewport_is_rejected_without_fallback(self) -> None:
        with self.assertRaises(HTTPError) as raised:
            urlopen(f"{self.base_url}/map/viewport?west=154&south=-28&east=153&north=-27")
        self.assertEqual(400, raised.exception.code)
        payload = json.loads(raised.exception.read())
        self.assertIn("bounded viewport", payload["error"])


if __name__ == "__main__":
    unittest.main()
