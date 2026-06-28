import tempfile
import unittest
from pathlib import Path

from app.document_storage import (
    UploadedFile,
    delete_stored_document,
    format_file_size,
    safe_file_name,
    store_document_upload,
    stored_document_path,
)


class DocumentStorageTests(unittest.TestCase):
    def test_upload_is_safely_named_stored_and_described(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir) / "documents"
            upload = UploadedFile("../Quarterly report?.txt", "text/plain", b"report")

            metadata = store_document_upload(upload, storage_dir)
            stored_path = stored_document_path(metadata["file_path"], storage_dir)

            self.assertEqual(metadata["file_name"], "../Quarterly report?.txt")
            self.assertEqual(metadata["mime_type"], "text/plain")
            self.assertEqual(metadata["file_size"], "6 B")
            self.assertTrue(metadata["file_path"].startswith("documents/"))
            self.assertIsNotNone(stored_path)
            self.assertEqual(stored_path.read_bytes(), b"report")
            self.assertEqual(stored_path.parent, storage_dir.resolve())
            self.assertTrue(stored_path.name.endswith("-Quarterly-report-.txt"))

    def test_stored_path_rejects_escape_and_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir) / "documents"
            self.assertIsNone(stored_document_path("../secret.txt", storage_dir))
            self.assertIsNone(stored_document_path("/tmp/secret.txt", storage_dir))
            self.assertIsNone(stored_document_path("other/file.txt", storage_dir))

    def test_delete_removes_only_confined_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_dir = Path(temp_dir) / "documents"
            metadata = store_document_upload(
                UploadedFile("owned.txt", "text/plain", b"owned"), storage_dir
            )
            stored_path = stored_document_path(metadata["file_path"], storage_dir)

            self.assertTrue(delete_stored_document(metadata["file_path"], storage_dir))
            self.assertFalse(stored_path.exists())
            self.assertFalse(delete_stored_document(metadata["file_path"], storage_dir))
            self.assertFalse(delete_stored_document("../outside.txt", storage_dir))

    def test_filename_and_size_helpers_preserve_existing_rules(self) -> None:
        self.assertEqual(safe_file_name("../a strange?.pdf"), "a-strange-.pdf")
        self.assertEqual(safe_file_name("..."), "document")
        self.assertEqual(format_file_size(1023), "1023 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1024 * 1024), "1.0 MB")


if __name__ == "__main__":
    unittest.main()
