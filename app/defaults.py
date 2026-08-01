"""Stable product defaults shared across schema, services, routes and views."""

PLATFORM_TIMEZONE = "Australia/Brisbane"
DEFAULT_CALENDAR_COLOUR = "#2563EB"
DEFAULT_EXTERNAL_CALENDAR_COLOUR = "#7C3AED"
DEFAULT_EVENT_DURATION_MINUTES = 60
BIRTHDAY_CALENDAR_COLOUR = "#DB2777"
BIRTHDAY_EVENT_DURATION_MINUTES = 24 * 60
MAX_EVENT_REMINDERS = 10

DEFAULT_REMINDER_TIMINGS: dict[str, tuple[str, ...]] = {
    "event": ("1h", "10m"),
    "birthday": ("1mo", "2w", "1w", "3d", "1d", "12h"),
    "document_expiry": ("1mo", "2w", "1w", "3d", "1d"),
}
