import json
import http.client
import sqlite3
import tempfile
import threading
from datetime import date
import unittest
from pathlib import Path
from urllib.parse import urlencode

from app.audit import list_audit_events
from app.db import (
    connect,
    create_entity,
    create_relationship,
    delete_entity,
    get_entity,
    initialise_database,
    list_relationships_for_entity,
    restore_entity,
    search_entities,
)
from app.db_schema import (
    create_entity_table,
    create_initial_event_table,
    create_initial_temporal_foundation_tables,
    create_schema,
    create_schema_migration_table,
)
from app.entity_merge import list_entity_history
from app.event_service import (
    EventInput,
    EventSchedule,
    EventUpdate,
    archive_event,
    cancel_event,
    create_event,
    get_event,
    list_events,
    reinstate_event,
    reschedule_event,
    unarchive_event,
    update_event,
)
from app.event_recurrence import RecurrenceRule, cancel_occurrence, exception_dates, get_recurrence, occurrence_exceptions, occurrences_between, set_recurrence, split_series
from app.entities import DEFINITIONS_BY_SLUG, DEFINITIONS_BY_TYPE, EVENT_DEFINITION
from app.temporal import TemporalValueError
from app import views
from app.calendar_service import CalendarInput, create_calendar, get_calendar, list_calendars
from app.reminder_service import get_override, get_policy
from app.web import EddyRequestHandler, ThreadingHTTPServer


class EventServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "events.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_create_timed_event_uses_defaults_and_normalises_to_utc(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="  Dentist  ",
                notes="  Annual check-up  ",
                all_day=False,
                start_local="2026-08-01T09:00",
                end_local="2026-08-01T10:00",
            ),
        )

        event = get_event(self.connection, event_id)

        self.assertEqual("Dentist", event.title)
        self.assertEqual("Annual check-up", event.notes)
        self.assertEqual("2026-07-31T23:00:00Z", event.start_utc)
        self.assertEqual("2026-08-01T00:00:00Z", event.end_utc)
        self.assertEqual("Australia/Brisbane", event.timezone)
        self.assertFalse(event.is_all_day)
        self.assertEqual("", event.start_date)
        self.assertNotIn("events", DEFINITIONS_BY_SLUG)

    def test_create_all_day_event_persists_date_boundaries_only(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Regional holiday",
                all_day=True,
                start_date="2026-08-10",
                end_date="2026-08-12",
                date_precision="approximate",
            ),
        )

        event = get_event(self.connection, event_id)

        self.assertTrue(event.is_all_day)
        self.assertEqual("2026-08-10", event.start_date)
        self.assertEqual("2026-08-13", event.end_date_exclusive)
        self.assertEqual("", event.start_utc)
        self.assertEqual("", event.timezone)
        self.assertEqual("approximate", event.date_precision)

    def test_event_uses_standard_relationships_with_multiple_peer_entities(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Project kickoff", all_day=False, start_local="2026-08-10T09:00", end_local="2026-08-10T10:00"))
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {"given_name": "Ada", "middle_name": "", "family_name": "", "sex": "Unknown", "birthday": "", "email": "", "phone": "", "display_name": "", "summary": "", "notes": ""})
        location_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["location"], {"display_name": "Meeting room", "summary": "", "notes": ""})
        project_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["project"], {"display_name": "Launch", "summary": "", "notes": "", "project_type": "", "status": "Active", "started_at": "", "target_date": "", "ended_at": ""})

        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(person_id), "type": "event_involves_person"})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(location_id), "type": "event_at_location"})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(project_id), "type": "event_related_to_project"})
        self.connection.commit()

        event_relationships = list_relationships_for_entity(self.connection, event_id)
        self.assertEqual({"event_involves_person", "event_at_location", "event_related_to_project"}, {relationship.type_key for relationship in event_relationships})
        self.assertEqual({person_id, location_id, project_id}, {relationship.other_entity(event_id).id for relationship in event_relationships})
        self.assertEqual("involved in", list_relationships_for_entity(self.connection, person_id)[0].label_from(person_id))

    def test_event_search_and_related_record_projection_use_shared_conventions(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Project kickoff", notes="Discuss launch plan", all_day=False, start_local="2026-08-10T09:00", end_local="2026-08-10T10:00"))
        person_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["person"], {"given_name": "Ada", "middle_name": "", "family_name": "", "sex": "Unknown", "birthday": "", "email": "", "phone": "", "display_name": "", "summary": "", "notes": ""})
        create_relationship(self.connection, {"source_entity_id": str(event_id), "target_entity_id": str(person_id), "type": "event_involves_person"})

        event_results = search_entities(self.connection, "kickoff", entity_type="event")
        relationship_results = search_entities(self.connection, "Ada")
        person_record = get_entity(
            self.connection, DEFINITIONS_BY_TYPE["person"], person_id
        )
        relationships = list_relationships_for_entity(self.connection, person_id)
        event = get_event(self.connection, event_id)
        calendar = get_calendar(self.connection, event.calendar_id)

        self.assertEqual([event_id], [result["entity"].id for result in event_results])
        self.assertIn(event_id, {result["entity"].id for result in relationship_results})
        self.assertIn(f'href="/events/{event_id}"', views.entity_detail_page(person_record, relationships))
        projection = views.event_projection_page(event, calendar, list_relationships_for_entity(self.connection, event_id), [], [])
        self.assertIn("Project kickoff", projection)
        self.assertIn("Australia/Brisbane", projection)
        self.assertIn("Ada", projection)
        self.assertNotIn("/events/new", projection)

    def test_event_projection_route_is_read_only(self) -> None:
        event_id = create_event(self.connection, EventInput(title="Read-only event", all_day=True, start_date="2026-08-10", end_date="2026-08-10"))
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", f"/events/{event_id}")
            response = client.getresponse()
            page = response.read().decode()
            self.assertEqual(200, response.status)
            self.assertIn("Read-only event", page)
            self.assertNotIn("/events/new", page)
            client.request("GET", "/events")
            self.assertEqual(404, client.getresponse().status)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_calendar_originates_event_creation_and_editing(self) -> None:
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", "/calendar")
            page = client.getresponse().read().decode()
            self.assertIn('data-quick-create="event"', page)
            self.assertIn('data-quick-create-dialog="event"', page)
            self.assertNotIn('data-quick-create-dialog="task"', page)
            self.assertIn('data-quick-create-more data-quick-create-url="/calendar/events/new"', page)
            self.assertIn('data-quick-create-dock', page)
            self.assertIn('data-quick-create-drag', page)
            self.assertIn('data-description-field', page)
            self.assertIn('<aside class="sidebar calendar-sidebar" aria-label="Calendar sidebar">', page)
            self.assertNotIn('aria-label="Browse"', page)
            self.assertIn('data-mini-month-picker', page)
            self.assertEqual(42, page.count('data-mini-picker-day'))
            self.assertEqual(6, page.count('mini-month-week-number'))
            self.assertLess(page.index('>Create event</a>'), page.index('data-mini-month-picker'))
            self.assertIn('href="/calendar/events/new?return_to=', page)
            self.assertNotIn('/calendar/tasks/new', page)
            self.assertIn('<h2 id="my-calendars-title">My calendars</h2>', page)
            self.assertIn('aria-label="Collapse My calendars" data-calendar-group-label="My calendars"', page)
            self.assertIn('<h2 id="other-calendars-title">Other calendars</h2>', page)
            self.assertIn('aria-label="Collapse Other calendars" data-calendar-group-label="Other calendars"', page)
            self.assertEqual(2, page.count("data-calendar-group-toggle"))
            self.assertIn('href="/calendar/settings/add?return_to=%2Fcalendar" aria-label="Create calendar"', page)
            self.assertEqual(1, page.count('aria-label="Create calendar"'))
            other_heading = page[page.index('<h2 id="other-calendars-title">'):page.index('id="other-calendars-list"')]
            self.assertLess(other_heading.index('aria-label="Create calendar"'), other_heading.index('aria-label="Collapse Other calendars"'))
            self.assertIn('No subscribed calendars yet.', page)
            self.assertIn('data-calendar-visibility-controls', page)
            self.assertIn('aria-label="Edit General calendar"', page)
            self.assertIn('<span>General</span></label><a class="calendar-edit-control" href="/calendar/settings/calendars/1?return_to=%2Fcalendar"', page)
            self.assertNotIn('Apply calendars', page)
            self.assertNotIn('Visible Calendars', page)
            self.assertNotIn('Derived and related dates', page)
            self.assertIn('<div class="calendar-header-controls" role="navigation" aria-label="Calendar navigation">', page)
            self.assertIn('<h1 class="calendar-header-date">', page)
            self.assertIn('<summary class="calendar-header-view">Month<span class="menu-chevron" aria-hidden="true">▾</span></summary>', page)
            self.assertIn('<div class="calendar-header-tools">', page)
            self.assertIn('class="calendar-settings-control"', page)
            self.assertIn('href="/calendar/settings?return_to=%2Fcalendar" aria-label="Calendar settings" title="Calendar settings"', page)
            self.assertLess(page.index('calendar-view-menu'), page.index('class="calendar-settings-control"'))
            self.assertLess(page.index('class="calendar-settings-control"'), page.index('class="global-search-link"'))
            self.assertNotIn('>Manage calendars</a>', page)
            self.assertNotIn('class="calendar-toolbar"', page)
            self.assertIn('href="/calendar?view=month&date=', page)
            self.assertIn('href="/calendar?view=week&date=', page)
            self.assertIn('href="/calendar?view=day&date=', page)
            self.assertIn('aria-current="page">Month</a>', page)
            self.assertIn('class="calendar-day-events"', page)
            self.assertIn('class="calendar-month-view"', page)
            self.assertIn('style="--calendar-week-count:', page)
            self.assertNotIn("Current Events", page)
            self.assertIn('class="calendar-page"', page)
            self.assertNotIn("Operational time", page)
            client.request("GET", "/")
            home_page = client.getresponse().read().decode()
            self.assertNotIn('class="calendar-header-controls"', home_page)
            client.request("GET", "/calendar?view=month&date=2026-07-15&mini_date=2026-08-01")
            independently_browsed_picker = client.getresponse().read().decode()
            self.assertIn('<h2>August 2026</h2>', independently_browsed_picker)
            self.assertIn('<h1 class="calendar-header-date">July 2026</h1>', independently_browsed_picker)
            self.assertIn('href="/calendar?view=month&date=2026-07-15&calendars=1&calendars=2&mini_date=2026-07-01" data-mini-month-previous', independently_browsed_picker)
            self.assertIn('href="/calendar?view=month&date=2026-08-01&calendars=1&calendars=2" data-mini-picker-day', independently_browsed_picker)
            client.request("GET", "/calendar/events/new")
            form_page = client.getresponse().read().decode()
            self.assertIn('action="/calendar/events/new"', form_page)
            self.assertIn("data-event-all-day", form_page)
            self.assertIn("Description", form_page)
            self.assertNotIn("Notes <em>", form_page)
            client.request("GET", "/calendar/events/new?title=Quick+Event&start_local=2026-09-10T08%3A00&end_local=2026-09-10T09%3A00")
            handoff_page = client.getresponse().read().decode()
            self.assertIn('value="Quick Event"', handoff_page)
            self.assertIn('value="2026-09-10T08:00"', handoff_page)

            create_body = urlencode({
                "title": "Calendar-created Event", "calendar_id": "1",
                "start_date": "2026-09-10", "end_date": "2026-09-10",
                "start_local": "2026-09-10T09:00", "end_local": "2026-09-10T10:00",
                "timezone": "Australia/Brisbane", "notes": "Created in Calendar", "recurrence_preset": "custom",
                "recurrence_custom_interval": "1", "recurrence_custom_frequency": "week",
                "recurrence_custom_weekdays": "0,2", "recurrence_custom_ends": "after", "recurrence_custom_count": "3",
            })
            client.request("POST", "/calendar/events/new", create_body, {
                "Content-Type": "application/x-www-form-urlencoded",
            })
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar?created=1", response.getheader("Location"))
            created_rule = get_recurrence(self.connection, 1).rule
            self.assertEqual(("weekly", (0, 2), "2026-09-21"), (created_rule.frequency, created_rule.weekdays, created_rule.until_date))

            context_body = urlencode({
                "title": "Week-context Event", "calendar_id": "1",
                "start_local": "2026-09-10T09:00", "end_local": "2026-09-10T10:00",
                "timezone": "Australia/Brisbane", "return_to": "/calendar?view=week&date=2026-09-10",
            })
            client.request("POST", "/calendar/events/new", context_body, {
                "Content-Type": "application/x-www-form-urlencoded",
            })
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar?view=week&date=2026-09-10&created=2", response.getheader("Location"))

            client.request("GET", "/calendar/events/1/edit")
            edit_page = client.getresponse().read().decode()
            self.assertIn('value="2026-09-10T09:00"', edit_page)
            self.assertIn("add a relationship", edit_page)

            edit_body = urlencode({
                "title": "Calendar-edited Event", "calendar_id": "1",
                "start_date": "2026-09-11", "end_date": "2026-09-11",
                "start_local": "2026-09-11T11:00", "end_local": "2026-09-11T12:00",
                "timezone": "Australia/Brisbane", "notes": "Rescheduled in Calendar",
                "return_to": "/calendar?view=week&date=2026-09-11",
            })
            client.request("POST", "/calendar/events/1/edit", edit_body, {
                "Content-Type": "application/x-www-form-urlencoded",
            })
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar?view=week&date=2026-09-11&saved=1", response.getheader("Location"))
            event = get_event(self.connection, 1)
            self.assertEqual("Calendar-edited Event", event.title)
            self.assertEqual("2026-09-11T01:00:00Z", event.start_utc)
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_calendar_visual_refinement_assets_preserve_view_state_and_scroll_boundaries(self) -> None:
        static_dir = Path(__file__).resolve().parents[1] / "app" / "static"
        styles = (static_dir / "styles.css").read_text()
        groups = (static_dir / "calendar-groups.js").read_text()
        grid = (static_dir / "calendar-grid.js").read_text()

        self.assertIn(".calendar-shell { --calendar-sidebar-width: 240px; grid-template-columns: var(--calendar-sidebar-width) minmax(0, 1fr);", styles)
        self.assertIn("grid-template-columns: var(--calendar-sidebar-width) minmax(0, 1fr) auto auto;", styles)
        self.assertIn(".calendar-settings-shell { --calendar-settings-sidebar-width: 208px;", styles)
        self.assertIn(".calendar-settings-main { margin: 0; max-width: none; min-height: 0; overflow-y: auto;", styles)
        self.assertIn(".calendar-settings-sidebar { min-height: 0; overflow-y: auto;", styles)
        self.assertIn(".calendar-sidebar { min-height: 0; overflow-y: auto;", styles)
        self.assertIn(".calendar-main { min-height: 0; overflow: hidden; padding: 0;", styles)
        self.assertIn(".calendar-page .calendar-projection { border: 0; border-radius: 0;", styles)
        self.assertIn("grid-template-rows: repeat(var(--calendar-week-count), minmax(0, 1fr));", styles)
        self.assertIn(".calendar-current-time { border-top: 2px solid var(--color-calendar-current-time);", styles)
        self.assertIn('toggle.setAttribute("aria-expanded", String(!expanded));', groups)
        self.assertIn("content.hidden = expanded;", groups)
        self.assertNotIn('input[name="calendars"]', groups)
        self.assertIn('timeZone: timezone', grid)
        self.assertIn("Number(parts.hour) * 60 + Number(parts.minute)", grid)
        self.assertIn("window.setInterval(updateCurrentTime, 60_000);", grid)
        self.assertTrue((static_dir / "icons" / "settings.svg").is_file())

    def test_event_recurrence_picker_maps_create_and_edit_presets(self) -> None:
        cases = [
            ("2026-09-10", "daily", ("daily", (), 0, -1)),
            ("2026-09-10", "weekly_3", ("weekly", (3,), 0, -1)),
            ("2026-09-14", "monthly_2_0", ("monthly", (), 2, 0)),
            ("2026-09-28", "monthly_last_0", ("monthly", (), -1, 0)),
            ("2024-02-29", "yearly", ("yearly", (), 0, -1)),
            ("2026-09-10", "weekdays", ("weekly", (0, 1, 2, 3, 4), 0, -1)),
        ]
        for index, (start_date, preset, expected) in enumerate(cases):
            event_id = create_event(self.connection, EventInput(f"Preset {index}", True, start_date=start_date, end_date=start_date))
            event = get_event(self.connection, event_id)
            rule = EddyRequestHandler.recurrence_rule_from_form({"recurrence_preset": preset}, event)
            definition = set_recurrence(self.connection, event, rule)
            self.assertEqual(expected, (definition.rule.frequency, definition.rule.weekdays, definition.rule.monthly_ordinal, definition.rule.monthly_weekday))

        calendars = list_calendars(self.connection, include_archived=True)
        fourth_monday = views.event_form_page(calendars, {"all_day": "1", "start_date": "2026-09-28"})
        fifth_monday = views.event_form_page(calendars, {"all_day": "1", "start_date": "2026-03-30"})
        self.assertIn("Monthly on the fourth Monday", fourth_monday)
        self.assertIn("Monthly on the last Monday", fourth_monday)
        self.assertNotIn("Monthly on the fifth Monday", fifth_monday)
        self.assertIn("Monthly on the last Monday", fifth_monday)
        self.assertIn('value="custom"', fourth_monday)

        custom_event_id = create_event(self.connection, EventInput("Custom", True, start_date="2026-01-05", end_date="2026-01-05"))
        custom_event = get_event(self.connection, custom_event_id)
        custom_rule = EddyRequestHandler.recurrence_rule_from_form({
            "recurrence_preset": "custom", "recurrence_custom_interval": "1", "recurrence_custom_frequency": "week",
            "recurrence_custom_weekdays": "0,2", "recurrence_custom_ends": "after", "recurrence_custom_count": "3",
        }, custom_event)
        self.assertEqual(("weekly", (0, 2), "2026-01-12"), (custom_rule.frequency, custom_rule.weekdays, custom_rule.until_date))
        monthly_custom_rule = EddyRequestHandler.recurrence_rule_from_form({
            "recurrence_preset": "custom", "recurrence_custom_interval": "1", "recurrence_custom_frequency": "month",
            "recurrence_custom_monthly_pattern": "ordinal", "recurrence_custom_ends": "never",
        }, custom_event)
        self.assertEqual(("monthly", 1, 0), (monthly_custom_rule.frequency, monthly_custom_rule.monthly_ordinal, monthly_custom_rule.monthly_weekday))
        first_monday = views.event_form_page(calendars, {"all_day": "1", "start_date": "2024-01-01"})
        self.assertIn("on day 1 of the month", first_monday)
        self.assertIn("on the first Monday", first_monday)
        self.assertNotIn("data-custom-monthly-ordinal", first_monday)
        self.assertIn("on the last Monday", fourth_monday)
        last_monday_event_id = create_event(self.connection, EventInput("Last Monday", True, start_date="2026-09-28", end_date="2026-09-28"))
        last_monday_rule = EddyRequestHandler.recurrence_rule_from_form({
            "recurrence_preset": "custom", "recurrence_custom_interval": "1", "recurrence_custom_frequency": "month",
            "recurrence_custom_monthly_pattern": "last", "recurrence_custom_ends": "never",
        }, get_event(self.connection, last_monday_event_id))
        self.assertEqual(("monthly", -1, 0), (last_monday_rule.frequency, last_monday_rule.monthly_ordinal, last_monday_rule.monthly_weekday))
        self.assertIn("Custom recurrence", fourth_monday)
        self.assertIn("Repeat every", fourth_monday)
        self.assertIn("occurrences", fourth_monday)
        styles = (Path(__file__).resolve().parents[1] / "app" / "static" / "styles.css").read_text()
        self.assertIn('.custom-recurrence-ends input[type="radio"] { flex: 0 0 auto;', styles)
        self.assertIn('max-width: 24rem;', styles)
        self.assertIn('height: 1.75rem;', styles)
        self.assertIn('grid-template-columns: auto 4.5rem 5.5rem;', styles)

    def test_calendar_renders_month_week_filters_and_event_preview(self) -> None:
        work_calendar_id = create_calendar(
            self.connection, CalendarInput("Work", "#EF4444", "Europe/London")
        )
        all_day_id = create_event(
            self.connection,
            EventInput("Conference", True, start_date="2026-09-14", end_date="2026-09-16"),
        )
        create_event(
            self.connection,
            EventInput(
                "London call", False, work_calendar_id,
                timezone="Europe/London", start_local="2026-09-15T09:00",
                end_local="2026-09-15T10:00",
            ),
        )
        create_event(
            self.connection,
            EventInput(
                "Overnight focus", False, work_calendar_id,
                timezone="Australia/Brisbane", start_local="2026-09-15T18:00",
                end_local="2026-09-16T02:00",
            ),
        )
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            client.request("GET", "/calendar?view=month&date=2026-09-15")
            month_page = client.getresponse().read().decode()
            self.assertIn("September 2026", month_page)
            self.assertIn("Conference", month_page)
            self.assertIn("18:00 · </span>London call", month_page)
            self.assertIn("My calendars", month_page)

            client.request("GET", "/calendar?view=month&date=2026-09-15&calendars=1")
            filtered_page = client.getresponse().read().decode()
            self.assertNotIn("--calendar-colour:#EF4444", filtered_page)

            client.request("GET", "/calendar?view=week&date=2026-09-15")
            week_page = client.getresponse().read().decode()
            self.assertIn("September 2026", week_page)
            self.assertIn("Week 38", week_page)
            self.assertIn("calendar-time-grid", week_page)
            self.assertIn('data-calendar-time-grid-scroll', week_page)
            self.assertEqual(7, week_page.count("data-calendar-current-time"))
            self.assertIn('data-calendar-timezone="Australia/Brisbane"', week_page)
            self.assertIn("18:00–00:00", week_page)
            self.assertIn("00:00–02:00", week_page)
            self.assertIn("Overnight focus", week_page)
            self.assertIn('href="/calendar/settings?return_to=%2Fcalendar%3Fview%3Dweek%26date%3D2026-09-15"', week_page)

            client.request("GET", "/calendar?view=day&date=2026-09-15")
            day_page = client.getresponse().read().decode()
            self.assertIn('<h1 class="calendar-header-date">15 September 2026</h1>', day_page)
            self.assertNotIn('<h1 class="calendar-header-date">Tuesday,', day_page)
            self.assertIn('aria-label="2026-09-15"', day_page)
            self.assertEqual(1, day_page.count("data-calendar-current-time"))

            client.request("GET", f"/calendar?view=month&date=2026-09-15&preview={all_day_id}")
            preview_page = client.getresponse().read().decode()
            self.assertIn("Event preview", preview_page)
            self.assertIn(f'/calendar/events/{all_day_id}/delete', preview_page)

            client.request("POST", f"/calendar/events/{all_day_id}/delete", urlencode({"return_to": "/calendar?view=week&date=2026-09-15"}), {"Content-Type": "application/x-www-form-urlencoded"})
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertEqual("/calendar?view=week&date=2026-09-15&deleted=1", response.getheader("Location"))
            self.assertIsNone(get_event(self.connection, all_day_id))
        finally:
            client.close()
            server.shutdown()
            server.server_close()
            thread.join()

    def test_monthly_recurrence_projects_clamped_dates_without_duplicate_events(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput("Month end", True, start_date="2026-01-31", end_date="2026-01-31"),
        )
        event = get_event(self.connection, event_id)
        definition = set_recurrence(
            self.connection, event, RecurrenceRule("monthly", until_date="2026-04-30")
        )
        occurrences = occurrences_between(event, definition, date(2026, 1, 1), date(2026, 5, 1))
        self.assertEqual(
            ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
            [item.occurrence_date for item in occurrences],
        )
        self.assertEqual(1, self.connection.execute("SELECT COUNT(*) FROM entities WHERE type = 'event'").fetchone()[0])

        cancel_occurrence(self.connection, definition, "2026-03-31")
        remaining = occurrences_between(event, definition, date(2026, 1, 1), date(2026, 5, 1), exception_dates(self.connection, definition))
        self.assertNotIn("2026-03-31", [item.occurrence_date for item in remaining])

    def test_split_series_creates_traceable_successor(self) -> None:
        event_id = create_event(self.connection, EventInput("Stand-up", True, start_date="2026-01-05", end_date="2026-01-05"))
        event = get_event(self.connection, event_id)
        definition = set_recurrence(self.connection, event, RecurrenceRule("weekly"))
        successor_id = split_series(self.connection, event, definition, "2026-01-19")
        source = get_recurrence(self.connection, event_id)
        successor = get_event(self.connection, successor_id)
        self.assertEqual("2026-01-12", source.rule.until_date)
        self.assertEqual("2026-01-19", successor.start_date)
        self.assertIsNotNone(get_recurrence(self.connection, successor_id))
        self.assertEqual((event_id, successor_id, "2026-01-19"), tuple(self.connection.execute("SELECT source_event_id, successor_event_id, split_occurrence_date FROM event_recurrence_splits").fetchone()))
        self.assertIn("series_split", [item["event_type"] for item in list_entity_history(self.connection, event_id)])

    def test_recurring_occurrence_scope_routes_persist_override_and_cancellation(self) -> None:
        event_id = create_event(self.connection, EventInput("Stand-up", True, start_date="2026-01-05", end_date="2026-01-05"))
        event = get_event(self.connection, event_id)
        definition = set_recurrence(self.connection, event, RecurrenceRule("weekly"))
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            client.request("GET", "/calendar?view=week&date=2026-01-19")
            page = client.getresponse().read().decode()
            self.assertIn("occurrence=2026-01-19", page)
            client.request("GET", f"/calendar?view=week&date=2026-01-19&preview={event_id}&occurrence=2026-01-19")
            preview = client.getresponse().read().decode()
            self.assertIn('data-recurrence-delete-scope-dialog', preview)
            self.assertIn("Delete recurring event", preview)
            self.assertIn("This and following", preview)
            self.assertNotIn('<select name="recurrence_scope">', preview)
            styles = (Path(__file__).resolve().parents[1] / "app" / "static" / "styles.css").read_text()
            self.assertIn('.recurrence-scope-dialog[open] { display: grid;', styles)
            self.assertNotIn('.recurrence-scope-dialog { display: grid;', styles)
            client.request("GET", f"/calendar/events/{event_id}/edit?occurrence=2026-01-19")
            form = client.getresponse().read().decode()
            self.assertIn('data-recurrence-scope-dialog', form)
            self.assertIn("Edit recurring event", form)
            self.assertIn("This and following", form)
            self.assertNotIn('<select name="recurrence_scope">', form)
            body = urlencode({
                "title": "One-off stand-up", "calendar_id": "1", "all_day": "1",
                "start_date": "2026-01-19", "end_date": "2026-01-19", "notes": "Exception",
                "occurrence_date": "2026-01-19", "recurrence_scope": "this",
                "recurrence_frequency": "weekly", "recurrence_interval": "1",
            })
            client.request("POST", f"/calendar/events/{event_id}/edit", body, {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(303, client.getresponse().status)
            projected = occurrences_between(event, definition, date(2026, 1, 19), date(2026, 1, 19), occurrence_exceptions(self.connection, definition))
            self.assertEqual("One-off stand-up", projected[0].event.title)
            self.assertEqual("Stand-up", get_event(self.connection, event_id).title)
            delete_body = urlencode({"occurrence_date": "2026-01-26", "recurrence_scope": "this"})
            client.request("POST", f"/calendar/events/{event_id}/delete", delete_body, {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(303, client.getresponse().status)
            remaining = occurrences_between(event, definition, date(2026, 1, 26), date(2026, 1, 26), occurrence_exceptions(self.connection, definition))
            self.assertEqual([], remaining)
            split_body = urlencode({
                "title": "Future stand-up", "calendar_id": "1", "all_day": "1",
                "start_date": "2026-02-02", "end_date": "2026-02-02", "notes": "New series",
                "occurrence_date": "2026-02-02", "recurrence_scope": "following",
                "recurrence_frequency": "weekly", "recurrence_interval": "1",
            })
            client.request("POST", f"/calendar/events/{event_id}/edit", split_body, {"Content-Type": "application/x-www-form-urlencoded"})
            response = client.getresponse()
            self.assertEqual(303, response.status)
            successor_id = int(response.getheader("Location").split("/")[3])
            self.assertEqual("Future stand-up", get_event(self.connection, successor_id).title)
            self.assertEqual("2026-01-26", get_recurrence(self.connection, event_id).rule.until_date)
            audit = list_audit_events(self.connection, "entity", event_id)
            self.assertTrue(any("occurrence overridden" in item.notes.lower() for item in audit))
        finally:
            client.close()
            server.shutdown(); server.server_close(); thread.join()

    def test_calendar_settings_shell_and_routes_use_calendar_services(self) -> None:
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        return_to = "/calendar?view=week&date=2026-09-15&calendars=1"
        settings_query = urlencode({"return_to": return_to})
        try:
            client.request("GET", "/static/reminder-timings.js")
            script_response = client.getresponse()
            self.assertEqual(200, script_response.status)
            self.assertIn("data-add-reminder-timing", script_response.read().decode())

            client.request("GET", f"/calendar/settings?{settings_query}")
            page = client.getresponse().read().decode()
            self.assertIn('class="app-shell calendar-settings-shell"', page)
            self.assertIn('<aside class="sidebar calendar-settings-sidebar" aria-label="Calendar settings">', page)
            self.assertIn('class="calendar-settings-back" href="/calendar?view=week&amp;date=2026-09-15&amp;calendars=1"', page)
            self.assertIn('<a class="active" aria-current="page" href="/calendar/settings?', page)
            self.assertIn('title="Coming soon!">General</a>', page)
            self.assertIn("<span>Add Calendar</span>", page)
            self.assertIn("<span>Import/Export</span>", page)
            self.assertIn("Settings for my calendars", page)
            self.assertIn('class="calendar-colour" style="background:#2563EB"', page)
            self.assertNotIn('class="brand"', page)
            self.assertNotIn('class="global-search-link"', page)
            self.assertNotIn('aria-label="Browse"', page)
            self.assertNotIn(">Export</a>", page)
            self.assertIn("Coming soon!", page)

            client.request("GET", f"/calendar/settings/import?{settings_query}")
            import_page = client.getresponse().read().decode()
            self.assertIn('aria-current="page" href="/calendar/settings/import?', import_page)
            self.assertNotIn('title="Coming soon!">Import</a>', import_page)
            self.assertIn(">Export</a>", import_page)
            self.assertIn("Supported now: UTF-8 iCalendar 2.0", import_page)
            self.assertNotIn("/system-tools/portability", import_page)

            client.request("GET", f"/calendar/settings/discover?{settings_query}")
            discover_page = client.getresponse().read().decode()
            self.assertIn("<h1>Browse calendars of interest</h1>", discover_page)
            self.assertIn("Coming soon!", discover_page)
            client.request("GET", f"/calendar/settings/from-url?{settings_query}")
            from_url_page = client.getresponse().read().decode()
            self.assertIn("<h1>From URL</h1>", from_url_page)
            self.assertIn("Public iCalendar HTTPS URL", from_url_page)
            client.request("GET", f"/calendar/settings/export?{settings_query}")
            export_page = client.getresponse().read().decode()
            self.assertIn("<h1>Export</h1>", export_page)
            self.assertIn("Download ZIP", export_page)

            client.request("POST", f"/calendar/settings/import?{settings_query}", "", {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(400, client.getresponse().status)

            client.request("GET", "/calendar/settings?return_to=https%3A%2F%2Fexample.com")
            safe_page = client.getresponse().read().decode()
            self.assertIn('class="calendar-settings-back" href="/calendar"', safe_page)
            self.assertNotIn('href="https://example.com"', safe_page)

            client.request("GET", f"/calendar/settings/add?{settings_query}")
            add_page = client.getresponse().read().decode()
            self.assertIn("<h1>Create New Calendar</h1>", add_page)
            self.assertIn('class="calendar-settings-disclosure" open', add_page)
            self.assertIn('class="calendar-colour-picker"', add_page)
            self.assertIn('action="/calendar/settings/add"', add_page)
            self.assertIn('action="/calendar/settings/add" data-dirty-form', add_page)
            self.assertNotIn('name="timezone"', add_page)
            self.assertNotIn('name="default_event_duration_minutes"', add_page)
            self.assertNotIn('name="sort_order"', add_page)
            body = urlencode({"name": "Work", "colour": "#EF4444", "timezone": "Europe/London", "default_event_duration_minutes": "45", "sort_order": "2", "return_to": return_to})
            client.request("POST", "/calendar/settings/add", body, {"Content-Type": "application/x-www-form-urlencoded"})
            response = client.getresponse()
            self.assertEqual(303, response.status)
            work = next(item for item in list_calendars(self.connection) if item.name == "Work")
            self.assertEqual("Australia/Brisbane", work.timezone)
            self.assertEqual(60, work.default_event_duration_minutes)
            expected_location = f"/calendar/settings/calendars/{work.id}?return_to=%2Fcalendar%3Fview%3Dweek%26date%3D2026-09-15%26calendars%3D1&saved=1"
            self.assertEqual(expected_location, response.getheader("Location"))

            client.request("GET", response.getheader("Location"))
            created_page = client.getresponse().read().decode()
            self.assertIn(f'class="calendar-settings-calendar active" href="/calendar/settings/calendars/{work.id}', created_page)
            self.assertIn('aria-current="page"><span class="calendar-colour" style="background:#EF4444"></span><span>Work</span></a>', created_page)

            action_body = urlencode({"return_to": return_to})
            client.request("POST", f"/calendar/settings/calendars/{work.id}/default", action_body, {"Content-Type": "application/x-www-form-urlencoded"})
            action_response = client.getresponse()
            self.assertEqual(303, action_response.status)
            self.assertTrue(get_calendar(self.connection, work.id).is_default)

            client.request("POST", "/calendar/settings/calendars/1/archive", action_body, {"Content-Type": "application/x-www-form-urlencoded"})
            archive_response = client.getresponse()
            self.assertEqual(303, archive_response.status)
            self.assertTrue(get_calendar(self.connection, 1, include_archived=True).is_archived)
            client.request("GET", archive_response.getheader("Location"))
            archived_page = client.getresponse().read().decode()
            self.assertIn("<h3>Archived calendars</h3>", archived_page)
            self.assertIn("General<small>Archived</small>", archived_page)
            self.assertIn(">Unarchive</button>", archived_page)
            client.request("POST", "/calendar/settings/calendars/1/unarchive", action_body, {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(303, client.getresponse().status)
            self.assertFalse(get_calendar(self.connection, 1).is_archived)

            client.request("GET", f"/calendar/settings/calendars/{work.id}?{settings_query}")
            notification_page = client.getresponse().read().decode()
            self.assertNotIn('name="reminder_mode"', notification_page)
            self.assertIn('data-add-reminder-timing', notification_page)
            self.assertIn('action="/calendar/settings/calendars/', notification_page)
            self.assertIn('" data-dirty-form>', notification_page)
            self.assertIn("Calendar status", notification_page)
            custom_settings = urlencode({"name": "Work", "colour": "#EF4444", "timezone": "Europe/London", "default_event_duration_minutes": "45", "sort_order": "2", "calendar_reminder_amount_0": "15", "calendar_reminder_unit_0": "m", "calendar_reminder_amount_1": "2", "calendar_reminder_unit_1": "h", "return_to": return_to})
            client.request("POST", f"/calendar/settings/calendars/{work.id}", custom_settings, {"Content-Type": "application/x-www-form-urlencoded"})
            edit_response = client.getresponse()
            self.assertEqual(303, edit_response.status)
            self.assertEqual(expected_location, edit_response.getheader("Location"))
            self.assertEqual(["15m", "2h"], get_policy(self.connection, "calendar", work.id, "event"))
            settings = urlencode({"name": "Work", "colour": "#EF4444", "timezone": "Europe/London", "default_event_duration_minutes": "45", "sort_order": "2", "return_to": return_to})
            client.request("POST", f"/calendar/settings/calendars/{work.id}", settings, {"Content-Type": "application/x-www-form-urlencoded"})
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertIsNone(get_policy(self.connection, "calendar", work.id, "event"))

            event_id = create_event(self.connection, EventInput("Structured reminder", False, calendar_id=work.id, start_local="2026-10-01T10:00", end_local="2026-10-01T11:00"))
            client.request("GET", f"/calendar/events/{event_id}/reminders")
            event_notification_page = client.getresponse().read().decode()
            self.assertNotIn('name="mode"', event_notification_page)
            self.assertIn("uses its Calendar notifications", event_notification_page)
            client.request("POST", f"/calendar/events/{event_id}/reminders", urlencode({"custom_reminder_amount_0": "30", "custom_reminder_unit_0": "m"}), {"Content-Type": "application/x-www-form-urlencoded"})
            self.assertEqual(303, client.getresponse().status)
            self.assertEqual(["30m"], get_override(self.connection, "event", event_id)["custom_timings"])
        finally:
            client.close()
            server.shutdown(); server.server_close(); thread.join()

    def test_create_rejects_invalid_time_and_rolls_back_identity(self) -> None:
        with self.assertRaises(TemporalValueError):
            create_event(
                self.connection,
                EventInput(
                    title="Invalid",
                    all_day=False,
                    timezone="Australia/Sydney",
                    start_local="2026-10-04T02:30",
                    end_local="2026-10-04T03:30",
                ),
            )

        count = self.connection.execute(
            "SELECT COUNT(*) FROM entities WHERE type = 'event'"
        ).fetchone()[0]
        self.assertEqual(0, count)

    def test_update_changes_details_without_rescheduling(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Conference",
                all_day=False,
                start_local="2026-09-01T09:00",
                end_local="2026-09-01T10:00",
            ),
        )

        update_event(
            self.connection,
            event_id,
            EventUpdate(
                title="Conference day",
                notes="Updated details",
            ),
        )

        event = get_event(self.connection, event_id)
        history = list_entity_history(self.connection, event_id)
        audits = list_audit_events(self.connection, "entity", event_id)
        details = json.loads(history[0]["details"])
        self.assertEqual("Conference day", event.title)
        self.assertFalse(event.is_all_day)
        self.assertFalse(event.is_cancelled)
        self.assertEqual("Conference", details["before"]["title"])
        self.assertEqual("Conference day", details["after"]["title"])
        self.assertEqual(["edit", "create"], [audit.action for audit in audits])

    def test_cancel_reinstate_and_reschedule_are_dedicated_operations(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Conference",
                all_day=False,
                start_local="2026-09-01T09:00",
                end_local="2026-09-01T10:00",
            ),
        )

        self.assertTrue(cancel_event(self.connection, event_id))
        self.assertFalse(cancel_event(self.connection, event_id))
        self.assertTrue(get_event(self.connection, event_id).is_cancelled)
        self.assertTrue(reinstate_event(self.connection, event_id))
        self.assertFalse(reinstate_event(self.connection, event_id))
        self.assertTrue(
            reschedule_event(
                self.connection,
                event_id,
                EventSchedule(
                    all_day=True,
                    start_date="2026-09-02",
                    end_date="2026-09-02",
                ),
            )
        )
        event = get_event(self.connection, event_id)
        self.assertTrue(event.is_all_day)
        self.assertEqual("2026-09-02", event.start_date)
        actions = [
            audit.action
            for audit in list_audit_events(self.connection, "entity", event_id)
        ]
        self.assertEqual(
            ["reschedule", "reinstate", "cancel", "create"], actions
        )

    def test_archive_is_distinct_recoverable_state(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Old plan",
                all_day=True,
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        )

        self.assertTrue(archive_event(self.connection, event_id))
        self.assertFalse(archive_event(self.connection, event_id))
        self.assertIsNone(get_event(self.connection, event_id))
        archived = get_event(self.connection, event_id, include_archived=True)
        self.assertTrue(archived.is_archived)
        self.assertEqual("", archived.deleted_at)
        self.assertEqual([], list_events(self.connection))
        self.assertEqual(1, len(list_events(self.connection, include_archived=True)))

        self.assertTrue(unarchive_event(self.connection, event_id))
        self.assertFalse(unarchive_event(self.connection, event_id))
        self.assertIsNotNone(get_event(self.connection, event_id))
        history_types = [
            row["event_type"] for row in list_entity_history(self.connection, event_id)
        ]
        self.assertEqual(["unarchive", "archive"], history_types)
        audit_actions = [
            event.action
            for event in list_audit_events(self.connection, "entity", event_id)
        ]
        self.assertEqual(["unarchive", "archive", "create"], audit_actions)

    def test_archived_calendar_can_be_retained_but_not_newly_selected(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Existing",
                all_day=True,
                start_date="2026-02-01",
                end_date="2026-02-01",
            ),
        )
        self.connection.execute(
            "UPDATE calendars SET archived_at = 'archived' WHERE is_default = 1"
        )
        self.connection.commit()

        update_event(
            self.connection,
            event_id,
            EventUpdate(
                title="Existing renamed",
            ),
        )
        with self.assertRaisesRegex(ValueError, "default calendar"):
            create_event(
                self.connection,
                EventInput(
                    title="New",
                    all_day=True,
                    start_date="2026-02-02",
                    end_date="2026-02-02",
                ),
            )

    def test_recycle_bin_restore_preserves_archive_and_cancellation(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Preserved state",
                all_day=True,
                start_date="2026-04-01",
                end_date="2026-04-01",
            ),
        )
        cancel_event(self.connection, event_id)
        archive_event(self.connection, event_id)

        delete_entity(self.connection, EVENT_DEFINITION, event_id)
        self.assertTrue(restore_entity(self.connection, event_id))

        event = get_event(self.connection, event_id, include_archived=True)
        self.assertTrue(event.is_archived)
        self.assertTrue(event.is_cancelled)

    def test_database_constraints_keep_temporal_modes_exclusive(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                title="Constrained",
                all_day=True,
                start_date="2026-03-01",
                end_date="2026-03-01",
            ),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                "UPDATE events SET start_utc = '2026-03-01T00:00:00Z' "
                "WHERE entity_id = ?",
                (event_id,),
            )
        self.connection.rollback()

    def test_corrective_migration_preserves_existing_event_identity_and_state(
        self,
    ) -> None:
        legacy_path = Path(self.directory.name) / "legacy-events.sqlite3"
        with connect(legacy_path) as connection:
            create_entity_table(connection)
            create_initial_temporal_foundation_tables(connection)
            create_initial_event_table(connection)
            create_schema_migration_table(connection)
            connection.executemany(
                """
                INSERT INTO schema_migrations (migration_id, applied_at)
                VALUES (?, 'already-applied')
                """,
                (
                    ("20260719_16_temporal_foundation",),
                    ("20260719_17_canonical_events",),
                ),
            )
            connection.execute(
                """
                INSERT INTO entities (
                    id, type, display_name, summary, notes,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    41, 'event', 'Legacy Event', '', '',
                    'created', 'updated', ''
                )
                """
            )
            calendar_id = connection.execute(
                "SELECT id FROM calendars WHERE is_default = 1"
            ).fetchone()[0]
            category_id = connection.execute(
                "SELECT id FROM event_categories WHERE is_default = 1"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO events (
                    entity_id, calendar_id, category_id, is_all_day,
                    start_date, end_date_exclusive, date_precision,
                    status, archived_at
                ) VALUES (
                    41, ?, ?, 1, '2026-05-01', '2026-05-02',
                    'exact', 'cancelled', 'archived'
                )
                """,
                (calendar_id, category_id),
            )
            create_schema(connection)
            columns = {
                row["name"] for row in connection.execute(
                    "PRAGMA table_info(events)"
                )
            }
            category_table = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'event_categories'
                """
            ).fetchone()
            event = connection.execute(
                "SELECT * FROM events WHERE entity_id = 41"
            ).fetchone()
            calendar = connection.execute(
                "SELECT * FROM calendars WHERE id = ?", (calendar_id,)
            ).fetchone()
        self.assertNotIn("category_id", columns)
        self.assertIsNone(category_table)
        self.assertEqual("cancelled", event["status"])
        self.assertEqual("archived", event["archived_at"])
        self.assertEqual(calendar_id, event["calendar_id"])
        self.assertEqual("General", calendar["name"])


    def test_month_projection_bounds_day_entries_and_links_overflow_to_day(self) -> None:
        for index in range(4):
            create_event(self.connection, EventInput(
                title=f"Busy {index}", all_day=True,
                start_date="2026-09-10", end_date="2026-09-10",
            ))
        calendars = list_calendars(self.connection)
        projection = views.calendar_projection(
            list_events(self.connection), calendars, view="month", anchor_date=date(2026, 9, 10),
            selected_calendar_ids={calendar.id for calendar in calendars}, preview_event=None,
        )
        self.assertEqual(3, projection.count('class="calendar-event"'))
        self.assertIn('data-calendar-id="1"', projection)
        self.assertIn('class="calendar-day-overflow" href="/calendar?view=day&amp;date=2026-09-10&amp;calendars=1&amp;calendars=2">+ 1 more</a>', projection)
        self.assertNotIn("Derived and related dates", projection)


if __name__ == "__main__":
    unittest.main()
