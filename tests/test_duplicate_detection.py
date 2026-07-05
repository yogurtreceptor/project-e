import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.db import connect, create_entity, get_entity, initialise_database, list_entities
from app.duplicate_detection import find_duplicate_entities
from app.entities import DEFINITIONS_BY_SLUG
from app.web import EddyRequestHandler, ThreadingHTTPServer


class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "duplicates.postgres"
        initialise_database(self.database_path)
        self.people = DEFINITIONS_BY_SLUG["people"]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def create_person(self, name: str, email: str = "", phone: str = "") -> int:
        with connect(self.database_path) as connection:
            return create_entity(
                connection,
                self.people,
                {
                    "display_name": name,
                    "given_name": name.split(maxsplit=1)[0],
                    "family_name": name.split(maxsplit=1)[1] if len(name.split(maxsplit=1)) > 1 else "",
                    "email": email,
                    "phone": phone,
                    "sex": "Unknown",
                },
            )

    def test_matches_normalised_name_and_strong_identity_fields(self) -> None:
        entity_id = self.create_person("Ada  Lovelace", "ADA@example.test")
        with connect(self.database_path) as connection:
            name_matches = find_duplicate_entities(
                connection, self.people, {"display_name": " ada lovelace "}
            )
            email_matches = find_duplicate_entities(
                connection,
                self.people,
                {"display_name": "Augusta King", "email": "ada@EXAMPLE.test"},
            )
            excluded = find_duplicate_entities(
                connection,
                self.people,
                {"display_name": "Ada Lovelace"},
                exclude_entity_id=entity_id,
            )

        self.assertEqual(name_matches[0].matched_fields, ("Name",))
        self.assertEqual(email_matches[0].matched_fields, ("Email",))
        self.assertEqual(excluded, [])

    def test_blank_identity_fields_do_not_match(self) -> None:
        self.create_person("First Person")
        with connect(self.database_path) as connection:
            matches = find_duplicate_entities(
                connection, self.people, {"display_name": "Different Person"}
            )
        self.assertEqual(matches, [])

    def test_http_create_warns_then_allows_explicit_confirmation(self) -> None:
        existing_id = self.create_person("Ada Lovelace", "ada@example.test")
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            first_status, first_headers, first_body = self.post_person(
                server.server_port,
                {"given_name": "Ada", "family_name": "Lovelace", "email": "new@example.test"},
            )
            with connect(self.database_path) as connection:
                count_after_warning = len(list_entities(connection, self.people))

            second_status, second_headers, _second_body = self.post_person(
                server.server_port,
                {
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "email": "new@example.test",
                    "confirm_duplicate": "1",
                },
            )
            with connect(self.database_path) as connection:
                count_after_confirmation = len(list_entities(connection, self.people))
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

        self.assertEqual(first_status, 200)
        self.assertIn("Possible duplicate records found", first_body)
        self.assertIn("Save anyway", first_body)
        self.assertIn(f'/people/{existing_id}', first_body)
        self.assertEqual(count_after_warning, 1)
        self.assertEqual(second_status, 303)
        self.assertEqual(second_headers["Location"], "/people/2")
        self.assertEqual(count_after_confirmation, 2)

    def test_http_edit_excludes_self_and_warns_before_matching_another_record(self) -> None:
        self.create_person("Ada Lovelace")
        edited_id = self.create_person("Grace Hopper")
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            warning_status, _warning_headers, warning_body = self.post_person(
                server.server_port,
                {"given_name": "Ada", "family_name": "Lovelace"},
                path=f"/people/{edited_id}/edit",
            )
            with connect(self.database_path) as connection:
                after_warning = get_entity(connection, self.people, edited_id)

            confirmed_status, confirmed_headers, _confirmed_body = self.post_person(
                server.server_port,
                {"given_name": "Ada", "family_name": "Lovelace", "confirm_duplicate": "1"},
                path=f"/people/{edited_id}/edit",
            )
            with connect(self.database_path) as connection:
                after_confirmation = get_entity(connection, self.people, edited_id)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

        self.assertEqual(warning_status, 200)
        self.assertIn("Possible duplicate records found", warning_body)
        self.assertEqual(after_warning.display_name, "Grace Hopper")
        self.assertEqual(confirmed_status, 303)
        self.assertEqual(confirmed_headers["Location"], f"/people/{edited_id}")
        self.assertEqual(after_confirmation.display_name, "Ada Lovelace")

    @staticmethod
    def post_person(
        port: int, values: dict[str, str], path: str = "/people/new"
    ) -> tuple[int, dict[str, str], str]:
        body = urlencode(values)
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body.encode("utf-8"))),
            },
        )
        response = connection.getresponse()
        response_body = response.read().decode("utf-8")
        headers = dict(response.getheaders())
        status = response.status
        connection.close()
        return status, headers, response_body


if __name__ == "__main__":
    unittest.main()
