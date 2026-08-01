import unittest

from app.entities import DEFINITIONS_BY_SLUG, EntityRecord
from app import views


def record(slug, metadata):
    definition = DEFINITIONS_BY_SLUG[slug]
    return EntityRecord(7, definition, "Example", "", "Notes", "now", "now", "now", False, metadata)


class DomainPrototypeTests(unittest.TestCase):
    def test_document_leads_with_safe_file_actions_and_domain_facts(self):
        html = views.entity_detail_page(record("documents", {"document_type": "Contract", "identifier": "C-7", "file_name": "terms.txt", "mime_type": "text/plain"}), [])
        self.assertLess(html.index("Open</a>"), html.index("Purpose</dt>"))
        self.assertIn('/download?open=1', html)
        self.assertIn('download>Download</a>', html)
        self.assertNotIn("Stored file path", html)
        self.assertNotIn("<h2>Metadata</h2>", html)

    def test_unsupported_document_offers_download_without_open(self):
        html = views.entity_detail_page(record("documents", {"file_name": "archive.bin", "mime_type": "application/octet-stream"}), [])
        self.assertIn('download>Download</a>', html)
        self.assertNotIn('>Open</a>', html)

    def test_project_leads_with_status_and_milestones(self):
        html = views.entity_detail_page(record("projects", {"status": "Active", "project_type": "Work", "started_at": "2026-01-01", "target_date": "2026-12-31"}), [])
        self.assertLess(html.index("<h2>Status</h2>"), html.index("<h2>Milestones</h2>"))
        self.assertLess(html.index("<h2>Milestones</h2>"), html.index("Project type</dt>"))
        self.assertNotIn("Related Entities", html)


if __name__ == "__main__":
    unittest.main()
