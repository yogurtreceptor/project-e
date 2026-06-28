import unittest
from types import SimpleNamespace

from app.view_pages.common import format_relationship_dates
from app.view_pages.relationships import relationship_detail_page


def relationship(**overrides):
    values = {
        "id": 1,
        "status": "active",
        "started_at": "2020-01-02",
        "started_at_precision": "exact",
        "ended_at": "",
        "ended_at_precision": "exact",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class RelationshipDateDisplayTests(unittest.TestCase):
    def test_relationship_without_end_date_displays_only_start(self) -> None:
        for status in ("active", "unknown", "former"):
            with self.subTest(status=status):
                self.assertEqual(
                    format_relationship_dates(relationship(status=status)),
                    "Since 2020-01-02",
                )

    def test_relationship_displays_end_date_only_when_recorded(self) -> None:
        self.assertEqual(
            format_relationship_dates(relationship(ended_at="2024-05-06")),
            "2020-01-02 to 2024-05-06",
        )
        self.assertEqual(
            format_relationship_dates(relationship(started_at="", ended_at="2024-05-06")),
            "2024-05-06",
        )

    def test_relationship_with_no_dates_is_not_recorded(self) -> None:
        self.assertEqual(
            format_relationship_dates(relationship(started_at="")),
            "Not recorded",
        )

    def test_detail_omits_unrecorded_end_date(self) -> None:
        record = relationship(
            type=SimpleNamespace(inverse_label="known by"),
            source=SimpleNamespace(id=1, slug="people", title="Ada"),
            target=SimpleNamespace(id=2, slug="people", title="Charles"),
            label="knows",
            notes="",
            created_at="2020-01-02",
            updated_at="2020-01-02",
        )

        html = relationship_detail_page(record)

        self.assertNotIn("<dt>Ended</dt>", html)
        self.assertNotIn("Not recorded", html)


if __name__ == "__main__":
    unittest.main()
