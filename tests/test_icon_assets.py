import threading
import unittest
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from app.view_pages.icons import DOMAIN_ICONS, icon
from app.view_pages.layout import layout
from app.web import EddyRequestHandler


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "app" / "static" / "icons"


class IconAssetTests(unittest.TestCase):
    def test_initial_icon_set_is_coherent_local_svg(self) -> None:
        required = {
            "e-mark", "home", "information", "connections", "system", "search",
            "super-key", "add", "edit", "delete", "overflow", "close", "warning",
            "people", "organisation", "location", "project", "document", "asset",
            "relationships", "timeline", "map",
        }
        self.assertEqual({path.stem for path in ICON_DIR.glob("*.svg")}, required)
        for path in ICON_DIR.glob("*.svg"):
            root = ET.parse(path).getroot()
            self.assertEqual(root.attrib.get("viewBox"), "0 0 24 24")
            source = path.read_text()
            if "stroke=" in source:
                self.assertIn('stroke-linecap="round"', source)

    def test_layout_uses_named_brand_and_decorative_labelled_icons(self) -> None:
        html = layout("Icons", "<h1>Icons</h1>", active_slug="people")

        self.assertIn('src="/static/icons/e-mark.svg" alt="Project E"', html)
        self.assertIn('<span class="brand-name">Project E</span>', html)
        self.assertIn('src="/static/icons/people.svg" alt="" aria-hidden="true"', html)
        self.assertIn('src="/static/icons/search.svg" alt="" aria-hidden="true"', html)
        self.assertNotIn("Operation Eddy", html)
        self.assertEqual(set(DOMAIN_ICONS), {"people", "organisations", "locations", "projects", "documents", "assets"})

    def test_brand_mark_is_the_tilted_block_e(self) -> None:
        root = ET.parse(ICON_DIR / "e-mark.svg").getroot()
        path = next(child for child in root if child.tag.endswith("path"))

        self.assertEqual(root.attrib.get("fill"), "currentColor")
        self.assertEqual(path.attrib.get("transform"), "rotate(-38 12 12)")

    def test_icon_helper_supports_meaningful_and_decorative_icons(self) -> None:
        self.assertIn('alt="Add relationship"', icon("add", "Add relationship"))
        self.assertIn('alt="" aria-hidden="true"', icon("add"))

    def test_static_handler_serves_only_valid_existing_svg_assets(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/static"
            with urlopen(f"{base}/icons/e-mark.svg", timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
                self.assertIn(b'viewBox="0 0 24 24"', response.read())
            with urlopen(f"{base}/shell.js", timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "text/javascript")
                self.assertIn(b"sessionStorage", response.read())
            with urlopen(f"{base}/super-key.js", timeout=5) as response:
                self.assertEqual(response.headers.get_content_type(), "text/javascript")
                self.assertIn(b"contextualAliases", response.read())
            with self.assertRaises(HTTPError) as invalid:
                urlopen(f"{base}/icons/../styles.svg", timeout=5)
            self.assertEqual(invalid.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
