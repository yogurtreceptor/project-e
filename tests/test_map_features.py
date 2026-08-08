import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.db import connect, create_entity
from app.entities import DEFINITIONS_BY_TYPE
from app.map_feature_service import (
    add_map_feature_membership,
    clear_map_feature_list,
    create_map_feature_list,
    find_provider_promotion_matches,
    get_map_feature_list,
    list_map_feature_lists,
    list_map_feature_memberships,
    map_feature_membership_export,
    promote_provider_feature,
    provider_feature_from_form,
    remove_map_feature_membership,
)
from app.place_repository import location_place_context
from app.portability import apply_import_bundle, create_bundle
from app.spatial_pack import (
    activate_staged_spatial_pack,
    inspect_and_stage_spatial_pack,
    read_active_search_feature,
)
from tests.database_test_support import initialise_test_database
from tests.spatial_pack_test_support import fictional_spatial_pack
from tests.web_test_support import make_test_server


PACK_ID = "au-qld-fictional-coast"


def activate_pack(root: Path, version: str = "2026.08.01"):
    preview = inspect_and_stage_spatial_pack(
        fictional_spatial_pack(version), root
    )
    return activate_staged_spatial_pack(preview.token, root)


def provider_values(version: str = "2026.08.01") -> dict[str, str]:
    return {
        "provider_key": f"spatial-pack:{PACK_ID}",
        "feature_id": f"place:surfers:{version}",
        "feature_version": version,
        "title": "Tampered client title",
        "description": "Tampered client description",
        "feature_type": "Tampered",
        "source_name": "Tampered source",
        "source_layer": "tampered",
        "latitude": "-28.002",
        "longitude": "153.43",
        "formatted_address": "Not supplied by this pack",
    }


class MapFeatureServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database_path = self.root / "database.sqlite3"
        self.pack_root = self.root / "spatial-packs"
        initialise_test_database(self.database_path)
        activate_pack(self.pack_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_review_is_non_mutating_and_new_promotion_accepts_audited_assertions(self) -> None:
        feature = provider_feature_from_form(provider_values(), self.pack_root)
        self.assertEqual("Surfers Paradise", feature.title)
        self.assertEqual("Fictional suburb", feature.description)
        self.assertEqual("", feature.formatted_address)
        self.assertEqual(
            "Fictional Coast local map 2026.08.01 · Local", feature.source_name
        )

        with connect(self.database_path) as connection:
            before = connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            self.assertEqual([], find_provider_promotion_matches(connection, feature))
            after_review = connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            location_id, created = promote_provider_feature(
                connection,
                feature,
                choice="new",
                display_name="Surfers Paradise",
            )
            context = location_place_context(connection, location_id)
            audit_notes = {
                row[0]
                for row in connection.execute(
                    "SELECT notes FROM audit_events ORDER BY id"
                )
            }

        self.assertEqual(before, after_review)
        self.assertTrue(created)
        self.assertEqual([], list(context.addresses))
        self.assertEqual([153.43, -28.002], context.representative_point.coordinates)
        self.assertEqual("Source reported", context.representative_point.confidence)
        self.assertEqual(
            f"spatial-pack:{PACK_ID}", context.provider_references[0].provider_key
        )
        self.assertIn("Provider reference accepted for canonical Location", audit_notes)

    def test_reviewed_existing_match_adds_reference_without_moving_location(self) -> None:
        with connect(self.database_path) as connection:
            location_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["location"],
                {
                    "display_name": "Surfers Paradise",
                    "latitude": "-28.0018",
                    "longitude": "153.4301",
                    "geometry_confidence": "User confirmed",
                },
            )
            feature = provider_feature_from_form(provider_values(), self.pack_root)
            matches = find_provider_promotion_matches(connection, feature)
            self.assertEqual([location_id], [item.record.id for item in matches])
            self.assertTrue(
                any("within" in reason for reason in matches[0].reasons),
                matches[0].reasons,
            )
            returned_id, created = promote_provider_feature(
                connection,
                feature,
                choice=str(location_id),
                display_name="Ignored",
            )
            context = location_place_context(connection, location_id)

        self.assertEqual(location_id, returned_id)
        self.assertFalse(created)
        self.assertEqual([153.4301, -28.0018], context.representative_point.coordinates)
        self.assertEqual("User confirmed", context.representative_point.confidence)
        self.assertEqual(1, len(context.provider_references))

    def test_new_provider_version_reconciles_by_review_without_overwriting_assertions(self) -> None:
        first = provider_feature_from_form(provider_values(), self.pack_root)
        with connect(self.database_path) as connection:
            location_id, _created = promote_provider_feature(
                connection,
                first,
                choice="new",
                display_name="Surfers Paradise",
            )
            original = location_place_context(connection, location_id).representative_point

        activate_pack(self.pack_root, "2026.08.02")
        second = provider_feature_from_form(
            provider_values("2026.08.02"), self.pack_root
        )
        with connect(self.database_path) as connection:
            matches = find_provider_promotion_matches(connection, second)
            self.assertEqual([location_id], [item.record.id for item in matches])
            promote_provider_feature(
                connection,
                second,
                choice=str(location_id),
                display_name="Ignored",
            )
            context = location_place_context(connection, location_id)

        self.assertEqual(original.coordinates, context.representative_point.coordinates)
        self.assertEqual(original.id, context.representative_point.id)
        self.assertEqual(
            ["2026.08.01", "2026.08.02"],
            [item.feature_version for item in context.provider_references],
        )

    def test_portable_list_membership_survives_provider_version_disappearance(self) -> None:
        feature = provider_feature_from_form(provider_values(), self.pack_root)
        with connect(self.database_path) as connection:
            list_id = create_map_feature_list(connection, "Weekend places")
            _membership_id, created = add_map_feature_membership(
                connection, list_id, feature
            )
            feature_list = get_map_feature_list(connection, list_id)
            memberships = list_map_feature_memberships(connection, list_id)
            export = map_feature_membership_export(feature_list, memberships)

        self.assertTrue(created)
        self.assertNotIn("latitude", json.dumps(export))
        self.assertNotIn("feature_version", json.dumps(export))
        self.assertIsNotNone(
            read_active_search_feature(
                self.pack_root, feature.provider_key, feature.feature_id
            )
        )

        activate_pack(self.pack_root, "2026.08.02")

        with self.assertRaisesRegex(ValueError, "no longer active"):
            provider_feature_from_form(provider_values(), self.pack_root)
        self.assertIsNone(
            read_active_search_feature(
                self.pack_root, feature.provider_key, feature.feature_id
            )
        )
        with connect(self.database_path) as connection:
            retained = list_map_feature_memberships(connection, list_id)
            lists = list_map_feature_lists(connection)
        self.assertEqual("Surfers Paradise", retained[0].user_label)
        self.assertEqual(1, next(item for item in lists if item.id == list_id).member_count)

        bundle = create_bundle(self.database_path, self.root / "documents")
        target_database = self.root / "imported" / "database.sqlite3"
        target_documents = target_database.parent / "documents"
        target_documents.mkdir(parents=True)
        initialise_test_database(target_database)
        apply_import_bundle(
            bundle,
            target_database,
            target_documents,
            target_database.parent / "backups",
        )
        with connect(target_database) as connection:
            imported_list = next(
                item for item in list_map_feature_lists(connection) if item.name == "Weekend places"
            )
            imported_memberships = list_map_feature_memberships(
                connection, imported_list.id
            )
        self.assertEqual("Surfers Paradise", imported_memberships[0].user_label)
        with connect(target_database) as connection:
            self.assertTrue(
                remove_map_feature_membership(
                    connection, imported_list.id, imported_memberships[0].id
                )
            )
            self.assertEqual([], list_map_feature_memberships(connection, imported_list.id))
            add_map_feature_membership(connection, imported_list.id, feature)
            self.assertEqual(1, clear_map_feature_list(connection, imported_list.id))
            self.assertEqual([], list_map_feature_memberships(connection, imported_list.id))


class MapFeatureHttpTests(unittest.TestCase):
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
        self.port = self.server.server_port

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method: str, path: str, values: dict[str, str] | None = None):
        body = urlencode(values or {}).encode()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request(
            method,
            path,
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        content = response.read()
        result = response.status, dict(response.getheaders()), content
        connection.close()
        return result

    def test_review_promotion_and_external_favourite_routes_are_explicit(self) -> None:
        values = provider_values()
        values["return_to"] = "/map?q=Surfers"
        with connect(self.database_path) as connection:
            before = connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        status, _headers, review = self.request(
            "POST", "/map/provider-location/review", values
        )
        self.assertEqual(200, status)
        self.assertIn(b"Review Save as Location", review)
        self.assertIn(b"Browsing has not changed canonical data", review)
        with connect(self.database_path) as connection:
            self.assertEqual(
                before, connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            )

        values.update({"choice": "new", "display_name": "Reviewed Surfers"})
        status, headers, _body = self.request(
            "POST", "/map/provider-location/save", values
        )
        self.assertEqual(303, status)
        self.assertRegex(headers["Location"], r"/locations/\d+\?saved=1")

        with connect(self.database_path) as connection:
            favourite = list_map_feature_lists(connection)[0]
        values["list_id"] = str(favourite.id)
        status, headers, _body = self.request("POST", "/map/lists/add", values)
        self.assertEqual(303, status)
        self.assertEqual("/map?q=Surfers&saved=1", headers["Location"])

        status, _headers, page = self.request("GET", f"/map/lists/{favourite.id}")
        self.assertEqual(200, status)
        self.assertIn(b"Surfers Paradise", page)
        self.assertIn(b"Available now", page)
        status, headers, export = self.request(
            "GET", f"/map/lists/{favourite.id}/export.json"
        )
        self.assertEqual(200, status)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual("project-e-map-feature-list", json.loads(export)["format"])
        status, _headers, rejected = self.request(
            "POST", f"/map/lists/{favourite.id}/clear", {"confirm": "not-yet"}
        )
        self.assertEqual(400, status)
        self.assertIn(b"Type CLEAR", rejected)
        status, headers, _body = self.request(
            "POST", f"/map/lists/{favourite.id}/clear", {"confirm": "CLEAR"}
        )
        self.assertEqual(303, status)
        self.assertEqual(f"/map/lists/{favourite.id}?saved=1", headers["Location"])
        with connect(self.database_path) as connection:
            self.assertEqual([], list_map_feature_memberships(connection, favourite.id))


if __name__ == "__main__":
    unittest.main()
