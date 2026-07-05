import io
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

from app.audit import get_provenance, list_audit_events
from app.db import (
    connect,
    create_entity,
    create_relationship,
    delete_relationship,
    get_entity_by_id,
    initialise_database,
)
from app.entities import DEFINITIONS_BY_TYPE
from app.portability import (
    apply_import_bundle,
    create_bundle,
    create_recovery_backup,
    inspect_bundle,
    restore_recovery_bundle,
)


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_db = self.root / "source" / "project.postgres"
        self.source_documents = self.source_db.parent / "documents"
        self.source_documents.mkdir(parents=True)
        initialise_database(self.source_db)

    def tearDown(self):
        self.temporary.cleanup()

    def make_source_data(self):
        stored_name = "fixture-evidence.txt"
        stored_path = self.source_documents / stored_name
        stored_path.write_bytes(b"fictional evidence")
        with connect(self.source_db) as connection:
            first = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["person"],
                {
                    "display_name": "Ada Example",
                    "given_name": "Ada",
                    "family_name": "Example",
                    "languages": "",
                },
            )
            document = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["document"],
                {
                    "display_name": "Evidence",
                    "document_type": "Letter",
                    "file_name": "evidence.txt",
                    "file_path": f"documents/{stored_name}",
                    "mime_type": "text/plain",
                    "file_size": "18 B",
                },
            )
            relationship = create_relationship(
                connection,
                {
                    "source_entity_id": str(document),
                    "target_entity_id": str(first),
                    "type": "document_references_person",
                },
            )
            delete_relationship(connection, relationship)
            connection.commit()
        return first, document, relationship

    def test_export_clean_import_round_trip_preserves_records_files_and_provenance(self):
        first, document, relationship = self.make_source_data()
        bundle = create_bundle(self.source_db, self.source_documents)
        preview = inspect_bundle(bundle)
        self.assertEqual((2, 1, 1, 1), (
            preview.entities,
            preview.relationships,
            preview.documents,
            preview.deleted_relationships,
        ))

        target_db = self.root / "target" / "project.postgres"
        target_documents = target_db.parent / "documents"
        backups = target_db.parent / "backups"
        target_documents.mkdir(parents=True)
        initialise_database(target_db)

        imported = apply_import_bundle(
            bundle, target_db, target_documents, backups
        )

        self.assertEqual(preview, imported)
        self.assertEqual(
            b"fictional evidence",
            (target_documents / "fixture-evidence.txt").read_bytes(),
        )
        with connect(target_db) as connection:
            self.assertEqual("Ada Example", get_entity_by_id(connection, first).title)
            self.assertEqual("Evidence", get_entity_by_id(connection, document).title)
            row = connection.execute(
                "SELECT deleted_at FROM relationships WHERE id=?", (relationship,)
            ).fetchone()
            self.assertTrue(row["deleted_at"])
            self.assertEqual(
                "manual", get_provenance(connection, "entity", first)["display_name"]
            )
            self.assertEqual(
                "import",
                list_audit_events(connection, "system", 0)[0].event_type,
            )
        self.assertEqual(1, len(list(backups.glob("*-before-import-*.zip"))))

    def test_checksum_failure_and_nonempty_target_do_not_mutate_target(self):
        self.make_source_data()
        bundle = create_bundle(self.source_db, self.source_documents)
        with zipfile.ZipFile(io.BytesIO(bundle)) as source:
            manifest = json.loads(source.read("manifest.json"))
            members = {name: source.read(name) for name in source.namelist()}
        members["data/project-e.dump"] += b"tampered"
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as target:
            for name, value in members.items():
                target.writestr(
                    name,
                    json.dumps(manifest) if name == "manifest.json" else value,
                )
        with self.assertRaisesRegex(ValueError, "checksum"):
            inspect_bundle(output.getvalue())

        target_db = self.root / "occupied" / "project.postgres"
        target_documents = target_db.parent / "documents"
        target_documents.mkdir(parents=True)
        initialise_database(target_db)
        with connect(target_db) as connection:
            occupied_id = create_entity(
                connection,
                DEFINITIONS_BY_TYPE["person"],
                {"display_name": "Existing", "given_name": "Existing"},
            )
        with self.assertRaisesRegex(ValueError, "empty"):
            apply_import_bundle(
                bundle, target_db, target_documents, target_db.parent / "backups"
            )
        with connect(target_db) as connection:
            self.assertEqual("Existing", get_entity_by_id(connection, occupied_id).title)

    def test_recovery_copy_failure_restores_previous_database_and_documents(self):
        self.make_source_data()
        bundle = create_bundle(self.source_db, self.source_documents)
        target_db = self.root / "failure" / "project.postgres"
        target_documents = target_db.parent / "documents"
        target_documents.mkdir(parents=True)
        (target_documents / "keep.txt").write_text("keep")
        initialise_database(target_db)
        with connect(target_db) as connection:
            existing_id = create_entity(connection, DEFINITIONS_BY_TYPE["person"], {"display_name": "Existing", "given_name": "Existing"})
        backup_path = target_db.parent / "incoming.zip"
        backup_path.write_bytes(bundle)
        with patch("app.portability._run_pg", side_effect=ValueError("restore failed")):
            with self.assertRaisesRegex(ValueError, "restore failed"):
                restore_recovery_bundle(backup_path, target_db, target_documents, target_db.parent / "backups")
        with connect(target_db) as connection:
            self.assertEqual("Existing", get_entity_by_id(connection, existing_id).title)
        self.assertEqual("keep", (target_documents / "keep.txt").read_text())

    def test_recovery_bundle_replaces_nonempty_state(self):
        original_id, _document, _relationship = self.make_source_data()
        backup_dir = self.root / "recovery"
        backup = create_recovery_backup(
            self.source_db, self.source_documents, backup_dir, "manual"
        )
        with connect(self.source_db) as connection:
            connection.execute("UPDATE entities SET display_name='Changed' WHERE id=?", (original_id,))
            connection.commit()

        restore_recovery_bundle(
            backup, self.source_db, self.source_documents, backup_dir
        )

        with connect(self.source_db) as connection:
            self.assertEqual("Ada Example", get_entity_by_id(connection, original_id).title)
        self.assertGreaterEqual(len(list(backup_dir.glob("*-before-import-*.zip"))), 1)


if __name__ == "__main__":
    unittest.main()
