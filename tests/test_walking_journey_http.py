from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.db import connect, create_entity, get_mobility_profile, get_routing_policy
from app.entities import DEFINITIONS_BY_TYPE
from app.journey_contract import JourneySource
from app.routing_resources import LocalValhallaCapability, RoutingCapabilityStatus
from app.valhalla_adapter import ValhallaWalkingAdapter
from app.walking_journeys import (
    ensure_default_walk_profile,
    list_journey_endpoint_options,
)
from tests.database_test_support import initialise_test_database
from tests.test_valhalla_adapter import FakeValhallaTransport
from tests.web_test_support import make_test_server


class WalkingJourneyHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "walking-http.sqlite3"
        initialise_test_database(self.database_path)
        with connect(self.database_path) as connection:
            for name, longitude, latitude in (
                ("Fictional Route Origin", 153.4000, -27.9000),
                ("Fictional Route Destination", 153.4100, -27.9050),
            ):
                create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["location"],
                    {
                        "display_name": name,
                        "longitude": str(longitude),
                        "latitude": str(latitude),
                        "geometry_confidence": "User confirmed",
                        "address_confidence": "User confirmed",
                    },
                )
            ensure_default_walk_profile(connection)
            self.endpoints = list_journey_endpoint_options(connection)
        self.server = make_test_server(self.database_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    @staticmethod
    def capability(root: Path) -> LocalValhallaCapability:
        return LocalValhallaCapability(
            base_url="http://127.0.0.1:18081",
            provider_version="3.8.3",
            service_binary=root / "valhalla_service",
            service_config=root / "valhalla.json",
            service_binary_sha256="a" * 64,
            service_config_sha256="b" * 64,
            graph_path=root / "tiles.tar",
            graph_sha256="c" * 64,
            graph_bytes=1,
            coverage_key="fictional-gold-coast-streets",
            coverage_bbox=(153.0, -28.4, 153.7, -27.5),
            coverage_timezone="Australia/Brisbane",
            maximum_snap_distance_metres=100,
            compatible_spatial_pack_id="fictional-coast",
            compatible_spatial_pack_version="1",
            maximum_cache_entries=8,
            cache_fresh_seconds=3600,
            sources=(
                JourneySource("fictional-streets", "osm-v1", "Fictional snapshot"),
            ),
        )

    def test_planner_is_honest_when_no_local_router_is_activated(self) -> None:
        with urlopen(f"{self.base_url}/journeys/walk") as response:
            html = response.read().decode("utf-8")

        self.assertIn("No local walking-routing capability is activated", html)
        self.assertIn("Fictional Route Origin", html)
        self.assertIn("Regular walk · 5.00 km/h · provisional estimate", html)
        self.assertIn("Fast walk / jog · not available yet", html)
        self.assertIn("Run · not available yet", html)
        self.assertIn("Calculate walking journey", html)
        self.assertIn("disabled", html)

    def test_calculation_renders_text_and_overlay_then_reuses_bounded_cache(self) -> None:
        capability = self.capability(self.root)
        transport = FakeValhallaTransport()
        adapter = ValhallaWalkingAdapter(capability, transport=transport)
        journey_time = (datetime.now(UTC) + timedelta(hours=1)).astimezone().strftime(
            "%Y-%m-%dT%H:%M"
        )
        body = urlencode(
            {
                "origin": self.endpoints[0].value,
                "destination": self.endpoints[1].value,
                "time_kind": "depart_at",
                "journey_time": journey_time,
                "profile_key": "regular-walk",
                "preparation_minutes": "5",
                "arrival_minutes": "3",
                "alternatives": "1",
            }
        ).encode("utf-8")
        status = RoutingCapabilityStatus(
            "available", "Fictional local routing is ready.", capability
        )

        def calculate() -> str:
            request = Request(
                f"{self.base_url}/journeys/walk/plan",
                data=body,
                method="POST",
            )
            with urlopen(request) as response:
                return response.read().decode("utf-8")

        with (
            patch("app.web.routing_capability_status", return_value=status),
            patch("app.web.load_active_valhalla_capability", return_value=capability),
            patch("app.web.ValhallaWalkingAdapter", return_value=adapter),
        ):
            first_html = calculate()
            second_html = calculate()

        with connect(self.database_path) as connection:
            event_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM entities WHERE type='event'"
                ).fetchone()[0]
            )
        self.assertIn("Walking result", first_html)
        self.assertIn("New local calculation", first_html)
        self.assertIn('"journeyOverlay"', first_html)
        self.assertIn("No Event or journey history was created", first_html)
        self.assertIn("Fresh cached result", second_html)
        self.assertEqual(1, [path for path, _payload in transport.calls].count("/route"))
        self.assertEqual(0, event_count)

    def test_jog_and_run_are_rejected_by_the_http_contract(self) -> None:
        for profile_key in ("fast-walk", "run"):
            body = urlencode(
                {
                    "origin": self.endpoints[0].value,
                    "destination": self.endpoints[1].value,
                    "time_kind": "depart_at",
                    "journey_time": "2026-08-10T09:00",
                    "profile_key": profile_key,
                    "preparation_minutes": "0",
                    "arrival_minutes": "0",
                    "alternatives": "1",
                }
            ).encode("utf-8")
            with self.subTest(profile_key=profile_key):
                request = Request(
                    f"{self.base_url}/journeys/walk/plan",
                    data=body,
                    method="POST",
                )
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request)
                html = caught.exception.read().decode("utf-8")
                self.assertEqual(400, caught.exception.code)
                self.assertIn("Jog and Run are not enabled", html)

    def test_settings_explain_generic_speed_and_policy_enable_is_explicit(self) -> None:
        def post(path: str, data: dict[str, str]) -> str:
            request = Request(
                self.base_url + path,
                data=urlencode(data).encode("utf-8"),
                method="POST",
            )
            with urlopen(request) as response:
                return response.read().decode("utf-8")

        with urlopen(f"{self.base_url}/journeys/walk/settings") as response:
            settings_html = response.read().decode("utf-8")
        policy_html = post(
            "/journeys/walk/settings/avoid-steps", {"enabled": "1"}
        )

        with connect(self.database_path) as connection:
            profile = get_mobility_profile(connection, "regular-walk")
            policy = get_routing_policy(connection, "avoid-steps")
        self.assertIn("Why 5 km/h?", settings_html)
        self.assertIn("Provisional generic estimate", settings_html)
        self.assertIn('aria-disabled="true"', settings_html)
        self.assertIn("Avoid-steps preference enabled", policy_html)
        self.assertEqual(1, profile.revision)
        self.assertAlmostEqual(1.388889, profile.definition["speed_metres_per_second"])
        self.assertTrue(policy.is_enabled)


if __name__ == "__main__":
    unittest.main()
