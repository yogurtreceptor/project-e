import unittest

from app import views


class SystemToolsViewTests(unittest.TestCase):
    def test_hub_links_all_maintenance_tools(self):
        html = views.system_tools_page()
        for href, label in (
            ("/search", "Search"),
            ("/data-quality", "Data Quality"),
            ("/taxonomies", "Taxonomies"),
            ("/recycle-bin", "Recycle Bin"),
        ):
            self.assertIn(f'href="{href}"', html)
            self.assertIn(f"<h2>{label}</h2>", html)

    def test_navigation_replaces_individual_tool_links_with_active_hub(self):
        html = views.layout("Tools", views.system_tools_page(), "system-tools")
        nav = html.split("<nav>", 1)[1].split("</nav>", 1)[0]
        self.assertIn('<a class="active" href="/system-tools">System Tools</a>', nav)
        self.assertNotIn('href="/taxonomies"', nav)
        self.assertNotIn('href="/data-quality"', nav)
        self.assertNotIn('href="/recycle-bin"', nav)
        self.assertNotIn('href="/search"', nav)
        self.assertIn('action="/search"', html)


if __name__ == "__main__":
    unittest.main()
