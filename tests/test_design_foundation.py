import unittest
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from app.view_pages.layout import layout
from app.web import EddyRequestHandler


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"


class DesignFoundationTests(unittest.TestCase):
    def test_application_stylesheet_imports_single_foundation_entry_first(self) -> None:
        stylesheet = (STATIC_DIR / "styles.css").read_text()

        self.assertTrue(stylesheet.startswith('@import url("/static/foundation.css");'))
        self.assertEqual(stylesheet.count("foundation.css"), 1)
        self.assertTrue((STATIC_DIR / "foundation.css").is_file())

    def test_shared_layout_keeps_the_existing_application_stylesheet(self) -> None:
        html = layout("Foundation smoke", "<h1>Foundation smoke</h1>")

        self.assertIn('<link rel="stylesheet" href="/static/styles.css">', html)

    def test_foundation_file_is_allowed_by_static_handler(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/static/foundation.css",
                timeout=5,
            ) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "text/css")
                self.assertIn(b"Project E design foundation", response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_shared_stylesheet_has_balanced_blocks_and_defined_custom_properties(self) -> None:
        foundation = (STATIC_DIR / "foundation.css").read_text()
        stylesheet = (STATIC_DIR / "styles.css").read_text()
        combined = foundation + stylesheet

        self.assertEqual(combined.count("{"), combined.count("}"))
        self.assertNotIn("var(--ink)", combined)


if __name__ == "__main__":
    unittest.main()
