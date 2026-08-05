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
    create_mobility_profile,
    create_relationship,
    create_routing_policy,
    delete_relationship,
    get_entity_by_id,
    get_mobility_profile,
    get_routing_policy,
)
from app.entities import DEFINITIONS_BY_TYPE
from app.journey_contract import JourneyMode, PolicyKind
from app.portability import (
    apply_import_bundle,
    create_bundle,
    create_recovery_backup,
    inspect_bundle,
    restore_recovery_bundle,
)
from tests.database_test_support import initialise_test_database


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source_db = self.root / "source" / "project.sqlite3"
        self.source_documents = self.source_db.parent / "documents"
        self.source_documents.mkdir(parents=True)
        initialise_test_database(self.source_db)

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

        target_db = self.root / "target" / "project.sqlite3"
        target_documents = target_db.parent / "documents"
        backups = target_db.parent / "backups"
        target_documents.mkdir(parents=True)
        initialise_test_database(target_db)

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
        members["data/project-e.sqlite3"] += b"tampered"
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as target:
            for name, value in members.items():
                target.writestr(
                    name,
                    json.dumps(manifest) if name == "manifest.json" else value,
                )
        with self.assertRaisesRegex(ValueError, "checksum"):
            inspect_bundle(output.getvalue())

        target_db = self.root / "occupied" / "project.sqlite3"
        target_documents = target_db.parent / "documents"
        target_documents.mkdir(parents=True)
        initialise_test_database(target_db)
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
        target_db = self.root / "failure" / "project.sqlite3"
        target_documents = target_db.parent / "documents"
        target_documents.mkdir(parents=True)
        (target_documents / "keep.txt").write_text("keep")
        initialise_test_database(target_db)
        with connect(target_db) as connection:
            existing_id = create_entity(connection, DEFINITIONS_BY_TYPE["person"], {"display_name": "Existing", "given_name": "Existing"})
        backup_path = target_db.parent / "incoming.zip"
        backup_path.write_bytes(bundle)
        with patch("app.portability.shutil.copy2", side_effect=OSError("copy failed")):
            with self.assertRaisesRegex(OSError, "copy failed"):
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

    def test_user_owned_journey_configuration_round_trips_but_cache_is_excluded(self):
        with connect(self.source_db) as connection:
            create_mobility_profile(
                connection,
                "fictional-portable-walk",
                "Fictional portable walk",
                JourneyMode.WALK,
                {"speed_metres_per_second": 1.2},
            )
            create_routing_policy(
                connection,
                "fictional-portable-policy",
                "Fictional portable policy",
                PolicyKind.SOFT_AVOIDANCE,
                {"modes": ["walk"], "attribute": "stairs"},
            )
        cache_path = self.source_db.parent / "journey-cache.sqlite3"
        cache_path.write_bytes(b"disposable fictional cache")

        bundle = create_bundle(self.source_db, self.source_documents)
        with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
            self.assertNotIn("journey-cache.sqlite3", archive.namelist())
        target_db = self.root / "journey-target" / "project.sqlite3"
        target_documents = target_db.parent / "documents"
        target_documents.mkdir(parents=True)
        initialise_test_database(target_db)

        apply_import_bundle(
            bundle,
            target_db,
            target_documents,
            target_db.parent / "backups",
        )

        with connect(target_db) as connection:
            profile = get_mobility_profile(connection, "fictional-portable-walk")
            policy = get_routing_policy(connection, "fictional-portable-policy")
        self.assertEqual(JourneyMode.WALK, profile.primary_mode)
        self.assertEqual(PolicyKind.SOFT_AVOIDANCE, policy.kind)
        self.assertFalse((target_db.parent / "journey-cache.sqlite3").exists())

    def test_invalid_journey_configuration_is_rejected_before_import(self):
        with connect(self.source_db) as connection:
            profile = create_mobility_profile(
                connection,
                "fictional-invalid-walk",
                "Fictional invalid walk",
                JourneyMode.WALK,
                {},
            )
            connection.execute(
                "UPDATE mobility_profiles SET definition_json='[]' WHERE id=?",
                (profile.id,),
            )
            connection.commit()

        bundle = create_bundle(self.source_db, self.source_documents)

        with self.assertRaisesRegex(ValueError, "Journey configuration"):
            inspect_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
