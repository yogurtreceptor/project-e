import http.client
import io
import re
import tempfile
import threading
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode
import zipfile

from app.audit import get_provenance, list_audit_events
from app.calendar_service import (
    CalendarInput,
    archive_calendar,
    create_calendar,
    get_calendar,
    list_calendars,
    reorder_calendars,
)
from app.calendar_subscription_service import (
    _PublicRedirectHandler,
    SubscriptionFetch,
    SubscriptionSettingsInput,
    create_subscription,
    get_subscription,
    list_subscriptions,
    refresh_due_subscriptions,
    refresh_subscription,
    remove_subscription,
    reorder_subscriptions,
    set_subscription_enabled,
    subscription_projection,
    update_subscription_settings,
    validate_public_https_url,
)
from app.db import connect, initialise_database
from app.event_recurrence import (
    RecurrenceRule,
    get_recurrence,
    occurrences_between,
    set_recurrence,
)
from app.event_service import EventInput, create_event, get_event, list_events
from app.reminder_service import (
    evaluate_due_reminders,
    get_policy,
    list_inbox_items,
    set_policy,
)
from app.icalendar_service import (
    MAX_ICALENDAR_BYTES,
    apply_icalendar_import,
    create_calendar_export,
    inspect_icalendar_import,
    parse_icalendar,
    read_staged_icalendar,
    stage_icalendar,
)
from app.view_pages.calendar import (
    _calendar_period,
    calendar_header,
    calendar_projection,
    calendar_settings_create_page,
    calendar_settings_edit_page,
    calendar_settings_export_page,
)
from app.view_pages.inbox import inbox_page
from app.web import EddyRequestHandler, ThreadingHTTPServer


FICTIONAL_ICS = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//Fictional Test Suite//EN\r
CALSCALE:GREGORIAN\r
METHOD:PUBLISH\r
X-WR-CALNAME:Fictional Observances\r
X-WR-TIMEZONE:Australia/Brisbane\r
BEGIN:VEVENT\r
UID:fictional-one@example.test\r
SEQUENCE:2\r
DTSTAMP:20260701T000000Z\r
DTSTART;VALUE=DATE:20260730\r
DTEND;VALUE=DATE:20260731\r
SUMMARY:Fictional Day\r
DESCRIPTION:A folded description that is \r
 continued\\, with punctuation\\; and a newline\\nSecond line\r
RRULE:FREQ=YEARLY\r
STATUS:CONFIRMED\r
TRANSP:TRANSPARENT\r
END:VEVENT\r
END:VCALENDAR\r
"""

SECOND_ICS = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
X-WR-CALNAME:Second Source\r
X-WR-TIMEZONE:Australia/Brisbane\r
BEGIN:VEVENT\r
UID:fictional-two@example.test\r
DTSTART;VALUE=DATE:20260801\r
DTEND;VALUE=DATE:20260803\r
SUMMARY:Two-day Fiction\r
STATUS:CANCELLED\r
END:VEVENT\r
END:VCALENDAR\r
"""


class CalendarInterchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "calendar-interchange.sqlite3"
        self.staging_path = Path(self.directory.name) / "staging"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_parser_unfolds_text_and_maps_all_day_yearly_recurrence(self) -> None:
        document = parse_icalendar(FICTIONAL_ICS)
        event = document.events[0]
        self.assertEqual("Fictional Observances", document.name)
        self.assertEqual("Australia/Brisbane", document.timezone)
        self.assertEqual("A folded description that is continued, with punctuation; and a newline\nSecond line", event.description)
        self.assertEqual(("2026-07-30", "2026-07-31"), (event.start_date, event.end_date_exclusive))
        self.assertEqual("yearly", event.recurrence.frequency)
        self.assertIn("transparency", event.warnings[0])
        self.assertTrue(document.can_apply)

    def test_parser_rejects_malformed_duplicate_and_meaningful_loss(self) -> None:
        with self.assertRaisesRegex(ValueError, "2 MB"):
            parse_icalendar(b"X" * (MAX_ICALENDAR_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "VERSION"):
            parse_icalendar(FICTIONAL_ICS.replace(b"VERSION:2.0\r\n", b""))
        duplicate = FICTIONAL_ICS.replace(
            b"UID:fictional-one@example.test\r\n",
            b"UID:fictional-one@example.test\r\nUID:duplicate@example.test\r\n",
        )
        self.assertTrue(any(
            "repeats singleton property UID" in item
            for item in parse_icalendar(duplicate).events[0].blockers
        ))
        with_location = FICTIONAL_ICS.replace(
            b"SUMMARY:Fictional Day\r\n",
            b"SUMMARY:Fictional Day\r\nLOCATION:Fictional Hall\r\n",
        )
        self.assertIn("unsupported LOCATION", parse_icalendar(with_location).events[0].blockers[0])
        with_todo = FICTIONAL_ICS.replace(
            b"END:VCALENDAR",
            b"BEGIN:VTODO\r\nUID:todo@example.test\r\nEND:VTODO\r\nEND:VCALENDAR",
        )
        self.assertIn("VTODO", parse_icalendar(with_todo).blockers[0])

    def test_recurrence_count_uses_monday_week_intervals_and_matching_start(self) -> None:
        every_other_week = FICTIONAL_ICS.replace(
            b"RRULE:FREQ=YEARLY",
            b"RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,TH;COUNT=3",
        )
        rule = parse_icalendar(every_other_week).events[0].recurrence
        self.assertEqual(("weekly", 2, (0, 3), "2026-08-13"), (
            rule.frequency, rule.interval, rule.weekdays, rule.until_date,
        ))
        mismatched_start = FICTIONAL_ICS.replace(
            b"RRULE:FREQ=YEARLY",
            b"RRULE:FREQ=WEEKLY;BYDAY=MO",
        )
        self.assertTrue(any(
            "DTSTART does not match" in blocker
            for blocker in parse_icalendar(mismatched_start).events[0].blockers
        ))

    def test_fifth_weekday_recurrence_skips_months_without_a_fifth(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                "Fifth Monday",
                True,
                start_date="2026-03-30",
                end_date="2026-03-30",
            ),
        )
        event = get_event(self.connection, event_id)
        definition = set_recurrence(
            self.connection,
            event,
            RecurrenceRule("monthly", monthly_ordinal=5, monthly_weekday=0),
        )
        self.assertEqual(
            ["2026-03-30", "2026-06-29"],
            [
                item.occurrence_date
                for item in occurrences_between(
                    event, definition, date(2026, 3, 1), date(2026, 6, 30)
                )
            ],
        )

    def test_preview_and_confirm_import_one_event_into_general(self) -> None:
        preview = inspect_icalendar_import(
            self.connection, FICTIONAL_ICS, filename="fictional.ics"
        )
        self.assertEqual("new", preview.events[0].classification)
        self.assertEqual(0, len(list_events(self.connection)))

        result = apply_icalendar_import(
            self.connection, FICTIONAL_ICS, destination_calendar_id=1
        )
        event = get_event(self.connection, result.created_event_ids[0])
        self.assertEqual(1, event.calendar_id)
        self.assertEqual("Fictional Day", event.title)
        self.assertEqual("yearly", get_recurrence(self.connection, event.id).rule.frequency)
        self.assertEqual("imported", get_provenance(self.connection, "entity", event.id)["title"])
        self.assertTrue(any(item.action == "import" for item in list_audit_events(self.connection, "calendar", 1)))

    def test_repeat_is_noop_and_changed_uid_is_conflict(self) -> None:
        first = apply_icalendar_import(
            self.connection, FICTIONAL_ICS, destination_calendar_id=1
        )
        repeat = apply_icalendar_import(
            self.connection, FICTIONAL_ICS, destination_calendar_id=1
        )
        self.assertEqual((), repeat.created_event_ids)
        self.assertEqual(first.created_event_ids, repeat.unchanged_event_ids)
        changed = FICTIONAL_ICS.replace(b"SUMMARY:Fictional Day", b"SUMMARY:Changed Fiction")
        self.assertEqual(
            "conflicting",
            inspect_icalendar_import(self.connection, changed).events[0].classification,
        )
        with self.assertRaisesRegex(ValueError, "reviewed update workflow"):
            apply_icalendar_import(self.connection, changed, destination_calendar_id=1)
        self.assertEqual(1, len(list_events(self.connection)))

    def test_new_calendar_import_uses_explicit_destination_and_atomic_defaults(self) -> None:
        extra_event = FICTIONAL_ICS[
            FICTIONAL_ICS.index(b"BEGIN:VEVENT"):
            FICTIONAL_ICS.index(b"END:VCALENDAR")
        ]
        multi_event = SECOND_ICS.replace(
            b"END:VCALENDAR",
            extra_event + b"END:VCALENDAR",
        )
        result = apply_icalendar_import(
            self.connection,
            multi_event,
            new_calendar=CalendarInput(
                "Imported Fiction",
                "#7C3AED",
                "Australia/Brisbane",
                60,
                2,
            ),
        )
        calendar = get_calendar(self.connection, result.calendar_id)
        events = [get_event(self.connection, item) for item in result.created_event_ids]
        self.assertEqual(("Imported Fiction", 60, 2), (calendar.name, calendar.default_event_duration_minutes, calendar.sort_order))
        self.assertEqual(2, len(events))
        self.assertTrue(all(event.calendar_id == calendar.id for event in events))
        self.assertEqual({"cancelled", "planned"}, {event.status for event in events})
        blocked = SECOND_ICS.replace(
            b"SUMMARY:Two-day Fiction\r\n",
            b"SUMMARY:Two-day Fiction\r\nATTENDEE:mailto:person@example.test\r\n",
        )
        before = len(list_calendars(self.connection, include_archived=True))
        with self.assertRaisesRegex(ValueError, "ATTENDEE"):
            apply_icalendar_import(
                self.connection,
                blocked,
                new_calendar=CalendarInput("Must Roll Back"),
            )
        self.assertEqual(before, len(list_calendars(self.connection, include_archived=True)))

    def test_staging_token_is_bounded_and_single_use(self) -> None:
        token = stage_icalendar(FICTIONAL_ICS, self.staging_path)
        self.assertEqual(FICTIONAL_ICS, read_staged_icalendar(token, self.staging_path))
        self.assertEqual(
            FICTIONAL_ICS,
            read_staged_icalendar(token, self.staging_path, consume=True),
        )
        with self.assertRaisesRegex(ValueError, "expired or does not exist"):
            read_staged_icalendar(token, self.staging_path)

    def test_selectable_zip_export_preserves_members_uids_and_empty_calendars(self) -> None:
        apply_icalendar_import(
            self.connection, FICTIONAL_ICS, destination_calendar_id=1
        )
        empty_id = create_calendar(self.connection, CalendarInput("Empty / Fiction"))
        content = create_calendar_export(
            self.connection, ["local:1", f"local:{empty_id}"]
        )
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(2, len(archive.namelist()))
            general = next(name for name in archive.namelist() if "general" in name)
            empty = next(name for name in archive.namelist() if "empty-fiction" in name)
            parsed = parse_icalendar(archive.read(general))
            self.assertEqual("fictional-one@example.test", parsed.events[0].uid)
            self.assertEqual(0, len(parse_icalendar(archive.read(empty)).events))

    def test_export_is_all_or_nothing_for_timed_events_and_bad_selection(self) -> None:
        create_event(
            self.connection,
            EventInput(
                "Timed",
                False,
                start_local="2026-07-30T09:00",
                end_local="2026-07-30T10:00",
            ),
        )
        with self.assertRaisesRegex(ValueError, "timed"):
            create_calendar_export(self.connection, ["local:1"])
        with self.assertRaisesRegex(ValueError, "at least one"):
            create_calendar_export(self.connection, [])
        with self.assertRaisesRegex(ValueError, "invalid source"):
            create_calendar_export(self.connection, ["local:999", "tampered"])

    def test_export_blocks_recurrence_and_date_precision_that_would_change_meaning(self) -> None:
        event_id = create_event(
            self.connection,
            EventInput(
                "Month end",
                True,
                start_date="2026-01-31",
                end_date="2026-01-31",
            ),
        )
        set_recurrence(
            self.connection,
            get_event(self.connection, event_id),
            RecurrenceRule("monthly"),
        )
        with self.assertRaisesRegex(ValueError, "month-end"):
            create_calendar_export(self.connection, ["local:1"])

        self.connection.execute(
            "DELETE FROM entities WHERE id = ?",
            (event_id,),
        )
        self.connection.commit()
        create_event(
            self.connection,
            EventInput(
                "Approximate",
                True,
                start_date="2026-02-01",
                end_date="2026-02-01",
                date_precision="approximate",
            ),
        )
        with self.assertRaisesRegex(ValueError, "approximate"):
            create_calendar_export(self.connection, ["local:1"])

    def test_url_subscription_is_separate_cached_and_projected_read_only(self) -> None:
        fetched = self.subscription_fetch(FICTIONAL_ICS)
        subscription_id = create_subscription(self.connection, fetched)
        self.assertEqual(0, len(list_events(self.connection)))
        self.assertEqual(2, len(list_calendars(self.connection)))
        projection = subscription_projection(self.connection)
        self.assertEqual(-subscription_id, projection.calendars[0].id)
        self.assertEqual("external", projection.calendars[0].kind)
        self.assertEqual("Fictional Day", projection.events[0].title)
        self.assertEqual(-subscription_id, projection.events[0].calendar_id)

    def test_url_calendar_settings_and_reminders_use_stable_cached_occurrences(
        self,
    ) -> None:
        subscription_id = create_subscription(
            self.connection, self.subscription_fetch(FICTIONAL_ICS)
        )
        external_event_id = int(self.connection.execute(
            """SELECT id FROM external_calendar_events
               WHERE subscription_id = ?""",
            (subscription_id,),
        ).fetchone()["id"])

        self.assertTrue(update_subscription_settings(
            self.connection,
            subscription_id,
            SubscriptionSettingsInput(
                "Personal observances", "#123ABC", "Pacific/Auckland"
            ),
        ))
        set_policy(
            self.connection,
            "calendar_subscription",
            subscription_id,
            "event",
            ["1d"],
        )

        self.assertEqual(
            1,
            evaluate_due_reminders(
                self.connection,
                now=datetime(2026, 7, 28, 23, 0, tzinfo=UTC),
            ),
        )
        item = list_inbox_items(self.connection)[0]
        self.assertEqual("event", item.source_kind)
        self.assertEqual(-external_event_id, item.source_id)
        self.assertEqual("2026-07-30", item.occurrence_key)
        self.assertIn(
            f"external_preview=-{external_event_id}",
            inbox_page([item], archived=False),
        )

        renamed_feed = FICTIONAL_ICS.replace(
            b"Fictional Observances", b"Remote source name"
        ).replace(
            b"X-WR-TIMEZONE:Australia/Brisbane",
            b"X-WR-TIMEZONE:Europe/London",
        )
        self.assertTrue(refresh_subscription(
            self.connection,
            subscription_id,
            fetcher=lambda *args, **kwargs: self.subscription_fetch(renamed_feed),
        ))
        source = get_subscription(self.connection, subscription_id)
        self.assertEqual("Personal observances", source.name)
        self.assertEqual("#123ABC", source.colour)
        self.assertEqual("Pacific/Auckland", source.timezone)
        self.assertEqual(
            external_event_id,
            int(self.connection.execute(
                """SELECT id FROM external_calendar_events
                   WHERE subscription_id = ?""",
                (subscription_id,),
            ).fetchone()["id"]),
        )
        self.assertEqual(
            ["1d"],
            get_policy(
                self.connection,
                "calendar_subscription",
                subscription_id,
                "event",
            ),
        )

        self.assertTrue(
            set_subscription_enabled(self.connection, subscription_id, False)
        )
        self.assertEqual(
            "resolved",
            self.connection.execute(
                "SELECT state FROM inbox_items WHERE source_id = ?",
                (-external_event_id,),
            ).fetchone()["state"],
        )

    def test_refresh_swaps_valid_cache_and_retains_stale_cache_on_error(self) -> None:
        subscription_id = create_subscription(
            self.connection, self.subscription_fetch(FICTIONAL_ICS)
        )
        changed = SECOND_ICS.replace(b"Second Source", b"Fictional Observances")
        self.assertTrue(refresh_subscription(
            self.connection,
            subscription_id,
            fetcher=lambda *args, **kwargs: self.subscription_fetch(changed),
        ))
        self.assertEqual(
            ["Two-day Fiction"],
            [event.title for event in subscription_projection(self.connection).events],
        )
        self.assertFalse(refresh_subscription(
            self.connection,
            subscription_id,
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("offline")),
        ))
        self.assertEqual(
            ["Two-day Fiction"],
            [event.title for event in subscription_projection(self.connection).events],
        )
        self.assertEqual("offline", get_subscription(self.connection, subscription_id).current_error)

    def test_conditional_refresh_enable_disable_and_remove_lifecycle(self) -> None:
        subscription_id = create_subscription(
            self.connection, self.subscription_fetch(FICTIONAL_ICS)
        )
        self.connection.execute(
            """UPDATE calendar_subscriptions
               SET last_checked_at = '2026-07-28T00:00:00+00:00'
               WHERE id = ?""",
            (subscription_id,),
        )
        self.connection.commit()
        requests = []

        def not_modified(url, **kwargs):
            requests.append((url, kwargs))
            return SubscriptionFetch(
                url,
                url,
                b"",
                "text/calendar",
                kwargs["etag"],
                kwargs["last_modified"],
                None,
                True,
            )

        self.assertEqual(
            1,
            refresh_due_subscriptions(
                self.connection,
                now=datetime(2026, 7, 30, tzinfo=UTC),
                fetcher=not_modified,
            ),
        )
        self.assertEqual('"fictional-etag"', requests[0][1]["etag"])
        self.assertEqual(1, len(subscription_projection(self.connection).events))
        self.assertTrue(set_subscription_enabled(self.connection, subscription_id, False))
        self.assertEqual((), subscription_projection(self.connection).events)
        self.assertTrue(set_subscription_enabled(self.connection, subscription_id, True))
        remove_subscription(self.connection, subscription_id)
        self.assertIsNone(get_subscription(self.connection, subscription_id))
        self.assertEqual(0, self.connection.execute(
            "SELECT COUNT(*) FROM external_calendar_events"
        ).fetchone()[0])

    def test_group_ordering_requires_complete_untampered_lists(self) -> None:
        work_id = create_calendar(self.connection, CalendarInput("Work"))
        local_ids = [calendar.id for calendar in list_calendars(self.connection)]
        self.assertTrue(reorder_calendars(self.connection, list(reversed(local_ids))))
        self.assertEqual(
            list(reversed(local_ids)),
            [calendar.id for calendar in list_calendars(self.connection)],
        )
        with self.assertRaisesRegex(ValueError, "every active"):
            reorder_calendars(self.connection, [work_id])
        first = create_subscription(self.connection, self.subscription_fetch(FICTIONAL_ICS))
        second = create_subscription(self.connection, self.subscription_fetch(
            SECOND_ICS,
            url="https://example.com/second.ics",
        ))
        self.assertTrue(reorder_subscriptions(self.connection, [second, first]))
        self.assertEqual([second, first], [item.id for item in list_subscriptions(self.connection)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reorder_subscriptions(self.connection, [first, first])

    def test_public_url_validation_rejects_private_and_credentials(self) -> None:
        public = lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))]
        private = lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 443))]
        self.assertEqual(
            "https://example.com/calendar.ics",
            validate_public_https_url("https://example.com/calendar.ics", resolver=public),
        )
        with self.assertRaisesRegex(ValueError, "private or local"):
            validate_public_https_url("https://example.com/calendar.ics", resolver=private)
        with self.assertRaisesRegex(ValueError, "credentials"):
            validate_public_https_url(
                "https://user:secret@example.com/calendar.ics", resolver=public
            )
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_public_https_url("http://example.com/calendar.ics", resolver=public)
        redirect_handler = _PublicRedirectHandler(private)
        with self.assertRaisesRegex(ValueError, "private or local"):
            redirect_handler.redirect_request(
                None, None, 302, "Found", {}, "https://private.example/calendar.ics"
            )
        redirect_handler.redirects = 3
        with self.assertRaisesRegex(ValueError, "redirect limit"):
            redirect_handler.redirect_request(
                None, None, 302, "Found", {}, "https://example.com/calendar.ics"
            )

    def test_minimal_create_edit_forms_and_date_context(self) -> None:
        create_page = calendar_settings_create_page()
        self.assertIn('name="name"', create_page)
        self.assertIn('name="colour"', create_page)
        self.assertNotIn('name="timezone"', create_page)
        self.assertNotIn('name="default_event_duration_minutes"', create_page)
        self.assertNotIn('name="sort_order"', create_page)
        edit_page = calendar_settings_edit_page(get_calendar(self.connection, 1), None)
        self.assertIn('name="timezone"', edit_page)
        self.assertNotIn('name="sort_order"', edit_page)
        self.assertEqual("June 2026", _calendar_period("week", date(2026, 6, 10))[4])
        self.assertEqual("Jun \u2013 Jul 2026", _calendar_period("week", date(2026, 6, 30))[4])
        self.assertEqual("Dec 2026 \u2013 Jan 2027", _calendar_period("week", date(2026, 12, 31))[4])
        header = calendar_header(view="day", anchor_date=date(2026, 7, 30), selected_calendar_ids={1}, return_to="/calendar")
        self.assertIn("30 July 2026", header)
        self.assertIn("Week 31", header)
        projection = calendar_projection(
            [], list_calendars(self.connection), view="month",
            anchor_date=date(2026, 7, 1), selected_calendar_ids={1, 2},
            preview_event=None,
        )
        self.assertIn('class="calendar-week-heading" aria-label="Weeks">Wk', projection)
        self.assertIn('class="calendar-month-week-number" aria-label="Week 27">27', projection)
        self.assertNotIn('class="calendar-header-week"', projection)
        four_week_month = calendar_projection(
            [], list_calendars(self.connection), view="month",
            anchor_date=date(2021, 2, 1), selected_calendar_ids={1, 2},
            preview_event=None,
        )
        six_week_month = calendar_projection(
            [], list_calendars(self.connection), view="month",
            anchor_date=date(2026, 8, 1), selected_calendar_ids={1, 2},
            preview_event=None,
        )
        self.assertEqual(4, four_week_month.count("calendar-month-week-number"))
        self.assertEqual(6, six_week_month.count("calendar-month-week-number"))
        year_boundary = calendar_header(
            view="day", anchor_date=date(2021, 1, 1),
            selected_calendar_ids={1}, return_to="/calendar",
        )
        self.assertIn("Week 53", year_boundary)

    def test_export_page_defaults_only_active_local_sources_to_checked(self) -> None:
        archived_id = create_calendar(
            self.connection, CalendarInput("Archived Fiction")
        )
        archive_calendar(self.connection, archived_id)
        subscription_id = create_subscription(
            self.connection, self.subscription_fetch(FICTIONAL_ICS)
        )
        page = calendar_settings_export_page(
            list_calendars(self.connection, include_archived=True),
            list_subscriptions(self.connection),
        )
        self.assertRegex(page, r'value="local:1" checked')
        self.assertRegex(page, rf'value="local:{archived_id}"(?! checked)')
        self.assertRegex(page, rf'value="external:{subscription_id}"(?! checked)')
        self.assertIn("data-calendar-export-select", page)
        self.assertIn("data-calendar-export-clear", page)
        with zipfile.ZipFile(io.BytesIO(create_calendar_export(
            self.connection, [f"local:{archived_id}"]
        ))) as archive:
            self.assertEqual(1, len(archive.namelist()))

    def subscription_fetch(
        self,
        content: bytes,
        *,
        url: str = "https://example.com/calendar.ics",
    ) -> SubscriptionFetch:
        return SubscriptionFetch(
            url,
            url,
            content,
            "text/calendar",
            '"fictional-etag"',
            "Thu, 30 Jul 2026 00:00:00 GMT",
            parse_icalendar(content),
        )


class CalendarInterchangeRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "route.sqlite3"
        self.staging_path = Path(self.directory.name) / "staging"
        initialise_database(self.database_path)
        EddyRequestHandler.database_path = self.database_path
        EddyRequestHandler.import_staging_dir = self.staging_path
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.client = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )

    def tearDown(self) -> None:
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def test_upload_preview_confirm_and_zip_download(self) -> None:
        boundary = "----ProjectEFictionalBoundary"
        body = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"return_to\"\r\n\r\n/calendar\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"upload\"; filename=\"fictional.ics\"\r\nContent-Type: text/calendar\r\n\r\n"
        ).encode() + FICTIONAL_ICS + f"\r\n--{boundary}--\r\n".encode()
        self.client.request(
            "POST",
            "/calendar/settings/import",
            body,
            {"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        response = self.client.getresponse()
        page = response.read().decode()
        self.assertEqual(200, response.status)
        self.assertIn("Import preview", page)
        self.assertIn("No canonical Event or Calendar has been created yet.", page)
        token = re.search(r'name="token" value="([0-9a-f]{32})"', page).group(1)
        with connect(self.database_path) as connection:
            self.assertEqual(0, len(list_events(connection)))

        confirm = urlencode({
            "token": token,
            "destination_mode": "existing",
            "calendar_id": "1",
            "return_to": "/calendar",
        })
        self.client.request(
            "POST",
            "/calendar/settings/import/confirm",
            confirm,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        imported = self.client.getresponse()
        self.assertEqual(303, imported.status)
        with connect(self.database_path) as connection:
            self.assertEqual(["Fictional Day"], [event.title for event in list_events(connection)])

        export = urlencode({"sources": "local:1", "return_to": "/calendar"})
        self.client.request(
            "POST",
            "/calendar/settings/export",
            export,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        downloaded = self.client.getresponse()
        content = downloaded.read()
        self.assertEqual(200, downloaded.status)
        self.assertEqual("application/zip", downloaded.getheader("Content-Type"))
        self.assertIn("project-e-calendars.zip", downloaded.getheader("Content-Disposition"))
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(1, len(archive.namelist()))
            self.assertEqual("fictional-one@example.test", parse_icalendar(archive.read(archive.namelist()[0])).events[0].uid)

    def test_url_calendars_live_under_settings_for_other_calendars(self) -> None:
        with connect(self.database_path) as connection:
            subscription_id = create_subscription(
                connection,
                SubscriptionFetch(
                    "https://example.com/calendar.ics",
                    "https://example.com/calendar.ics",
                    FICTIONAL_ICS,
                    "text/calendar",
                    '"fictional-etag"',
                    "",
                    parse_icalendar(FICTIONAL_ICS),
                ),
            )

        self.client.request("GET", "/calendar/settings/from-url")
        response = self.client.getresponse()
        page = response.read().decode()
        self.assertEqual(200, response.status)
        self.assertIn("Settings for my calendars", page)
        self.assertIn("Settings for other calendars", page)
        self.assertIn("Fictional Observances", page)
        self.assertNotIn("<h2>Subscriptions</h2>", page)

        self.client.request(
            "GET", f"/calendar/settings/other-calendars/{subscription_id}"
        )
        response = self.client.getresponse()
        detail = response.read().decode()
        self.assertEqual(200, response.status)
        self.assertIn("Settings for other calendars", detail)
        self.assertIn("externally owned and remains read-only", detail)
        self.assertIn('name="name"', detail)
        self.assertIn('name="colour"', detail)
        self.assertIn('name="timezone"', detail)
        self.assertIn("Event notifications", detail)
        self.assertNotIn('name="default_event_duration_minutes"', detail)
        self.assertIn("Refresh now", detail)
        self.assertIn("Remove calendar", detail)

        body = urlencode({
            "return_to": "/calendar",
            "name": "Renamed observances",
            "colour": "#345678",
            "timezone": "Europe/London",
            "calendar_reminder_amount_0": "2",
            "calendar_reminder_unit_0": "d",
            "default_event_duration_minutes": "5",
        })
        self.client.request(
            "POST",
            f"/calendar/settings/other-calendars/{subscription_id}",
            body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = self.client.getresponse()
        response.read()
        self.assertEqual(303, response.status)
        with connect(self.database_path) as connection:
            source = get_subscription(connection, subscription_id)
            self.assertEqual("Renamed observances", source.name)
            self.assertEqual("#345678", source.colour)
            self.assertEqual("Europe/London", source.timezone)
            self.assertEqual(
                ["2d"],
                get_policy(
                    connection,
                    "calendar_subscription",
                    subscription_id,
                    "event",
                ),
            )

        body = urlencode({"return_to": "/calendar"})
        self.client.request(
            "POST",
            f"/calendar/settings/other-calendars/{subscription_id}/disable",
            body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = self.client.getresponse()
        self.assertEqual(303, response.status)
        self.assertIn(
            f"/calendar/settings/other-calendars/{subscription_id}",
            response.getheader("Location"),
        )
        with connect(self.database_path) as connection:
            self.assertFalse(get_subscription(connection, subscription_id).enabled)

        self.client.request(
            "POST",
            f"/calendar/settings/other-calendars/{subscription_id}/remove",
            body,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = self.client.getresponse()
        response.read()
        self.assertEqual(303, response.status)
        self.assertIn(
            "/calendar/settings/from-url",
            response.getheader("Location"),
        )
        with connect(self.database_path) as connection:
            self.assertIsNone(get_subscription(connection, subscription_id))
            self.assertIsNone(get_policy(
                connection,
                "calendar_subscription",
                subscription_id,
                "event",
            ))


if __name__ == "__main__":
    unittest.main()
