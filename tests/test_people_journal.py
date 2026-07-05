import tempfile
import unittest
from pathlib import Path

from app import views
from app.db import (
    archive_journal_entry,
    connect,
    create_entity,
    create_journal_entry,
    delete_journal_entry,
    get_entity,
    get_journal_entry,
    initialise_database,
    list_journal_entries,
    update_journal_entry,
)
from app.entities import DEFINITIONS_BY_SLUG


class PeopleJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "journal.postgres"
        initialise_database(self.database_path)
        self.people = DEFINITIONS_BY_SLUG["people"]
        with connect(self.database_path) as connection:
            self.person_id = create_entity(
                connection,
                self.people,
                {
                    "given_name": "Ada",
                    "family_name": "Lovelace",
                    "birthday": "1815-12-10",
                    "notes": "Legacy notes",
                },
            )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_journal_crud_archive_and_chronological_listing(self) -> None:
        with connect(self.database_path) as connection:
            first_id = create_journal_entry(connection, "person", self.person_id, " First note ")
            second_id = create_journal_entry(connection, "person", self.person_id, "Second note")
            entries = list_journal_entries(connection, "person", self.person_id)
            self.assertEqual([first_id, second_id], [entry.id for entry in entries])
            self.assertEqual("First note", entries[0].body)

            update_journal_entry(connection, first_id, "Updated note")
            updated = get_journal_entry(connection, first_id)
            self.assertTrue(updated.is_edited)
            self.assertEqual("Updated note", updated.body)

            archive_journal_entry(connection, first_id)
            self.assertEqual([second_id], [entry.id for entry in list_journal_entries(connection, "person", self.person_id)])
            self.assertEqual(2, len(list_journal_entries(connection, "person", self.person_id, include_archived=True)))

            delete_journal_entry(connection, second_id)
            self.assertIsNone(get_journal_entry(connection, second_id))

    def test_blank_entries_are_rejected(self) -> None:
        with connect(self.database_path) as connection:
            with self.assertRaisesRegex(ValueError, "required"):
                create_journal_entry(connection, "person", self.person_id, "   ")

    def test_person_page_uses_journal_and_people_list_uses_dob(self) -> None:
        with connect(self.database_path) as connection:
            create_journal_entry(connection, "person", self.person_id, "Observed detail")
            person = get_entity(connection, self.people, self.person_id)
            entries = list_journal_entries(connection, "person", self.person_id)

        detail_html = views.entity_detail_page(person, [], journal_entries=entries)
        self.assertIn("<h2>Journal</h2>", detail_html)
        self.assertIn("Observed detail", detail_html)
        self.assertIn("Archive", detail_html)
        self.assertNotIn("<h2>Notes</h2>", detail_html)

        list_html = views.entity_list_page(self.people, [person])
        self.assertIn("<th>DOB</th>", list_html)
        self.assertIn("1815-12-10", list_html)
        self.assertNotIn("Legacy notes", list_html)

    def test_person_deletion_cascades_journal_entries(self) -> None:
        with connect(self.database_path) as connection:
            entry_id = create_journal_entry(connection, "person", self.person_id, "Temporary")
            connection.execute("DELETE FROM entities WHERE id = ?", (self.person_id,))
            connection.commit()
            self.assertIsNone(get_journal_entry(connection, entry_id))


if __name__ == "__main__":
    unittest.main()
