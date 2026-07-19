"""Calendar-originated Event creation and editing forms."""

from calendar import monthrange
from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from app.calendar_service import CalendarRecord
from app.event_service import EventRecord
from app.event_recurrence import RecurrenceDefinition, occurrences_between
from app.view_pages.forms import error_block


def calendar_page(
    calendars: list[CalendarRecord],
    events: list[EventRecord],
    created_event: EventRecord | None = None,
    projection: str = "",
) -> str:
    """Render Calendar projections only; Event mutation has dedicated routes."""
    created_notice = ""
    if created_event is not None:
        created_notice = f"""
        <section class="notice success" role="status"><strong>Event created.</strong>
        <a href="/relationships/new?context_entity_id={created_event.id}">Add relationships</a>
        or <a href="/events/{created_event.id}">open the Event record</a>.</section>
        """
    return f'<div class="calendar-page"><div class="actions"><a class="button" href="/calendar/events/new">Add Event</a><a class="button secondary" href="/calendar/tasks/new">Add Task</a></div>{projection}{created_notice}</div>'


def event_form_page(calendars, values, *, editing_event=None, recurrence=None, occurrence_date="", errors=None) -> str:
    errors = errors or []
    editing = editing_event is not None
    action = f"/calendar/events/{editing_event.id}/edit" if editing else "/calendar/events/new"
    relationship_link = f'<p class="help-text"><a href="/relationships/new?context_entity_id={editing_event.id}">add a relationship</a></p>' if editing else ""
    scope_fields = _recurrence_scope_fields(occurrence_date) if occurrence_date else ""
    return f'''<section class="page-heading"><p class="eyebrow">Calendar</p><h1>{"Edit" if editing else "Add"} Event</h1></section><section class="panel calendar-event-editor">{error_block(errors)}<form class="record-form" method="post" action="{action}" data-dirty-form data-event-form>{scope_fields}<div class="calendar-form-grid"><label for="title"><span>Title</span><input id="title" name="title" required value="{escape(values.get("title", ""))}"></label><label for="calendar_id"><span>Calendar</span><select id="calendar_id" name="calendar_id">{_calendar_options(calendars, values.get("calendar_id", ""))}</select></label><label class="inline-check" for="all_day"><input id="all_day" name="all_day" type="checkbox" value="1" data-event-all-day{" checked" if values.get("all_day") == "1" else ""}> All day</label><div data-all-day-fields><label for="start_date"><span>Start date</span><input id="start_date" name="start_date" type="date" value="{escape(values.get("start_date", ""))}"></label><label for="end_date"><span>End date</span><input id="end_date" name="end_date" type="date" value="{escape(values.get("end_date", ""))}"></label></div><div data-timed-fields><label for="start_local"><span>Starts</span><input id="start_local" name="start_local" type="datetime-local" value="{escape(values.get("start_local", ""))}"></label><label for="end_local"><span>Ends</span><input id="end_local" name="end_local" type="datetime-local" value="{escape(values.get("end_local", ""))}"></label><label for="timezone"><span>Timezone</span><input id="timezone" name="timezone" value="{escape(values.get("timezone", ""))}" placeholder="Australia/Brisbane"></label></div><label for="notes"><span>Notes <em>(optional)</em></span><textarea id="notes" name="notes" rows="3">{escape(values.get("notes", ""))}</textarea></label>{_recurrence_fields(recurrence) if editing else ""}</div><div class="actions"><a class="button secondary" href="/calendar">Cancel</a><button class="button" type="submit">{"Save changes" if editing else "Add Event"}</button></div></form>{relationship_link}</section>'''


def calendar_projection(
    events: list[EventRecord], calendars: list[CalendarRecord], *, view: str,
    anchor_date: date, selected_calendar_ids: set[int], preview_event: EventRecord | None, preview_occurrence: str = "",
    recurrences: dict[int, RecurrenceDefinition] | None = None,
    recurrence_exceptions: dict[int, object] | None = None,
) -> str:
    """Build Month, Week or Day read projections from canonical Event intervals."""
    active_calendars = [calendar for calendar in calendars if not calendar.is_archived]
    selected = selected_calendar_ids or {calendar.id for calendar in active_calendars}
    visible_events = [event for event in events if event.calendar_id in selected]
    calendar_by_id = {calendar.id: calendar for calendar in calendars}
    display_timezone = next(calendar.timezone for calendar in active_calendars if calendar.is_default)
    parameters = [("view", view), ("date", anchor_date.isoformat())]
    parameters.extend(("calendars", str(calendar_id)) for calendar_id in sorted(selected))
    if view == "week":
        period_start = anchor_date - timedelta(days=anchor_date.weekday())
        period_end = period_start + timedelta(days=6)
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _week_grid(visible_events, calendar_by_id, period_start, display_timezone, urlencode(parameters))
        previous = period_start - timedelta(days=7)
        following = period_start + timedelta(days=7)
        title = f"Week of {period_start.strftime('%-d %B %Y')}"
    elif view == "day":
        period_start = period_end = anchor_date
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _time_grid(visible_events, calendar_by_id, [period_start], display_timezone, urlencode(parameters))
        previous = period_start - timedelta(days=1)
        following = period_start + timedelta(days=1)
        title = period_start.strftime("%A, %-d %B %Y")
    else:
        period_start = anchor_date.replace(day=1)
        period_end = period_start.replace(day=monthrange(period_start.year, period_start.month)[1])
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _month_grid(visible_events, calendar_by_id, period_start, display_timezone, urlencode(parameters))
        previous = (period_start - timedelta(days=1)).replace(day=1)
        following = (period_end + timedelta(days=1)).replace(day=1)
        title = period_start.strftime("%B %Y")
    previous_url = _calendar_url([( "view", view), ("date", previous.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    following_url = _calendar_url([( "view", view), ("date", following.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    today_url = _calendar_url([( "view", view), ("date", date.today().isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    month_url = _calendar_url([("view", "month"), ("date", anchor_date.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    week_url = _calendar_url([("view", "week"), ("date", anchor_date.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    day_url = _calendar_url([("view", "day"), ("date", anchor_date.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    filters = "".join(
        f'<label class="calendar-filter"><input type="checkbox" name="calendars" value="{calendar.id}"{" checked" if calendar.id in selected else ""}> <span style="background:{escape(calendar.colour)}"></span>{escape(calendar.name)}</label>'
        for calendar in active_calendars
    )
    preview = _preview_panel(preview_event, calendar_by_id.get(preview_event.calendar_id) if preview_event else None, preview_occurrence, recurrences.get(preview_event.id) if preview_event else None) if preview_event and preview_event.calendar_id in selected else ""
    return f"""
    <section class="panel calendar-projection"><div class="calendar-toolbar"><div class="actions"><a class="button secondary" href="{previous_url}" aria-label="Previous {view}">Previous</a><a class="button secondary" href="{today_url}">Today</a><a class="button secondary" href="{following_url}" aria-label="Next {view}">Next</a></div><h2>{escape(title)}</h2><div class="calendar-view-switch" aria-label="Calendar view"><a class="button secondary" href="/calendar/manage">Calendars</a><a class="button{' secondary' if view != 'month' else ''}" href="{month_url}">Month</a><a class="button{' secondary' if view != 'week' else ''}" href="{week_url}">Week</a><a class="button{' secondary' if view != 'day' else ''}" href="{day_url}">Day</a><a class="button" href="/calendar/events/new" aria-label="Add Event">+</a></div></div>
        <form class="calendar-filters" method="get" action="/calendar"><input type="hidden" name="view" value="{escape(view)}"><input type="hidden" name="date" value="{anchor_date.isoformat()}"><fieldset><legend>Visible Calendars</legend>{filters}</fieldset><button class="button secondary" type="submit">Apply</button></form>
        {preview}
        {grid}
    </section>
    """


def _month_grid(events: list[EventRecord], calendars: dict[int, CalendarRecord], month: date, display_timezone: str, context_query: str) -> str:
    first = month - timedelta(days=month.weekday())
    final = month.replace(day=monthrange(month.year, month.month)[1])
    last = final + timedelta(days=6 - final.weekday())
    days = [first + timedelta(days=index) for index in range((last - first).days + 1)]
    cells = "".join(_day_cell(day, events, calendars, display_timezone, day.month == month.month, context_query=context_query) for day in days)
    return f'<div class="calendar-weekdays">{"".join(f"<span>{name}</span>" for name in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"))}</div><div class="calendar-month-grid">{cells}</div>'


def _expand_events(events: list[EventRecord], recurrences: dict[int, RecurrenceDefinition], exceptions: dict[int, object], start: date, end: date) -> list[EventRecord]:
    return [occurrence.event for event in events for occurrence in occurrences_between(event, recurrences.get(event.id), start, end, exceptions.get(event.id))]


def _week_grid(events: list[EventRecord], calendars: dict[int, CalendarRecord], monday: date, display_timezone: str, context_query: str) -> str:
    days = [monday + timedelta(days=index) for index in range(7)]
    return _time_grid(events, calendars, days, display_timezone, context_query)


def _time_grid(events: list[EventRecord], calendars: dict[int, CalendarRecord], days: list[date], display_timezone: str, context_query: str) -> str:
    """Render timed intervals on an hourly grid, clipping each to its visible day."""
    headers = "".join(
        f'<header class="calendar-time-day-header"><span>{day.strftime("%a")}</span><time datetime="{day.isoformat()}">{day.day}</time></header>'
        for day in days
    )
    all_day_cells = "".join(
        f'<div class="calendar-time-all-day-cell">{"".join(_projection_event(event, calendars[event.calendar_id], day, display_timezone, context_query) for event in events if event.is_all_day and _event_occurs_on(event, day, display_timezone))}</div>'
        for day in days
    )
    hour_labels = "".join(f'<time style="top:{hour * 48}px">{hour:02d}:00</time>' for hour in range(24))
    timed_cells = "".join(
        f'<div class="calendar-time-day" aria-label="{day.isoformat()}">{"".join(_timed_projection_event(event, calendars[event.calendar_id], day, display_timezone, context_query) for event in events if not event.is_all_day and _event_occurs_on(event, day, display_timezone))}</div>'
        for day in days
    )
    return f'<div class="calendar-time-grid-scroll"><div class="calendar-time-grid" style="--calendar-day-count:{len(days)}"><div class="calendar-time-axis-heading"></div>{headers}<div class="calendar-time-all-day-label">All day</div>{all_day_cells}<div class="calendar-time-axis">{hour_labels}</div>{timed_cells}</div></div>'


def _day_cell(day: date, events: list[EventRecord], calendars: dict[int, CalendarRecord], display_timezone: str, in_current_month: bool, include_weekday: bool = False, context_query: str = "") -> str:
    event_items = "".join(_projection_event(event, calendars[event.calendar_id], day, display_timezone, context_query) for event in events if _event_occurs_on(event, day, display_timezone))
    weekday = f'<span class="calendar-day-name">{day.strftime("%A")}</span>' if include_weekday else ""
    return f'<section class="calendar-day{" outside-month" if not in_current_month else ""}"><header>{weekday}<time datetime="{day.isoformat()}">{day.day}</time></header>{event_items}</section>'


def _projection_event(event: EventRecord, calendar: CalendarRecord, day: date, display_timezone: str, context_query: str) -> str:
    label = _projection_label(event, day, display_timezone)
    query = f"{context_query}&preview={event.id}&occurrence={_occurrence_date(event)}"
    state = " cancelled" if event.is_cancelled else ""
    return f'<a class="calendar-event{state}" style="--calendar-colour:{escape(calendar.colour)}" href="{_calendar_url_with_query(query)}"><span>{escape(label)}</span>{escape(event.title)}</a>'


def _timed_projection_event(event: EventRecord, calendar: CalendarRecord, day: date, display_timezone: str, context_query: str) -> str:
    zone = ZoneInfo(display_timezone)
    start = datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    end = datetime.fromisoformat(event.end_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    day_end = day_start + timedelta(days=1)
    segment_start, segment_end = max(start, day_start), min(end, day_end)
    start_minutes = segment_start.hour * 60 + segment_start.minute
    duration_minutes = max(1, int((segment_end - segment_start).total_seconds() / 60))
    query = f"{context_query}&preview={event.id}&occurrence={_occurrence_date(event)}"
    state = " cancelled" if event.is_cancelled else ""
    label = f"{segment_start.strftime('%H:%M')}–{segment_end.strftime('%H:%M')}"
    return f'<a class="calendar-timed-event{state}" style="--calendar-colour:{escape(calendar.colour)};top:{start_minutes * .8:.1f}px;height:{max(duration_minutes * .8, 24):.1f}px" href="{_calendar_url_with_query(query)}"><span>{label}</span>{escape(event.title)}</a>'


def _event_occurs_on(event: EventRecord, day: date, display_timezone: str) -> bool:
    if event.is_all_day:
        return event.start_date <= day.isoformat() < event.end_date_exclusive
    start, end = _timed_dates(event, display_timezone)
    return start <= day <= end


def _projection_label(event: EventRecord, day: date, display_timezone: str) -> str:
    if event.is_all_day:
        return "All day · " if event.start_date == day.isoformat() else "Continues · "
    start = datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(ZoneInfo(display_timezone))
    return f"{start.strftime('%H:%M')} · " if start.date() == day else "Continues · "


def _timed_dates(event: EventRecord, display_timezone: str) -> tuple[date, date]:
    zone = ZoneInfo(display_timezone)
    start = datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    end = datetime.fromisoformat(event.end_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    return start.date(), (end - timedelta(microseconds=1)).date()


def _preview_panel(event: EventRecord, calendar: CalendarRecord | None, occurrence_date: str = "", recurrence: RecurrenceDefinition | None = None) -> str:
    calendar_name = calendar.name if calendar else "Unavailable Calendar"
    colour = calendar.colour if calendar else "#6B7280"
    occurrence_query = f"?occurrence={escape(occurrence_date)}" if occurrence_date and recurrence else ""
    scope = _recurrence_scope_fields(occurrence_date, compact=True) if occurrence_date and recurrence else ""
    return f'<aside class="calendar-preview"><div><p class="eyebrow">Event preview</p><h3>{escape(event.title)}</h3><p>{escape(_event_schedule(event))}</p><p><span class="calendar-colour" style="background:{escape(colour)}"></span>{escape(calendar_name)}</p></div><div class="actions"><a class="button secondary" href="/calendar/events/{event.id}/edit{occurrence_query}">Edit</a><form method="post" action="/calendar/events/{event.id}/delete" data-confirm-object="{escape(event.title)}" data-confirm-consequence="Apply the selected deletion scope. The all-occurrences action moves this Event to the Recycle Bin.">{scope}<button class="button danger" type="submit">Delete</button></form></div></aside>'


def _occurrence_date(event: EventRecord) -> str:
    if event.is_all_day:
        return event.start_date
    return datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(ZoneInfo(event.timezone)).date().isoformat()


def _recurrence_scope_fields(occurrence_date: str, compact: bool = False) -> str:
    hidden = f'<input type="hidden" name="occurrence_date" value="{escape(occurrence_date)}">'
    label = "Apply to" if compact else "Apply changes to"
    help_text = "This occurrence keeps the series rule; following creates a linked successor series." if not compact else ""
    return f'{hidden}<label class="recurrence-scope"><span>{label}</span><select name="recurrence_scope"><option value="this">This occurrence</option><option value="following">This and following</option><option value="all">All occurrences</option></select></label><small class="field-help">{help_text}</small>'


def calendar_management_page(calendars: list[CalendarRecord], errors: list[str] | None = None) -> str:
    errors = errors or []
    rows = "".join(_calendar_management_row(calendar) for calendar in calendars)
    return f'''<section class="page-heading split"><div><p class="eyebrow">Calendar</p><h1>Manage Calendars</h1><p>Calendars set Event colour, display timezone and default duration.</p></div><a class="button secondary" href="/calendar">Back to Calendar</a></section><section class="panel">{error_block(errors)}<div class="calendar-management-list">{rows}</div></section><section class="panel"><h2>Add Calendar</h2><form class="record-form calendar-management-form" method="post" action="/calendar/manage"><label><span>Name</span><input name="name" required></label><label><span>Colour</span><input name="colour" type="color" value="#2563EB"></label><label><span>Timezone</span><input name="timezone" value="Australia/Brisbane" required></label><label><span>Default duration (minutes)</span><input name="default_event_duration_minutes" type="number" min="1" value="60" required></label><label><span>Order</span><input name="sort_order" type="number" value="0" required></label><div class="actions"><button class="button" type="submit">Add Calendar</button></div></form></section>'''


def calendar_management_edit_page(calendar: CalendarRecord, errors: list[str] | None = None) -> str:
    errors = errors or []
    return f'''<section class="page-heading split"><div><p class="eyebrow">Calendar</p><h1>Edit {escape(calendar.name)}</h1></div><a class="button secondary" href="/calendar/manage">Back to Calendars</a></section><section class="panel">{error_block(errors)}<form class="record-form calendar-management-form" method="post" action="/calendar/manage/{calendar.id}/edit"><label><span>Name</span><input name="name" required value="{escape(calendar.name)}"></label><label><span>Colour</span><input name="colour" type="color" value="{escape(calendar.colour)}"></label><label><span>Timezone</span><input name="timezone" value="{escape(calendar.timezone)}" required></label><label><span>Default duration (minutes)</span><input name="default_event_duration_minutes" type="number" min="1" value="{calendar.default_event_duration_minutes}" required></label><label><span>Order</span><input name="sort_order" type="number" value="{calendar.sort_order}" required></label><div class="actions"><a class="button secondary" href="/calendar/manage">Cancel</a><button class="button" type="submit">Save Calendar</button></div></form></section>'''


def _calendar_management_row(calendar: CalendarRecord) -> str:
    state = "Default" if calendar.is_default else "Archived" if calendar.is_archived else "Active"
    archive_action = "unarchive" if calendar.is_archived else "archive"
    archive_label = "Unarchive" if calendar.is_archived else "Archive"
    default_action = "" if calendar.is_default or calendar.is_archived else f'<form method="post" action="/calendar/manage/{calendar.id}/default" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="Make this the default Calendar for new Events."><button class="button secondary" type="submit">Make default</button></form>'
    delete_action = "" if calendar.is_default else f'<form method="post" action="/calendar/manage/{calendar.id}/delete" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="Permanently delete this empty Calendar. Assigned Events prevent deletion."><button class="button danger" type="submit">Delete</button></form>'
    return f'<article class="calendar-management-row"><div><h2><span class="calendar-colour" style="background:{escape(calendar.colour)}"></span>{escape(calendar.name)}</h2><p>{escape(calendar.timezone)} · {calendar.default_event_duration_minutes} minutes · order {calendar.sort_order} · {state}</p></div><div class="actions"><a class="button secondary" href="/calendar/manage/{calendar.id}/edit">Edit</a>{default_action}<form method="post" action="/calendar/manage/{calendar.id}/{archive_action}" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="{archive_label} this Calendar. Existing Event assignments are retained."><button class="button secondary" type="submit">{archive_label}</button></form>{delete_action}</div></article>'


def _calendar_url(parameters: list[tuple[str, str]]) -> str:
    return "/calendar?" + urlencode(parameters)


def _calendar_url_with_query(query: str) -> str:
    return "/calendar?" + query


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


def _recurrence_fields(recurrence: RecurrenceDefinition | None) -> str:
    rule = recurrence.rule if recurrence else None
    frequency = rule.frequency if rule else ""
    interval = str(rule.interval) if rule else "1"
    until = rule.until_date if rule else ""
    selected_days = set(rule.weekdays) if rule else set()
    weekday_choices = "".join(f'<label><input type="checkbox" name="recurrence_weekdays" value="{day}"{" checked" if day in selected_days else ""}>{label}</label>' for day, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")))
    ordinal = str(rule.monthly_ordinal) if rule else "0"
    ordinal_options = "".join(f'<option value="{value}"{" selected" if value == ordinal else ""}>{label}</option>' for value, label in (("0", "Calendar day"), ("1", "First"), ("2", "Second"), ("3", "Third"), ("4", "Fourth"), ("5", "Fifth"), ("-1", "Last")))
    monthly_weekday = str(rule.monthly_weekday) if rule else "0"
    weekday_options = "".join(f'<option value="{day}"{" selected" if str(day) == monthly_weekday else ""}>{label}</option>' for day, label in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")))
    options = '<option value="">Does not repeat</option>' + ''.join(f'<option value="{item}"{" selected" if item == frequency else ""}>{item.title()}</option>' for item in ("daily", "weekly", "monthly", "yearly"))
    return f'<fieldset class="calendar-recurrence"><legend>Recurrence</legend><label for="recurrence_frequency"><span>Repeats</span><select id="recurrence_frequency" name="recurrence_frequency">{options}</select></label><label for="recurrence_interval"><span>Every</span><input id="recurrence_interval" name="recurrence_interval" type="number" min="1" value="{interval}"></label><label for="recurrence_until"><span>Ends</span><input id="recurrence_until" name="recurrence_until" type="date" value="{escape(until)}"></label><fieldset><legend>Weekly days</legend>{weekday_choices}</fieldset><label for="recurrence_ordinal"><span>Monthly pattern</span><select id="recurrence_ordinal" name="recurrence_ordinal">{ordinal_options}</select></label><label for="recurrence_monthly_weekday"><span>Ordinal weekday</span><select id="recurrence_monthly_weekday" name="recurrence_monthly_weekday">{weekday_options}</select></label><small class="field-help">Monthly and yearly repeats on the 29th–31st shift backward in shorter periods.</small></fieldset>'
