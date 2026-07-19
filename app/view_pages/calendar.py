"""Calendar-originated Event creation and editing forms."""

from datetime import date, datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from app.calendar_service import CalendarRecord
from app.event_service import EventRecord
from app.view_pages.forms import error_block


def calendar_page(
    calendars: list[CalendarRecord],
    events: list[EventRecord],
    values: dict[str, str],
    errors: list[str] | None = None,
    editing_event: EventRecord | None = None,
    created_event: EventRecord | None = None,
) -> str:
    """Render the first Calendar workflow before Week and Month projections."""
    errors = errors or []
    form_action = (
        f"/calendar/events/{editing_event.id}/edit" if editing_event else "/calendar/events"
    )
    heading = "Edit Event" if editing_event else "Add Event"
    submit = "Save changes" if editing_event else "Add Event"
    calendar_options = _calendar_options(calendars, values.get("calendar_id", ""))
    event_rows = "".join(_event_row(event) for event in events)
    created_notice = ""
    if created_event is not None:
        created_notice = f"""
        <section class="notice success" role="status"><strong>Event created.</strong>
        <a href="/relationships/new?context_entity_id={created_event.id}">Add relationships</a>
        or <a href="/events/{created_event.id}">open the Event record</a>.</section>
        """
    return f"""
    <section class="page-heading split"><div><p class="eyebrow">Operational time</p><h1>Calendar</h1>
    <p>Create and edit Events here. Week and Month projections follow in the next milestone.</p></div></section>
    {created_notice}
    <section class="panel calendar-event-editor"><h2>{heading}</h2>
        {error_block(errors)}
        <form class="record-form" method="post" action="{form_action}" data-dirty-form>
            <div class="calendar-form-grid">
                <label for="title"><span>Title</span><input id="title" name="title" required value="{escape(values.get('title', ''))}"></label>
                <label for="calendar_id"><span>Calendar</span><select id="calendar_id" name="calendar_id">{calendar_options}</select></label>
                <label class="inline-check" for="all_day"><input id="all_day" name="all_day" type="checkbox" value="1"{' checked' if values.get('all_day') == '1' else ''}> All day</label>
                <label for="start_date"><span>Start date</span><input id="start_date" name="start_date" type="date" required value="{escape(values.get('start_date', ''))}"></label>
                <label for="end_date"><span>End date</span><input id="end_date" name="end_date" type="date" required value="{escape(values.get('end_date', ''))}"></label>
                <label for="start_local"><span>Starts</span><input id="start_local" name="start_local" type="datetime-local" value="{escape(values.get('start_local', ''))}"></label>
                <label for="end_local"><span>Ends</span><input id="end_local" name="end_local" type="datetime-local" value="{escape(values.get('end_local', ''))}"></label>
                <label for="timezone"><span>Timezone</span><input id="timezone" name="timezone" value="{escape(values.get('timezone', ''))}" placeholder="Australia/Brisbane"><small class="field-help">Use an IANA timezone when the Event's local time matters.</small></label>
                <label for="notes"><span>Notes <em>(optional)</em></span><textarea id="notes" name="notes" rows="3">{escape(values.get('notes', ''))}</textarea></label>
            </div>
            <p class="help-text">All-day ranges include both selected dates. Timed Events require a start and end time.</p>
            <div class="actions"><a class="button secondary" href="/calendar">Cancel</a><button class="button" type="submit">{submit}</button></div>
        </form>
        {(_edit_actions(editing_event) if editing_event else '')}
    </section>
    <section class="panel"><div class="section-heading split"><div><h2>Current Events</h2><p class="muted">Archived Events are intentionally excluded.</p></div></div>
    <div class="calendar-event-list">{event_rows or '<p class="empty">No Events yet.</p>'}</div></section>
    """


def default_event_values(calendars: list[CalendarRecord]) -> dict[str, str]:
    default = next(calendar for calendar in calendars if calendar.is_default)
    today = date.today().isoformat()
    start = datetime.combine(date.today(), datetime.min.time()).replace(hour=9)
    end = start + timedelta(minutes=default.default_event_duration_minutes)
    return {
        "title": "", "calendar_id": str(default.id), "all_day": "",
        "start_date": today, "end_date": today,
        "start_local": start.strftime("%Y-%m-%dT%H:%M"),
        "end_local": end.strftime("%Y-%m-%dT%H:%M"),
        "timezone": default.timezone, "notes": "",
    }


def event_form_values(event: EventRecord, calendar: CalendarRecord) -> dict[str, str]:
    values = {
        "title": event.title, "calendar_id": str(event.calendar_id),
        "all_day": "1" if event.is_all_day else "",
        "start_date": event.start_date, "notes": event.notes,
        "timezone": event.timezone or calendar.timezone,
    }
    if event.is_all_day:
        values["end_date"] = (date.fromisoformat(event.end_date_exclusive) - timedelta(days=1)).isoformat()
        values["start_local"] = values["end_local"] = ""
    else:
        zone = ZoneInfo(event.timezone)
        values["start_local"] = _as_local(event.start_utc, zone).replace(" ", "T")
        values["end_local"] = _as_local(event.end_utc, zone).replace(" ", "T")
        values["end_date"] = values["start_date"] = values["start_local"][:10]
    return values


def _calendar_options(calendars: list[CalendarRecord], selected_id: str) -> str:
    return "".join(
        f'<option value="{calendar.id}"{" selected" if str(calendar.id) == selected_id else ""}{" disabled" if calendar.is_archived and str(calendar.id) != selected_id else ""}>{escape(calendar.name)}{" (archived)" if calendar.is_archived else ""}</option>'
        for calendar in calendars
    )


def _event_row(event: EventRecord) -> str:
    schedule = _event_schedule(event)
    status = "Cancelled" if event.is_cancelled else "Planned"
    return f'<article class="calendar-event-row"><div><strong>{escape(event.title)}</strong><p>{escape(schedule)} · {status}</p></div><div class="actions"><a class="button secondary" href="/calendar/events/{event.id}/edit">Edit</a><a class="button quiet" href="/events/{event.id}">Open</a></div></article>'


def _event_schedule(event: EventRecord) -> str:
    if event.is_all_day:
        end = date.fromisoformat(event.end_date_exclusive) - timedelta(days=1)
        return f"{event.start_date} to {end.isoformat()} · All day"
    zone = ZoneInfo(event.timezone)
    return f"{_as_local(event.start_utc, zone)} to {_as_local(event.end_utc, zone)} · {event.timezone}"


def _as_local(utc_value: str, zone: ZoneInfo) -> str:
    return datetime.fromisoformat(utc_value.removesuffix("Z") + "+00:00").astimezone(zone).strftime("%Y-%m-%d %H:%M")


def _edit_actions(event: EventRecord) -> str:
    return f'<p class="help-text">Relationships are managed through the shared workflow: <a href="/relationships/new?context_entity_id={event.id}">add a relationship</a>. <a href="/events/{event.id}">Open record</a>.</p>'
