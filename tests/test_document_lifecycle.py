import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.db import connect, create_entity, delete_entity, get_entity, initialise_database
from app.document_lifecycle import delete_unreferenced_document_file
from app.document_storage import UploadedFile, store_document_upload, stored_document_path
from app.entities import DEFINITIONS_BY_SLUG
from app.web import EddyRequestHandler, ThreadingHTTPServer


class DocumentLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database_path = self.root / "documents.sqlite3"
        self.storage_dir = self.root / "documents"
        self.definition = DEFINITIONS_BY_SLUG["documents"]
        initialise_database(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_shared_legacy_reference_is_deleted_only_after_last_document(self) -> None:
        metadata = store_document_upload(
            UploadedFile("shared.txt", "text/plain", b"shared"), self.storage_dir
        )
        stored_path = stored_document_path(metadata["file_path"], self.storage_dir)
        with connect(self.database_path) as connection:
            first_id = create_entity(
                connection, self.definition, {"display_name": "First", **metadata}
            )
            second_id = create_entity(
                connection, self.definition, {"display_name": "Second", **metadata}
            )
            delete_entity(connection, self.definition, first_id)
            first_cleanup = delete_unreferenced_document_file(
                connection, metadata["file_path"], self.storage_dir
            )
            delete_entity(connection, self.definition, second_id)
            final_cleanup = delete_unreferenced_document_file(
                connection, metadata["file_path"], self.storage_dir
            )

        self.assertFalse(first_cleanup)
        self.assertTrue(final_cleanup)
        self.assertFalse(stored_path.exists())

    def test_http_replacement_and_deletion_clean_up_owned_files(self) -> None:
        EddyRequestHandler.database_path = self.database_path
        EddyRequestHandler.document_storage_dir = self.storage_dir
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            create_status, create_headers = self.post_multipart(
                server.server_port,
                "/documents/new",
                {"display_name": "Lifecycle document"},
                "original.txt",
                b"original",
            )
            document_id = int(create_headers["Location"].rsplit("/", 1)[1])
            with connect(self.database_path) as connection:
                original_record = get_entity(connection, self.definition, document_id)
            original_path = stored_document_path(
                original_record.metadata["file_path"], self.storage_dir
            )
            original_exists_after_create = original_path.exists()

            edit_status, _edit_headers = self.post_multipart(
                server.server_port,
                f"/documents/{document_id}/edit",
                {"display_name": "Lifecycle document"},
                "replacement.txt",
                b"replacement",
            )
            with connect(self.database_path) as connection:
                replaced_record = get_entity(connection, self.definition, document_id)
            replacement_path = stored_document_path(
                replaced_record.metadata["file_path"], self.storage_dir
            )
            original_exists_after_edit = original_path.exists()
            replacement_exists_after_edit = replacement_path.exists()

            delete_status, _delete_headers = self.post_empty(
                server.server_port, f"/documents/{document_id}/delete"
            )
            with connect(self.database_path) as connection:
                deleted_record = get_entity(connection, self.definition, document_id)
            replacement_exists_after_delete = replacement_path.exists()
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

        self.assertEqual(create_status, 303)
        self.assertTrue(original_exists_after_create)
        self.assertEqual(edit_status, 303)
        self.assertFalse(original_exists_after_edit)
        self.assertTrue(replacement_exists_after_edit)
        self.assertEqual(delete_status, 303)
        self.assertFalse(replacement_exists_after_delete)
        self.assertIsNone(deleted_record)

    def test_client_supplied_file_metadata_is_not_trusted(self) -> None:
        metadata = store_document_upload(
            UploadedFile("owned.txt", "text/plain", b"owned"), self.storage_dir
        )
        with connect(self.database_path) as connection:
            existing_id = create_entity(
                connection, self.definition, {"display_name": "Existing", **metadata}
            )

        EddyRequestHandler.database_path = self.database_path
        EddyRequestHandler.document_storage_dir = self.storage_dir
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            create_status, create_headers = self.post_urlencoded(
                server.server_port,
                "/documents/new",
                {
                    "display_name": "Forged metadata",
                    "file_name": "forged.txt",
                    "file_path": metadata["file_path"],
                    "mime_type": "text/plain",
                    "file_size": "5 B",
                },
            )
            created_id = int(create_headers["Location"].rsplit("/", 1)[1])
            edit_status, _edit_headers = self.post_urlencoded(
                server.server_port,
                f"/documents/{existing_id}/edit",
                {
                    "display_name": "Existing",
                    "file_name": "forged.txt",
                    "file_path": "documents/forged.txt",
                    "mime_type": "application/forged",
                    "file_size": "999 B",
                },
            )
            with connect(self.database_path) as connection:
                created = get_entity(connection, self.definition, created_id)
                edited = get_entity(connection, self.definition, existing_id)
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

        self.assertEqual(create_status, 303)
        self.assertEqual(created.metadata["file_path"], "")
        self.assertEqual(created.metadata["file_name"], "")
        self.assertEqual(edit_status, 303)
        self.assertEqual(edited.metadata["file_path"], metadata["file_path"])
        self.assertEqual(edited.metadata["file_name"], metadata["file_name"])

    @staticmethod
    def post_urlencoded(
        port: int, path: str, values: dict[str, str]
    ) -> tuple[int, dict[str, str]]:
        body = urlencode(values).encode("utf-8")
        return DocumentLifecycleTests.request(
            port, path, body, "application/x-www-form-urlencoded"
        )

    @staticmethod
    def post_multipart(
        port: int,
        path: str,
        fields: dict[str, str],
        file_name: str,
        data: bytes,
    ) -> tuple[int, dict[str, str]]:
        boundary = "----OperationEddyBoundary"
        parts = []
        for name, value in fields.items():
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n".encode("utf-8")
            )
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="upload"; filename="{file_name}"\r\n'
            "Content-Type: text/plain\r\n\r\n".encode("utf-8")
            + data
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        return DocumentLifecycleTests.request(
            port, path, body, f"multipart/form-data; boundary={boundary}"
        )

    @staticmethod
    def post_empty(port: int, path: str) -> tuple[int, dict[str, str]]:
        return DocumentLifecycleTests.request(
            port, path, b"", "application/x-www-form-urlencoded"
        )

    @staticmethod
    def request(
        port: int, path: str, body: bytes, content_type: str
    ) -> tuple[int, dict[str, str]]:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.request(
            "POST",
            path,
            body=body,
            headers={"Content-Type": content_type, "Content-Length": str(len(body))},
        )
        response = connection.getresponse()
        response.read()
        result = response.status, dict(response.getheaders())
        connection.close()
        return result


if __name__ == "__main__":
    unittest.main()
