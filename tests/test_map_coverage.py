import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.db import connect
from app.map_coverage_service import assess_map_coverage
from app.spatial_pack import (
    activate_staged_spatial_pack,
    inspect_and_stage_spatial_pack,
    spatial_pack_status,
)
from tests.database_test_support import initialise_test_database
from tests.spatial_pack_test_support import fictional_spatial_pack
from tests.web_test_support import make_test_server


def activate_pack(root: Path) -> None:
    preview = inspect_and_stage_spatial_pack(fictional_spatial_pack(), root)
    activate_staged_spatial_pack(preview.token, root)


class MapCoverageRecommendationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.pack_root = self.root / "spatial-packs"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_core_context_and_outside_points_use_reviewed_pack_geometry(self) -> None:
        activate_pack(self.pack_root)

        core = assess_map_coverage(
            self.pack_root,
            selection_title="Core place",
            latitude=-28.0,
            longitude=153.5,
        )
        context = assess_map_coverage(
            self.pack_root,
            selection_title="Bordering suburb",
            latitude=-28.0,
            longitude=153.05,
        )
        boundary = assess_map_coverage(
            self.pack_root,
            selection_title="Exact reviewed boundary",
            latitude=-28.0,
            longitude=153.1,
        )
        outside = assess_map_coverage(
            self.pack_root,
            selection_title="Adjoining authority",
            latitude=-28.0,
            longitude=152.9,
        )

        self.assertEqual("core", core.state)
        self.assertEqual("Refresh the current region only if needed", core.scope_label)
        self.assertEqual("context", context.state)
        self.assertGreater(context.distance_to_core_km, 4)
        self.assertIn("bordering suburb or adjoining authority", context.scope_explanation)
        self.assertEqual("core", boundary.state)
        self.assertEqual("outside", outside.state)
        self.assertGreater(outside.distance_to_bounds_km, 9)
        self.assertIn("common-snapshot union", outside.scope_explanation)

    def test_recommendation_explains_measured_size_network_and_sources(self) -> None:
        activate_pack(self.pack_root)
        recommendation = assess_map_coverage(
            self.pack_root,
            selection_title="Bordering suburb",
            latitude=-28.0,
            longitude=153.05,
        )

        self.assertGreater(recommendation.installed_bytes, 0)
        self.assertGreater(recommendation.bounds_area_km2, 0)
        self.assertIn("baseline, not a linear estimate", recommendation.size_explanation)
        self.assertIn("made no network request", recommendation.network_explanation)
        self.assertEqual(
            ["Fictional open map source", "Fictional transit source"],
            [item["label"] for item in recommendation.sources],
        )
        self.assertIn("own reviewed boundary source", recommendation.source_explanation)

        active = spatial_pack_status(self.pack_root).active
        (active.directory / "coverage.geojson").write_text("{}", encoding="utf-8")
        corrupted = assess_map_coverage(
            self.pack_root,
            selection_title="Bordering suburb",
            latitude=-28.0,
            longitude=153.05,
        )
        self.assertEqual("unavailable", corrupted.state)
        self.assertIn("pack state is invalid", corrupted.summary)

    def test_no_pack_recommends_bounded_initial_candidate_without_implied_source(self) -> None:
        recommendation = assess_map_coverage(
            self.pack_root,
            selection_title="Uncovered point",
            latitude=-27.5,
            longitude=153.0,
        )

        self.assertEqual("unavailable", recommendation.state)
        self.assertEqual("Initial regional candidate", recommendation.scope_label)
        self.assertEqual((), recommendation.sources)
        self.assertIn("No source is implied", recommendation.source_explanation)
        self.assertIn("512 MB inspection limit", recommendation.size_explanation)

    def test_invalid_coordinates_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Latitude is invalid"):
            assess_map_coverage(
                self.pack_root,
                selection_title="Invalid",
                latitude="not-a-coordinate",
                longitude="153",
            )


class MapCoverageHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "database.sqlite3"
        self.pack_root = self.root / "spatial-packs"
        initialise_test_database(self.database_path)
        activate_pack(self.pack_root)
        self.server = make_test_server(
            self.database_path, spatial_pack_dir=self.pack_root
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def get(self, path: str):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=10
        )
        connection.request("GET", path)
        response = connection.getresponse()
        content = response.read()
        status = response.status
        connection.close()
        return status, content

    def test_context_recommendation_retains_selection_without_mutation_or_network_action(self) -> None:
        return_to = "/map?q=Bordering&selected=coordinate%3A-28.000000%2C153.050000"
        path = "/map/coverage?" + urlencode(
            {
                "title": "Bordering suburb",
                "latitude": "-28",
                "longitude": "153.05",
                "return_to": return_to,
            }
        )
        with connect(self.database_path) as connection:
            before = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

        status, page = self.get(path)

        self.assertEqual(200, status)
        self.assertIn(b"Inside map context, outside reviewed core", page)
        self.assertIn(b"Bordering suburb", page)
        self.assertIn(b"Nothing was fetched, built, installed", page)
        self.assertIn(return_to.replace("&", "&amp;").encode(), page)
        with connect(self.database_path) as connection:
            self.assertEqual(
                before,
                connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
            )

    def test_invalid_coordinate_returns_review_error(self) -> None:
        status, page = self.get(
            "/map/coverage?title=Bad&latitude=999&longitude=153&return_to=https://example.test"
        )
        self.assertEqual(400, status)
        self.assertIn(b"Latitude is invalid for coverage review", page)
        self.assertIn(b'href="/map"', page)


if __name__ == "__main__":
    unittest.main()
