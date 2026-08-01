import tempfile
import unittest
from pathlib import Path

from app.http_server import HttpServerConfig, configured_handler
from app.web import EddyRequestHandler


class HttpServerConfigurationTests(unittest.TestCase):
    def test_each_server_gets_isolated_paths_without_mutating_base_handler(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = HttpServerConfig(
                root / "first.sqlite3",
                root / "first-documents",
                root / "first-backups",
                root / "first-staging",
            )
            second = HttpServerConfig(
                root / "second.sqlite3",
                root / "second-documents",
                root / "second-backups",
                root / "second-staging",
            )
            original_database_path = EddyRequestHandler.database_path

            first_handler = configured_handler(EddyRequestHandler, first)
            second_handler = configured_handler(EddyRequestHandler, second)

        self.assertEqual(first.database_path, first_handler.database_path)
        self.assertEqual(second.database_path, second_handler.database_path)
        self.assertNotEqual(first_handler.database_path, second_handler.database_path)
        self.assertEqual(original_database_path, EddyRequestHandler.database_path)


if __name__ == "__main__":
    unittest.main()
