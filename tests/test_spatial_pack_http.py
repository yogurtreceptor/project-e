import http.client
import json
import re
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

from app.db import connect
from app.spatial_pack import spatial_pack_status
from tests.database_test_support import initialise_test_database
from tests.spatial_pack_test_support import fictional_spatial_pack
from tests.web_test_support import make_test_server


class SpatialPackHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "database.sqlite3"
        self.pack_root = self.root / "spatial-packs"
        initialise_test_database(self.database_path)
        self.server = make_test_server(
            self.database_path, spatial_pack_dir=self.pack_root
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method: str, path: str, body: bytes = b"", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        content = response.read()
        result = response.status, dict(response.getheaders()), content
        connection.close()
        return result

    def test_preview_activation_map_resources_and_confirmed_removal(self) -> None:
        boundary = "project-e-fictional-boundary"
        bundle = fictional_spatial_pack()
        multipart = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="upload"; filename="fictional.zip"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        ).encode() + bundle + f"\r\n--{boundary}--\r\n".encode()

        status, _headers, preview_body = self.request(
            "POST",
            "/map/packs/preview",
            multipart,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        self.assertEqual(status, 200)
        preview_html = preview_body.decode()
        self.assertIn("Verified preview", preview_html)
        self.assertIn("No active data has changed", preview_html)
        self.assertIsNone(spatial_pack_status(self.pack_root).active)
        token = re.search(r'name="token" value="([0-9a-f]{32})"', preview_html)
        self.assertIsNotNone(token)

        form = urlencode({"token": token.group(1)}).encode()
        status, headers, _body = self.request(
            "POST",
            "/map/packs/activate",
            form,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/map/packs?saved=installed")
        active = spatial_pack_status(self.pack_root).active
        self.assertIsNotNone(active)

        status, _headers, manager_body = self.request("GET", "/map/packs")
        manager_html = manager_body.decode()
        self.assertEqual(status, 200)
        self.assertIn("Fictional Coast local map", manager_html)
        self.assertIn("Fictional Coast test bounds", manager_html)
        self.assertIn("Fictional map contributors", manager_html)
        self.assertIn("No previous version to roll back", manager_html)

        status, _headers, map_body = self.request("GET", "/map?q=Surfers")
        map_html = map_body.decode()
        self.assertEqual(status, 200)
        self.assertIn("Normal local map", map_html)
        self.assertIn("Installed map results", map_html)
        self.assertIn("Surfers Paradise", map_html)
        self.assertIn("maplibre-gl.css", map_html)

        status, headers, script = self.request(
            "GET", "/static/vendor/maplibre-6.2.0/maplibre-gl.mjs"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/javascript; charset=utf-8")
        self.assertIn(b"MapLibre GL JS", script[:200])

        status, headers, tile = self.request(
            "GET", f"/map/tiles/{active.activation_id}/0/0/0.pbf"
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Encoding"], "gzip")
        self.assertTrue(tile.startswith(b"\x1f\x8b"))

        status, _headers, transit_body = self.request(
            "GET",
            f"/map/packs/{active.activation_id}/public-transport.geojson",
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(transit_body)["features"][0]["properties"]["name"],
            "Broadbeach South station",
        )

        with connect(self.database_path) as connection:
            entity_count = connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        status, _headers, rejected = self.request(
            "POST",
            "/map/packs/remove",
            b"confirm=not-yet",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"Type REMOVE", rejected)
        self.assertIsNotNone(spatial_pack_status(self.pack_root).active)

        status, headers, _body = self.request(
            "POST",
            "/map/packs/remove",
            b"confirm=REMOVE",
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 303)
        self.assertEqual(headers["Location"], "/map/packs?saved=removed")
        self.assertIsNone(spatial_pack_status(self.pack_root).active)
        with connect(self.database_path) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
                entity_count,
            )


if __name__ == "__main__":
    unittest.main()
