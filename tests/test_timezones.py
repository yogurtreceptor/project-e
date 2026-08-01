import unittest

from app.timezones import timezone_catalogue
from app.view_pages.timezones import timezone_picker


class TimezonePickerTests(unittest.TestCase):
    def test_local_catalogue_exposes_country_and_current_offset(self) -> None:
        catalogue = {name: (country, offset) for name, country, offset in timezone_catalogue()}

        self.assertEqual(("Australia", "UTC+10:00"), catalogue["Australia/Brisbane"])
        self.assertEqual("United States", catalogue["America/New_York"][0])
        self.assertRegex(catalogue["America/New_York"][1], r"^UTC[+-]\d{2}:\d{2}$")

    def test_picker_defaults_to_brisbane_and_reveals_search_only_on_demand(self) -> None:
        page = timezone_picker("deadline_timezone", "America/New_York", name="deadline_timezone")

        self.assertIn('name="deadline_timezone"', page)
        self.assertIn('value="America/New_York"', page)
        self.assertIn("United States", page)
        self.assertIn("UTC", page)
        self.assertIn("data-timezone-options", page)
        self.assertIn('role="listbox" hidden', page)
        self.assertNotIn('type="search"', page)

        default_page = timezone_picker("timezone", "")
        self.assertIn('value="Australia/Brisbane"', default_page)


if __name__ == "__main__":
    unittest.main()
