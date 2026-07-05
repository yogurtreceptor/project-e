import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from app.db import connect, create_entity, get_entity_by_id, initialise_database
from app.entities import DEFINITIONS_BY_TYPE
from app.geo import NominatimGeocoder, build_map_payload


class OfflineOperationTests(unittest.TestCase):
    def test_wan_failure_does_not_affect_canonical_records_or_local_map_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "offline.sqlite3"
            initialise_database(database_path)
            with connect(database_path) as connection:
                entity_id = create_entity(
                    connection,
                    DEFINITIONS_BY_TYPE["location"],
                    {
                        "display_name": "Offline Place",
                        "latitude": "-27.4698",
                        "longitude": "153.0251",
                    },
                )
            with patch("app.geo.urlopen", side_effect=URLError("offline")):
                with self.assertRaises(URLError):
                    NominatimGeocoder().search("Offline Place")
            with connect(database_path) as connection:
                self.assertEqual(
                    "Offline Place", get_entity_by_id(connection, entity_id).title
                )
                payload = build_map_payload(connection)
            self.assertEqual("Offline Place", payload["markers"][0]["title"])


if __name__ == "__main__":
    unittest.main()
