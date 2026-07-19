import tempfile
import unittest
from pathlib import Path

from app.db import connect, initialise_database
from app.temporal import (
    TemporalValueError,
    local_datetime_to_utc,
    normalise_all_day_interval,
    normalise_timed_interval,
)


class TemporalTests(unittest.TestCase):
    def test_brisbane_local_interval_normalises_to_utc(self) -> None:
        interval = normalise_timed_interval(
            "2026-07-19T09:00", "2026-07-19T10:30", "Australia/Brisbane"
        )
        self.assertEqual("2026-07-18T23:00:00Z", interval.start_utc)
        self.assertEqual("2026-07-19T00:30:00Z", interval.end_utc)

    def test_all_day_user_range_becomes_end_exclusive(self) -> None:
        interval = normalise_all_day_interval("2026-07-19", "2026-07-21")
        self.assertEqual("2026-07-19", interval.start_date)
        self.assertEqual("2026-07-22", interval.end_date_exclusive)
        self.assertEqual("2026-07-21", interval.inclusive_end_date)

    def test_timed_interval_requires_a_bounded_positive_duration(self) -> None:
        with self.assertRaisesRegex(TemporalValueError, "after its start"):
            normalise_timed_interval(
                "2026-07-19T09:00", "2026-07-19T09:00", "Australia/Brisbane"
            )

    def test_nonexistent_daylight_saving_time_is_rejected(self) -> None:
        with self.assertRaisesRegex(TemporalValueError, "does not exist"):
            local_datetime_to_utc("2026-10-04T02:30", "Australia/Sydney")

    def test_ambiguous_daylight_saving_time_requires_choice(self) -> None:
        value = "2026-04-05T02:30"
        with self.assertRaisesRegex(TemporalValueError, "occurs twice"):
            local_datetime_to_utc(value, "Australia/Sydney")
        self.assertNotEqual(
            local_datetime_to_utc(value, "Australia/Sydney", fold=0),
            local_datetime_to_utc(value, "Australia/Sydney", fold=1),
        )

    def test_unknown_timezone_is_rejected(self) -> None:
        with self.assertRaisesRegex(TemporalValueError, "Unknown IANA timezone"):
            local_datetime_to_utc("2026-07-19T09:00", "Australia/Not_A_Place")

    def test_schema_migration_creates_default_calendar_and_category(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "temporal.sqlite3"
            initialise_database(database_path)
            with connect(database_path) as connection:
                calendar = connection.execute("SELECT * FROM calendars").fetchone()
                category = connection.execute(
                    "SELECT * FROM event_categories"
                ).fetchone()
                migration = connection.execute(
                    """
                    SELECT 1 FROM schema_migrations
                    WHERE migration_id = '20260719_16_temporal_foundation'
                    """
                ).fetchone()
        self.assertIsNotNone(migration)
        self.assertEqual("Australia/Brisbane", calendar["timezone"])
        self.assertEqual(60, calendar["default_event_duration_minutes"])
        self.assertEqual("General", category["name"])


if __name__ == "__main__":
    unittest.main()
