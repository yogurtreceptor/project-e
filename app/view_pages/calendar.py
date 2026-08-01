"""Calendar-originated Event creation and editing forms."""

from calendar import monthrange
from datetime import date, datetime, timedelta
from html import escape
from urllib.parse import parse_qsl, urlencode, urlparse
from zoneinfo import ZoneInfo

from app.calendar_service import CalendarRecord
from app.defaults import DEFAULT_CALENDAR_COLOUR, DEFAULT_EXTERNAL_CALENDAR_COLOUR
from app.calendar_subscription_service import SubscriptionFetch, SubscriptionRecord
from app.event_service import EventRecord
from app.event_recurrence import RecurrenceDefinition, occurrences_between
from app.icalendar_service import ImportPreview
from app.view_pages.forms import description_field, error_block
from app.view_pages.icons import icon
from app.view_pages.reminders import calendar_reminder_fields
from app.view_pages.timezones import timezone_picker


def calendar_page(
    calendars: list[CalendarRecord],
    events: list[EventRecord],
    return_to: str = "/calendar",
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
    return f'''<div class="calendar-page"><div data-quick-create-root>{_quick_create_dialogs(calendars)}</div>{projection}{created_notice}</div>'''


def calendar_sidebar(
    *,
    calendars: list[CalendarRecord],
    subscriptions: list[SubscriptionRecord] | None = None,
    anchor_date: date,
    mini_month_date: date,
    view: str,
    selected_calendar_ids: set[int],
    return_to: str,
) -> str:
    """Render Calendar-local controls in the reserved shell sidebar."""
    event_url = f'/calendar/events/new?{urlencode({"return_to": return_to})}'
    active_calendars = [calendar for calendar in calendars if not calendar.is_archived]
    subscriptions = subscriptions or []
    calendar_filters = "".join(
        f'<div class="calendar-sidebar-filter" draggable="true" data-calendar-order-item="{calendar.id}"><button class="calendar-drag-handle" type="button" aria-label="Reorder {escape(calendar.name)}" aria-pressed="false" title="Drag to reorder">⋮⋮</button><label><input type="checkbox" name="calendars" value="{calendar.id}"{" checked" if calendar.id in selected_calendar_ids else ""}> <span class="calendar-colour" style="background:{escape(calendar.colour)}"></span><span>{escape(calendar.name)}</span></label><a class="calendar-edit-control" href="{escape(_calendar_settings_url(f"/calendars/{calendar.id}", return_to))}" aria-label="Edit {escape(calendar.name)} calendar" title="Edit {escape(calendar.name)} calendar">⋮</a></div>'
        for calendar in active_calendars
    )
    my_calendars = f'''<section class="calendar-sidebar-calendars calendar-sidebar-group" aria-labelledby="my-calendars-title" data-calendar-group>
      <div class="calendar-sidebar-group-heading"><h2 id="my-calendars-title">My calendars</h2><div class="calendar-sidebar-group-actions"><button class="calendar-sidebar-group-toggle" type="button" aria-expanded="true" aria-controls="my-calendars-list" aria-label="Collapse My calendars" data-calendar-group-label="My calendars" data-calendar-group-toggle><span class="calendar-sidebar-group-chevron" aria-hidden="true">▾</span></button></div></div>
      <div class="calendar-sidebar-group-content" id="my-calendars-list" data-calendar-group-content data-calendar-visibility-controls data-calendar-order-list="local">{calendar_filters}<p class="visually-hidden" role="status" data-calendar-visibility-status></p><p class="visually-hidden" role="status" data-calendar-order-status></p></div>
    </section>'''
    external_filters = "".join(
        f'<div class="calendar-sidebar-filter" draggable="true" data-calendar-order-item="{subscription.id}"><button class="calendar-drag-handle" type="button" aria-label="Reorder {escape(subscription.name)}" aria-pressed="false" title="Drag to reorder">⋮⋮</button><label><input type="checkbox" name="calendars" value="{-subscription.id}"{" checked" if -subscription.id in selected_calendar_ids else ""}> <span class="calendar-colour" style="background:{escape(subscription.colour)}"></span><span>{escape(subscription.name)}</span></label></div>'
        for subscription in subscriptions if subscription.enabled
    ) or "<p>No URL calendars yet.</p>"
    other_calendars = f'''<section class="calendar-other-calendars calendar-sidebar-group" aria-labelledby="other-calendars-title" data-calendar-group>
      <div class="calendar-sidebar-group-heading"><h2 id="other-calendars-title">Other calendars</h2><div class="calendar-sidebar-group-actions"><a class="calendar-add-control" href="{escape(_calendar_settings_url("/add", return_to))}" aria-label="Create calendar" title="Create calendar">+</a><button class="calendar-sidebar-group-toggle" type="button" aria-expanded="true" aria-controls="other-calendars-list" aria-label="Collapse Other calendars" data-calendar-group-label="Other calendars" data-calendar-group-toggle><span class="calendar-sidebar-group-chevron" aria-hidden="true">▾</span></button></div></div>
      <div class="calendar-sidebar-group-content" id="other-calendars-list" data-calendar-group-content data-calendar-visibility-controls data-calendar-order-list="external">{external_filters}<p class="visually-hidden" role="status" data-calendar-visibility-status></p><p class="visually-hidden" role="status" data-calendar-order-status></p></div>
    </section>'''
    return f'''<div class="calendar-sidebar-content"><a class="button" href="{event_url}" data-quick-create="event">Create event</a>{_mini_month_day_picker(anchor_date, mini_month_date, view, selected_calendar_ids)}{my_calendars}{other_calendars}</div>'''


def calendar_header(*, view: str, anchor_date: date, selected_calendar_ids: set[int], return_to: str) -> str:
    """Render Calendar-only navigation in the shared Project E header."""
    period_start, _, previous, following, title = _calendar_period(view, anchor_date)
    selected = sorted(selected_calendar_ids)

    def navigation_url(target_view: str, target_date: date) -> str:
        return _calendar_url([
            ("view", target_view),
            ("date", target_date.isoformat()),
            *(("calendars", str(item)) for item in selected),
        ])

    today_url = navigation_url(view, date.today())
    previous_url = navigation_url(view, previous)
    following_url = navigation_url(view, following)
    view_options = "".join(
        f'<li><a href="{navigation_url(option, anchor_date)}"{" aria-current=\"page\"" if option == view else ""}>{label}</a></li>'
        for option, label in (("month", "Month"), ("week", "Week"), ("day", "Day"))
    )
    week_companion = (
        f'<span class="calendar-header-week">Week {(period_start if view == "week" else anchor_date).isocalendar().week}</span>'
        if view in {"week", "day"} else ""
    )
    return f'''<div class="calendar-header-controls" role="navigation" aria-label="Calendar navigation">
      <a class="calendar-header-today" href="{today_url}">Today</a>
      <nav class="calendar-header-step" aria-label="Move through {escape(view)} view"><a href="{previous_url}" aria-label="Previous {escape(view)}" title="Previous {escape(view)}">‹</a><a href="{following_url}" aria-label="Next {escape(view)}" title="Next {escape(view)}">›</a></nav>
      <div class="calendar-header-period"><h1 class="calendar-header-date">{escape(title)}</h1>{week_companion}</div>
    </div><div class="calendar-header-tools">
      <details class="action-menu calendar-view-menu"><summary class="calendar-header-view">{escape(view.title())}<span class="menu-chevron" aria-hidden="true">▾</span></summary><div class="menu-panel"><ul>{view_options}</ul></div></details>
      <a class="calendar-settings-control" href="{escape(_calendar_settings_url("", return_to))}" aria-label="Calendar settings" title="Calendar settings">{icon("settings")}</a>
    </div>'''


def _mini_month_day_picker(selected_date: date, displayed_date: date, view: str, selected_calendar_ids: set[int]) -> str:
    """Render a fixed six-week picker with independently navigable displayed month."""
    month = displayed_date.replace(day=1)
    first_visible_day = month - timedelta(days=month.weekday())
    previous_month = (month - timedelta(days=1)).replace(day=1)
    next_month = (month.replace(day=monthrange(month.year, month.month)[1]) + timedelta(days=1)).replace(day=1)
    focus_date = selected_date if first_visible_day <= selected_date < first_visible_day + timedelta(days=42) else month

    def picker_url(day: date, mini_date: date | None = None) -> str:
        parameters = [("view", view), ("date", day.isoformat()), *(("calendars", str(item)) for item in sorted(selected_calendar_ids))]
        if mini_date is not None:
            parameters.append(("mini_date", mini_date.isoformat()))
        return _calendar_url(parameters)

    weekday_labels = '<span aria-hidden="true"></span>' + "".join(
        f'<span aria-hidden="true">{label}</span>' for label in ("M", "T", "W", "T", "F", "S", "S")
    )
    weeks = []
    today = date.today()
    for week_offset in range(6):
        week_start = first_visible_day + timedelta(days=week_offset * 7)
        cells = [f'<span class="mini-month-week-number" aria-label="Week {week_start.isocalendar().week}">{week_start.isocalendar().week}</span>']
        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            classes = "mini-month-day"
            if day.month != month.month:
                classes += " outside-month"
            if day == today:
                classes += " is-today"
            if day == selected_date:
                classes += " is-selected"
            cells.append(
                f'<a class="{classes}" href="{picker_url(day)}" data-mini-picker-day '
                f'data-date="{day.isoformat()}" tabindex="{"0" if day == focus_date else "-1"}" '
                f'aria-label="{escape(day.strftime("%A, %-d %B %Y"))}"{" aria-current=\"date\"" if day == today else ""}>'
                f'<span>{day.day}</span></a>'
            )
        weeks.extend(cells)
    return f'''<section class="mini-month-picker" aria-label="Mini month day picker" data-mini-month-picker>
      <header class="mini-month-header"><h2>{escape(month.strftime("%B %Y"))}</h2><div class="mini-month-navigation"><a class="mini-month-nav" href="{picker_url(selected_date, previous_month)}" data-mini-month-previous aria-label="Previous month" title="Previous month">‹</a><a class="mini-month-nav" href="{picker_url(selected_date, next_month)}" data-mini-month-next aria-label="Next month" title="Next month">›</a></div></header>
      <div class="mini-month-weekdays">{weekday_labels}</div>
      <div class="mini-month-grid">{"".join(weeks)}</div>
    </section>'''


def _quick_create_dialogs(calendars: list[CalendarRecord]) -> str:
    event = default_event_values(calendars)
    return f'''<section class="calendar-quick-create" data-quick-create-dialog="event" aria-labelledby="quick-event-title" hidden><form method="post" action="/calendar/events/new" data-quick-event-form><input type="hidden" name="calendar_id" value="{escape(event["calendar_id"])}"><input type="hidden" name="timezone" value="{escape(event["timezone"])}"><input type="hidden" name="quick_create" value="1"><header class="quick-create-heading"><button class="button quiet" type="button" data-quick-create-dock>Dock</button><h2 id="quick-event-title" data-quick-create-drag>Add Event</h2><button class="button quiet icon-button" type="button" data-quick-create-close aria-label="Close Add Event" title="Close">×</button></header><label><span>Title</span><input name="title" required value=""></label><label class="inline-check"><input name="all_day" type="checkbox" value="1" data-event-all-day> All day</label><div data-all-day-fields hidden><label><span>Start date</span><input name="start_date" type="date" value="{escape(event["start_date"])}"></label><label><span>End date</span><input name="end_date" type="date" value="{escape(event["end_date"])}"></label></div><div data-timed-fields><label><span>Starts</span><input name="start_local" type="datetime-local" value="{escape(event["start_local"])}" required></label><label><span>Ends</span><input name="end_local" type="datetime-local" value="{escape(event["end_local"])}" required></label></div>{description_field()}<footer class="quick-create-actions"><button class="button secondary" type="button" data-quick-create-more data-quick-create-url="/calendar/events/new">More options</button><button class="button" type="submit">Add Event</button></footer></form></section>'''


def event_form_page(calendars, values, *, editing_event=None, recurrence=None, occurrence_date="", errors=None, return_to="/calendar") -> str:
    errors = errors or []
    editing = editing_event is not None
    action = f"/calendar/events/{editing_event.id}/edit" if editing else "/calendar/events/new"
    relationship_link = f'<p class="help-text"><a href="/relationships/new?context_entity_id={editing_event.id}">add a relationship</a></p>' if editing else ""
    scope_fields = f'<input type="hidden" name="return_to" value="{escape(return_to)}">' + (_recurrence_edit_scope_fields(occurrence_date) if occurrence_date else "")
    reminder_query = f'?occurrence={escape(occurrence_date)}' if occurrence_date else ""
    reminder_link = f'<a class="button secondary" href="/calendar/events/{editing_event.id}/reminders{reminder_query}">Reminder settings</a>' if editing else ""
    return f'''<section class="page-heading"><p class="eyebrow">Calendar</p><h1>{"Edit" if editing else "Add"} Event</h1></section><section class="panel calendar-event-editor">{error_block(errors)}<form class="record-form" method="post" action="{action}" data-dirty-form data-event-form>{scope_fields}<div class="calendar-form-grid"><label for="title"><span>Title</span><input id="title" name="title" required value="{escape(values.get("title", ""))}"></label><label for="calendar_id"><span>Calendar</span><select id="calendar_id" name="calendar_id">{_calendar_options(calendars, values.get("calendar_id", ""))}</select></label><label class="inline-check" for="all_day"><input id="all_day" name="all_day" type="checkbox" value="1" data-event-all-day{" checked" if values.get("all_day") == "1" else ""}> All day</label><div data-all-day-fields><label for="start_date"><span>Start date</span><input id="start_date" name="start_date" type="date" value="{escape(values.get("start_date", ""))}"></label><label for="end_date"><span>End date</span><input id="end_date" name="end_date" type="date" value="{escape(values.get("end_date", ""))}"></label></div><div data-timed-fields><label for="start_local"><span>Starts</span><input id="start_local" name="start_local" type="datetime-local" value="{escape(values.get("start_local", ""))}"></label><label for="end_local"><span>Ends</span><input id="end_local" name="end_local" type="datetime-local" value="{escape(values.get("end_local", ""))}"></label>{timezone_picker("timezone", values.get("timezone", ""))}</div>{description_field(values.get("notes", ""))}{_recurrence_fields(values, recurrence)}</div><div class="actions"><a class="button secondary" href="/calendar">Cancel</a>{reminder_link}<button class="button" type="submit">{"Save changes" if editing else "Add Event"}</button></div></form>{relationship_link}</section>'''


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
    display_timezone = next(calendar.timezone for calendar in active_calendars if calendar.is_default and calendar.kind == "event")
    parameters = [("view", view), ("date", anchor_date.isoformat())]
    parameters.extend(("calendars", str(calendar_id)) for calendar_id in sorted(selected))
    period_start, period_end, _, _, _ = _calendar_period(view, anchor_date)
    if view == "week":
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _week_grid(visible_events, calendar_by_id, period_start, display_timezone, urlencode(parameters))
    elif view == "day":
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _time_grid(visible_events, calendar_by_id, [period_start], display_timezone, urlencode(parameters))
    else:
        visible_events = _expand_events(visible_events, recurrences or {}, recurrence_exceptions or {}, period_start, period_end)
        grid = _month_grid(visible_events, calendar_by_id, period_start, display_timezone, urlencode(parameters))
    return_to = _calendar_url([("view", view), ("date", anchor_date.isoformat()), *(("calendars", str(item)) for item in sorted(selected))])
    preview = _preview_panel(preview_event, calendar_by_id.get(preview_event.calendar_id) if preview_event else None, preview_occurrence, recurrences.get(preview_event.id) if preview_event else None, return_to=return_to) if preview_event and preview_event.calendar_id in selected else ""
    return f"""
    <section class="panel calendar-projection calendar-projection-{escape(view)}">
        {preview}
        {grid}
    </section>
    """


def _calendar_period(view: str, anchor_date: date) -> tuple[date, date, date, date, str]:
    if view == "week":
        period_start = anchor_date - timedelta(days=anchor_date.weekday())
        period_end = period_start + timedelta(days=6)
        return (
            period_start,
            period_end,
            period_start - timedelta(days=7),
            period_start + timedelta(days=7),
            _week_heading(period_start, period_end),
        )
    if view == "day":
        return (
            anchor_date,
            anchor_date,
            anchor_date - timedelta(days=1),
            anchor_date + timedelta(days=1),
            anchor_date.strftime("%-d %B %Y"),
        )
    period_start = anchor_date.replace(day=1)
    period_end = period_start.replace(day=monthrange(period_start.year, period_start.month)[1])
    return (
        period_start,
        period_end,
        (period_start - timedelta(days=1)).replace(day=1),
        (period_end + timedelta(days=1)).replace(day=1),
        period_start.strftime("%B %Y"),
    )


def _week_heading(period_start: date, period_end: date) -> str:
    if (period_start.year, period_start.month) == (period_end.year, period_end.month):
        return period_start.strftime("%B %Y")
    if period_start.year == period_end.year:
        return f"{period_start.strftime('%b')} – {period_end.strftime('%b %Y')}"
    return f"{period_start.strftime('%b %Y')} – {period_end.strftime('%b %Y')}"


def _month_grid(events: list[EventRecord], calendars: dict[int, CalendarRecord], month: date, display_timezone: str, context_query: str) -> str:
    first = month - timedelta(days=month.weekday())
    final = month.replace(day=monthrange(month.year, month.month)[1])
    last = final + timedelta(days=6 - final.weekday())
    days = [first + timedelta(days=index) for index in range((last - first).days + 1)]
    context_pairs = [(key, value) for key, value in parse_qsl(context_query) if key == "calendars"]
    rows = []
    for week_start_index in range(0, len(days), 7):
        week_days = days[week_start_index:week_start_index + 7]
        week_start = week_days[0]
        rows.append(
            f'<span class="calendar-month-week-number" aria-label="Week {week_start.isocalendar().week}">{week_start.isocalendar().week}</span>'
        )
        rows.extend(
            _day_cell(
                day, events, calendars, display_timezone, day.month == month.month,
                context_query=context_query,
                more_url=_calendar_url([("view", "day"), ("date", day.isoformat()), *context_pairs]),
            )
            for day in week_days
        )
    cells = "".join(rows)
    week_count = len(days) // 7
    weekdays = '<span class="calendar-week-heading" aria-label="Weeks">Wk</span>' + "".join(
        f"<span>{name}</span>" for name in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    )
    return f'<div class="calendar-month-view"><div class="calendar-weekdays">{weekdays}</div><div class="calendar-month-grid" style="--calendar-week-count:{week_count}">{cells}</div></div>'


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
        f'<div class="calendar-time-day" aria-label="{day.isoformat()}" data-calendar-date="{day.isoformat()}">{"".join(_timed_projection_event(event, calendars[event.calendar_id], day, display_timezone, context_query) for event in events if not event.is_all_day and _event_occurs_on(event, day, display_timezone))}<span class="calendar-current-time" data-calendar-current-time hidden aria-hidden="true"><span class="calendar-current-time-dot"></span></span></div>'
        for day in days
    )
    return f'<div class="calendar-time-grid-scroll" data-calendar-time-grid-scroll data-calendar-timezone="{escape(display_timezone)}"><div class="calendar-time-grid" style="--calendar-day-count:{len(days)}"><div class="calendar-time-axis-heading"></div>{headers}<div class="calendar-time-all-day-label">All day</div>{all_day_cells}<div class="calendar-time-axis">{hour_labels}</div>{timed_cells}</div></div>'


def _day_cell(day: date, events: list[EventRecord], calendars: dict[int, CalendarRecord], display_timezone: str, in_current_month: bool, include_weekday: bool = False, context_query: str = "", more_url: str = "") -> str:
    day_events = [event for event in events if _event_occurs_on(event, day, display_timezone)]
    visible_events = day_events[:3]
    event_items = "".join(_projection_event(event, calendars[event.calendar_id], day, display_timezone, context_query) for event in visible_events)
    overflow = f'<a class="calendar-day-overflow" href="{escape(more_url)}">+ {len(day_events) - len(visible_events)} more</a>' if len(day_events) > len(visible_events) else ""
    weekday = f'<span class="calendar-day-name">{day.strftime("%A")}</span>' if include_weekday else ""
    return f'<section class="calendar-day{" outside-month" if not in_current_month else ""}"><header>{weekday}<time datetime="{day.isoformat()}">{day.day}</time></header><div class="calendar-day-events">{event_items}</div>{overflow}</section>'


def _projection_event(event: EventRecord, calendar: CalendarRecord, day: date, display_timezone: str, context_query: str) -> str:
    label = _projection_label(event, day, display_timezone)
    preview_key = "external_preview" if event.id < 0 else "preview"
    query = f"{context_query}&{preview_key}={event.id}&occurrence={_occurrence_date(event)}"
    state = " cancelled" if event.is_cancelled else ""
    return f'<a class="calendar-event{state}" data-calendar-id="{calendar.id}" style="--calendar-colour:{escape(calendar.colour)}" href="{_calendar_url_with_query(query)}"><span>{escape(label)}</span>{escape(event.title)}</a>'


def _timed_projection_event(event: EventRecord, calendar: CalendarRecord, day: date, display_timezone: str, context_query: str) -> str:
    zone = ZoneInfo(display_timezone)
    start = datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    end = datetime.fromisoformat(event.end_utc.removesuffix("Z") + "+00:00").astimezone(zone)
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    day_end = day_start + timedelta(days=1)
    segment_start, segment_end = max(start, day_start), min(end, day_end)
    start_minutes = segment_start.hour * 60 + segment_start.minute
    duration_minutes = max(1, int((segment_end - segment_start).total_seconds() / 60))
    preview_key = "external_preview" if event.id < 0 else "preview"
    query = f"{context_query}&{preview_key}={event.id}&occurrence={_occurrence_date(event)}"
    state = " cancelled" if event.is_cancelled else ""
    label = f"{segment_start.strftime('%H:%M')}–{segment_end.strftime('%H:%M')}"
    return f'<a class="calendar-timed-event{state}" data-calendar-id="{calendar.id}" style="--calendar-colour:{escape(calendar.colour)};top:{start_minutes * .8:.1f}px;height:{max(duration_minutes * .8, 24):.1f}px" href="{_calendar_url_with_query(query)}"><span>{label}</span>{escape(event.title)}</a>'


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


def _preview_panel(event: EventRecord, calendar: CalendarRecord | None, occurrence_date: str = "", recurrence: RecurrenceDefinition | None = None, *, return_to: str = "/calendar") -> str:
    calendar_name = calendar.name if calendar else "Unavailable Calendar"
    colour = calendar.colour if calendar else "#6B7280"
    if calendar is not None and calendar.kind == "external":
        return f'<aside class="calendar-preview"><div><p class="eyebrow">Read-only URL Calendar Event</p><h3>{escape(event.title)}</h3><p>{escape(_event_schedule(event))}</p><p><span class="calendar-colour" style="background:{escape(colour)}"></span>{escape(calendar_name)}</p>{f"<p>{escape(event.notes)}</p>" if event.notes else ""}</div><p class="help-text">This Event is supplied by an external Calendar and cannot be edited here.</p></aside>'
    occurrence_query = f"&occurrence={escape(occurrence_date)}" if occurrence_date and recurrence else ""
    recurring_occurrence = bool(occurrence_date and recurrence)
    scope = _recurrence_delete_scope_fields(occurrence_date) if recurring_occurrence else ""
    delete_confirmation = 'data-recurrence-delete-form' if recurring_occurrence else f'data-confirm-object="{escape(event.title)}" data-confirm-consequence="Move this Event to the Recycle Bin. It can be restored later."'
    context_query = urlencode({"return_to": return_to})
    return f'<aside class="calendar-preview"><div><p class="eyebrow">Event preview</p><h3>{escape(event.title)}</h3><p>{escape(_event_schedule(event))}</p><p><span class="calendar-colour" style="background:{escape(colour)}"></span>{escape(calendar_name)}</p></div><div class="actions"><a class="button secondary" href="/calendar/events/{event.id}/edit?{context_query}{occurrence_query}">Edit</a><form method="post" action="/calendar/events/{event.id}/delete" {delete_confirmation}><input type="hidden" name="return_to" value="{escape(return_to)}">{scope}<button class="button danger" type="submit">Delete</button></form></div></aside>'


def _occurrence_date(event: EventRecord) -> str:
    if event.is_all_day:
        return event.start_date
    return datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00").astimezone(ZoneInfo(event.timezone)).date().isoformat()


def _recurrence_scope_fields(occurrence_date: str, compact: bool = False) -> str:
    hidden = f'<input type="hidden" name="occurrence_date" value="{escape(occurrence_date)}">'
    label = "Apply to" if compact else "Apply changes to"
    help_text = "This occurrence keeps the series rule; following creates a linked successor series." if not compact else ""
    return f'{hidden}<label class="recurrence-scope"><span>{label}</span><select name="recurrence_scope"><option value="this">This occurrence</option><option value="following">This and following</option><option value="all">All occurrences</option></select></label><small class="field-help">{help_text}</small>'


def _recurrence_edit_scope_fields(occurrence_date: str) -> str:
    return f'''<input type="hidden" name="occurrence_date" value="{escape(occurrence_date)}"><input type="hidden" name="recurrence_scope" value="all" data-recurrence-scope-value><dialog class="confirmation-dialog recurrence-scope-dialog" data-recurrence-scope-dialog aria-labelledby="recurrence-edit-scope-title"><h2 id="recurrence-edit-scope-title">Edit recurring event</h2><div class="recurrence-scope-options" role="radiogroup" aria-label="Apply edits to"><button type="button" role="radio" value="this" aria-checked="false" data-recurrence-scope-choice>This event</button><button type="button" role="radio" value="following" aria-checked="false" data-recurrence-scope-choice>This and following</button><button type="button" role="radio" value="all" aria-checked="true" data-recurrence-scope-choice>All events</button></div><div class="actions recurrence-scope-actions"><button class="button secondary" type="button" data-recurrence-scope-cancel>Cancel</button><button class="button" type="button" data-recurrence-scope-confirm>OK</button></div></dialog>'''


def _recurrence_delete_scope_fields(occurrence_date: str) -> str:
    return f'''<input type="hidden" name="occurrence_date" value="{escape(occurrence_date)}"><input type="hidden" name="recurrence_scope" value="all" data-recurrence-delete-scope-value><dialog class="confirmation-dialog recurrence-scope-dialog" data-recurrence-delete-scope-dialog aria-labelledby="recurrence-delete-scope-title"><h2 id="recurrence-delete-scope-title">Delete recurring event</h2><div class="recurrence-scope-options" role="radiogroup" aria-label="Delete from"><button type="button" role="radio" value="this" aria-checked="false" data-recurrence-delete-scope-choice>This event</button><button type="button" role="radio" value="following" aria-checked="false" data-recurrence-delete-scope-choice>This and following</button><button type="button" role="radio" value="all" aria-checked="true" data-recurrence-delete-scope-choice>All events</button></div><div class="actions recurrence-scope-actions"><button class="button secondary" type="button" data-recurrence-delete-scope-cancel>Cancel</button><button class="button danger" type="button" data-recurrence-delete-scope-confirm>OK</button></div></dialog>'''


def calendar_settings_header(return_to: str) -> str:
    """Render the settings-only header with a context-preserving Calendar return."""
    return f'<a class="calendar-settings-back" href="{escape(return_to)}" aria-label="Back to Calendar"><span aria-hidden="true">‹</span> Settings</a>'


def calendar_settings_sidebar(
    calendars: list[CalendarRecord],
    subscriptions: list[SubscriptionRecord] | None = None,
    *,
    active_section: str,
    return_to: str,
) -> str:
    """Render navigation for the dedicated Calendar Settings shell."""

    def settings_link(path: str, label: str, section: str, *, coming_soon: bool = False) -> str:
        current = ' class="active" aria-current="page"' if active_section == section else ""
        coming_soon_title = ' title="Coming soon!"' if coming_soon else ""
        return f'<a{current} href="{escape(_calendar_settings_url(path, return_to))}"{coming_soon_title}>{escape(label)}</a>'

    add_sections = {"add", "discover", "from-url"}
    add_open = active_section in add_sections
    add_children = "".join((
        settings_link("/add", "Create New Calendar", "add"),
        settings_link("/discover", "Browse calendars of interest", "discover", coming_soon=True),
        settings_link("/from-url", "From URL", "from-url"),
    ))
    interchange_open = active_section in {"import", "export"}
    interchange_children = ""
    if interchange_open:
        interchange_children = f'''<div class="calendar-settings-subnav">
          {settings_link("/import", "Import", "import")}
          {settings_link("/export", "Export", "export")}
        </div>'''

    def calendar_link(calendar: CalendarRecord) -> str:
        selected = active_section == f"calendar:{calendar.id}"
        archived = '<small>Archived</small>' if calendar.is_archived else ""
        return f'<a class="calendar-settings-calendar{" is-archived" if calendar.is_archived else ""}{" active" if selected else ""}" href="{escape(_calendar_settings_url(f"/calendars/{calendar.id}", return_to))}"{" aria-current=\"page\"" if selected else ""}><span class="calendar-colour" style="background:{escape(calendar.colour)}"></span><span>{escape(calendar.name)}{archived}</span></a>'

    calendar_links = "".join(calendar_link(calendar) for calendar in calendars if not calendar.is_archived)
    archived_links = "".join(calendar_link(calendar) for calendar in calendars if calendar.is_archived)
    subscriptions = subscriptions or []

    def subscription_link(source: SubscriptionRecord) -> str:
        selected = active_section == f"subscription:{source.id}"
        disabled = "<small>Disabled</small>" if not source.enabled else ""
        return f'<a class="calendar-settings-calendar{" is-archived" if not source.enabled else ""}{" active" if selected else ""}" href="{escape(_calendar_settings_url(f"/other-calendars/{source.id}", return_to))}"{" aria-current=\"page\"" if selected else ""}><span class="calendar-colour" style="background:{escape(source.colour)}"></span><span>{escape(source.name)}{disabled}</span></a>'

    subscription_links = "".join(
        subscription_link(source) for source in subscriptions
    ) or "<p>No URL calendars.</p>"
    archived_section = f'''<div class="calendar-settings-archived">
        <h3>Archived calendars</h3>
        <div class="calendar-settings-calendar-list">{archived_links}</div>
      </div>''' if archived_links else ""
    return f'''<nav class="calendar-settings-nav" aria-label="Calendar settings navigation">
      {settings_link("", "General", "general", coming_soon=True)}
      <details class="calendar-settings-disclosure"{" open" if add_open else ""}>
        <summary><span class="calendar-settings-disclosure-chevron" aria-hidden="true">›</span><span>Add Calendar</span></summary>
        <div class="calendar-settings-subnav">{add_children}</div>
      </details>
      <section class="calendar-settings-interchange{" active" if interchange_open else ""}">
        <a class="calendar-settings-parent-link{" active" if interchange_open else ""}" href="{escape(_calendar_settings_url("/import", return_to))}" aria-expanded="{"true" if interchange_open else "false"}"><span class="calendar-settings-disclosure-chevron" aria-hidden="true">›</span><span>Import/Export</span></a>
        {interchange_children}
      </section>
    </nav>
    <section class="calendar-settings-calendars" aria-labelledby="calendar-settings-calendars-title">
      <h2 id="calendar-settings-calendars-title">Settings for my calendars</h2>
      <div class="calendar-settings-calendar-list">{calendar_links}</div>
      {archived_section}
    </section>
    <section class="calendar-settings-calendars calendar-settings-other-calendars" aria-labelledby="calendar-settings-other-calendars-title">
      <h2 id="calendar-settings-other-calendars-title">Settings for other calendars</h2>
      <div class="calendar-settings-calendar-list">{subscription_links}</div>
    </section>'''


def calendar_settings_general_page() -> str:
    return calendar_settings_placeholder_page(
        "General",
        "General Calendar preferences will live here once their behaviour is designed.",
    )


def calendar_settings_placeholder_page(title: str, description: str) -> str:
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Calendar settings</p><h1>{escape(title)}</h1></section>
    <section class="panel calendar-settings-placeholder"><span class="status-badge">Coming soon!</span><h2>{escape(title)}</h2><p>{escape(description)}</p></section>'''


def calendar_settings_import_page(
    calendars: list[CalendarRecord],
    *,
    preview: ImportPreview | None = None,
    token: str = "",
    errors: list[str] | None = None,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []
    upload = f'''<section class="panel calendar-interchange-panel">{error_block(errors)}<form class="record-form" method="post" action="/calendar/settings/import" enctype="multipart/form-data"><input type="hidden" name="return_to" value="{escape(return_to)}"><label><span>iCalendar file</span><input type="file" name="upload" accept=".ics,.ical,text/calendar" required></label><p class="help-text">Supported now: UTF-8 iCalendar 2.0 files containing losslessly representable all-day Events. VCS and CSV are not yet supported.</p><div class="actions"><button class="button" type="submit">Validate file</button></div></form></section>'''
    if preview is None:
        return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Import/Export</p><h1>Import</h1><p>Validate a file before choosing where its Events will be added.</p></section>{upload}'''
    document = preview.document
    start, end = document.date_span
    diagnostics = [
        *document.warnings,
        *document.blockers,
        *(message for item in preview.events for message in (*item.event.warnings, *item.event.blockers)),
    ]
    diagnostic_html = (
        '<section class="calendar-import-diagnostics"><h3>Compatibility diagnostics</h3><ul>'
        + "".join(f"<li>{escape(item)}</li>" for item in dict.fromkeys(diagnostics))
        + "</ul></section>"
    ) if diagnostics else '<p class="notice success">No blocking compatibility issues were found.</p>'
    rows = "".join(
        f'<tr><td>{escape(item.event.title or "(Untitled)")}</td><td>{escape(item.event.start_date)}</td><td>{"Recurring" if item.event.recurrence else "One Event"}</td><td>{escape(item.classification.title())}</td></tr>'
        for item in preview.events
    )
    active_event_calendars = [
        calendar for calendar in calendars
        if not calendar.is_archived and calendar.kind == "event"
    ]
    default = next((calendar for calendar in active_event_calendars if calendar.is_default), active_event_calendars[0])
    options = "".join(
        f'<option value="{calendar.id}"{" selected" if calendar.id == default.id else ""}>{escape(calendar.name)}</option>'
        for calendar in active_event_calendars
    )
    disabled = " disabled" if not preview.can_apply else ""
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Import/Export</p><h1>Import preview</h1><p>No canonical Event or Calendar has been created yet.</p></section>
    <section class="panel calendar-import-summary"><dl><div><dt>Source Calendar</dt><dd>{escape(document.name or "Not supplied")}</dd></div><div><dt>Timezone</dt><dd>{escape(document.timezone or "Not supplied")}</dd></div><div><dt>Events</dt><dd>{len(document.events)} ({document.recurring_count} recurring)</dd></div><div><dt>Date span</dt><dd>{escape(start or "Empty")}{" to " + escape(end) if end else ""}</dd></div></dl>{diagnostic_html}</section>
    <section class="panel"><div class="table-scroll"><table><thead><tr><th>Event</th><th>Starts</th><th>Pattern</th><th>Import state</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="panel"><form class="record-form" method="post" action="/calendar/settings/import/confirm" data-dirty-form><input type="hidden" name="return_to" value="{escape(return_to)}"><input type="hidden" name="token" value="{escape(token)}"><fieldset class="calendar-import-destination"><legend>Destination</legend><label><input type="radio" name="destination_mode" value="existing" checked> Add to an existing Calendar</label><label><span>Calendar</span><select name="calendar_id">{options}</select></label><label><input type="radio" name="destination_mode" value="new"> Create a new Calendar</label><div class="calendar-import-new-calendar"><label><span>Calendar name</span><input name="new_name" value="{escape(preview.proposed_name)}"></label><label><span>Colour</span><input class="calendar-colour-picker" name="new_colour" type="color" value="{DEFAULT_EXTERNAL_CALENDAR_COLOUR}"></label>{timezone_picker("new_timezone", preview.proposed_timezone)}</div></fieldset><div class="actions"><button class="button" type="submit"{disabled}>Import Events</button></div></form><form method="post" action="/calendar/settings/import/cancel"><input type="hidden" name="return_to" value="{escape(return_to)}"><input type="hidden" name="token" value="{escape(token)}"><button class="button secondary" type="submit">Cancel import</button></form></section>'''


def calendar_settings_export_page(
    calendars: list[CalendarRecord],
    subscriptions: list[SubscriptionRecord],
    *,
    errors: list[str] | None = None,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []

    def choice(value: str, name: str, colour: str, checked: bool) -> str:
        return f'<label class="calendar-export-choice"><input type="checkbox" name="sources" value="{escape(value)}"{" checked" if checked else ""}><span class="calendar-colour" style="background:{escape(colour)}"></span><span>{escape(name)}</span></label>'

    active = "".join(
        choice(f"local:{calendar.id}", calendar.name, calendar.colour, True)
        for calendar in calendars if not calendar.is_archived
    )
    archived = "".join(
        choice(f"local:{calendar.id}", calendar.name, calendar.colour, False)
        for calendar in calendars if calendar.is_archived
    ) or "<p>No archived Calendars.</p>"
    external = "".join(
        choice(f"external:{source.id}", source.name, source.colour, False)
        for source in subscriptions if source.enabled
    ) or "<p>No enabled URL subscriptions.</p>"
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Import/Export</p><h1>Export</h1><p>Download one ordinary iCalendar file per selected source in a ZIP archive.</p></section>
    <section class="panel calendar-interchange-panel">{error_block(errors)}<form class="record-form" method="post" action="/calendar/settings/export" data-calendar-export-form><input type="hidden" name="return_to" value="{escape(return_to)}"><div class="actions"><button class="button secondary" type="button" data-calendar-export-select> Select all</button><button class="button secondary" type="button" data-calendar-export-clear>Clear all</button></div><fieldset><legend>Active local Calendars</legend>{active}</fieldset><fieldset><legend>Archived local Calendars</legend>{archived}</fieldset><fieldset><legend>Read-only URL Calendars</legend>{external}</fieldset><p class="help-text">Timed Events and recurrence exceptions are reported before download rather than exported with data loss.</p><button class="button" type="submit">Download ZIP</button></form></section>'''


def calendar_settings_from_url_page(
    subscriptions: list[SubscriptionRecord],
    *,
    preview: SubscriptionFetch | None = None,
    token: str = "",
    errors: list[str] | None = None,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []
    add_form = f'''<section class="panel calendar-interchange-panel">{error_block(errors)}<form class="record-form" method="post" action="/calendar/settings/from-url"><input type="hidden" name="return_to" value="{escape(return_to)}"><label><span>Public iCalendar HTTPS URL</span><input name="url" type="url" placeholder="https://public-holidays.dteoh.com/all.ics" required></label><p class="help-text">The URL is validated and fetched once for preview. URL calendars stay read-only and retain a last-known-good local cache for offline Calendar use.</p><button class="button" type="submit">Preview Calendar</button></form></section>'''
    preview_html = ""
    if preview and preview.document:
        start, end = preview.document.date_span
        name = preview.document.name or "Subscribed Calendar"
        preview_html = f'''<section class="panel"><h2>Subscription preview</h2><dl><div><dt>Calendar</dt><dd>{escape(name)}</dd></div><div><dt>Final host</dt><dd>{escape(urlparse(preview.final_url).hostname or "")}</dd></div><div><dt>Content type</dt><dd>{escape(preview.content_type or "Not supplied")}</dd></div><div><dt>Events</dt><dd>{len(preview.document.events)}</dd></div><div><dt>Date span</dt><dd>{escape(start or "Empty")}{" to " + escape(end) if end else ""}</dd></div></dl><form class="record-form" method="post" action="/calendar/settings/from-url/confirm" data-dirty-form><input type="hidden" name="return_to" value="{escape(return_to)}"><input type="hidden" name="token" value="{escape(token)}"><label><span>Display name</span><input name="display_name" value="{escape(name)}" required></label><label><span>Colour</span><input class="calendar-colour-picker" name="colour" type="color" value="{DEFAULT_EXTERNAL_CALENDAR_COLOUR}"></label><button class="button" type="submit">Add subscription</button></form></section>'''
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Add Calendar</p><h1>From URL</h1><p>Add renewable, read-only public iCalendar sources under Other calendars.</p></section>{add_form}{preview_html}'''


def calendar_settings_subscription_page(
    source: SubscriptionRecord,
    configured_timings: list[str] | None,
    *,
    errors: list[str] | None = None,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Settings for other calendars</p><h1>{escape(source.name)}</h1><p>This URL calendar is externally owned and remains read-only in Project E.</p></section>
    <section class="panel calendar-settings-form-panel">{error_block(errors)}<form class="record-form calendar-settings-form" method="post" action="/calendar/settings/other-calendars/{source.id}" data-dirty-form><input type="hidden" name="return_to" value="{escape(return_to)}"><label><span>Name</span><input name="name" required value="{escape(source.name)}"></label><label><span>Colour</span><input class="calendar-colour-picker" name="colour" type="color" value="{escape(source.colour)}"></label>{timezone_picker("timezone", source.timezone)}{calendar_reminder_fields(configured_timings)}<p class="help-text">External Events remain read-only. Their schedule comes from the source, so this Calendar has no default Event duration.</p><div class="actions"><a class="button secondary" href="{escape(return_to)}">Cancel</a><button class="button" type="submit">Save Calendar</button></div></form></section>
    <section class="panel calendar-subscription-card"><div><p><span class="calendar-colour" style="background:{escape(source.colour)}"></span><strong>{escape(source.name)}</strong></p><dl><div><dt>Source host</dt><dd>{escape(source.host)}</dd></div><div><dt>Status</dt><dd>{"Enabled" if source.enabled else "Disabled"}</dd></div><div><dt>Last successful refresh</dt><dd>{escape(source.last_success_at or "Never")}</dd></div></dl>{f'<p class="warning-text">{escape(source.current_error)}</p>' if source.current_error else ""}</div>{_calendar_subscription_actions(source, return_to)}</section>'''


def _calendar_subscription_actions(
    source: SubscriptionRecord,
    return_to: str,
) -> str:
    hidden_return = f'<input type="hidden" name="return_to" value="{escape(return_to)}">'
    return f'''<div class="actions"><form method="post" action="/calendar/settings/other-calendars/{source.id}/refresh">{hidden_return}<button class="button secondary" type="submit">Refresh now</button></form><form method="post" action="/calendar/settings/other-calendars/{source.id}/{"disable" if source.enabled else "enable"}">{hidden_return}<button class="button secondary" type="submit">{"Disable" if source.enabled else "Enable"}</button></form><form method="post" action="/calendar/settings/other-calendars/{source.id}/remove" data-confirm-object="{escape(source.name)}" data-confirm-consequence="Remove this read-only URL calendar and its local cache.">{hidden_return}<button class="button danger" type="submit">Remove calendar</button></form></div>'''


def calendar_settings_create_page(
    errors: list[str] | None = None,
    *,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Add Calendar</p><h1>Create New Calendar</h1><p>Create a local Calendar for grouping Events and supplying their display defaults.</p></section>
    <section class="panel calendar-settings-form-panel">{error_block(errors)}<form class="record-form calendar-settings-form" method="post" action="/calendar/settings/add" data-dirty-form><input type="hidden" name="return_to" value="{escape(return_to)}"><label><span>Calendar name</span><input name="name" required></label><label><span>Colour</span><input class="calendar-colour-picker" name="colour" type="color" value="{DEFAULT_CALENDAR_COLOUR}"></label><div class="actions"><a class="button secondary" href="{escape(return_to)}">Cancel</a><button class="button" type="submit">Create Calendar</button></div></form></section>'''


def calendar_settings_edit_page(
    calendar: CalendarRecord,
    configured_timings: list[str] | None,
    errors: list[str] | None = None,
    *,
    return_to: str = "/calendar",
) -> str:
    errors = errors or []
    state = "Built-in Birthdays Calendar" if calendar.kind == "birthday" else "Default Calendar" if calendar.is_default else "Archived Calendar" if calendar.is_archived else "Active Calendar"
    status_controls = _calendar_settings_status_controls(calendar, return_to)
    status_panel = f'''<section class="panel calendar-settings-status"><div><p class="eyebrow">Calendar status</p><h2>{state}</h2><p>Calendar lifecycle changes retain existing Event assignments and use the established safeguards.</p></div><div class="actions">{status_controls}</div></section>''' if status_controls else f'''<section class="panel calendar-settings-status"><div><p class="eyebrow">Calendar status</p><h2>{state}</h2><p>This protected Calendar is managed from its source records.</p></div></section>'''
    return f'''<section class="page-heading calendar-settings-page-heading"><p class="eyebrow">Calendar settings</p><h1>{escape(calendar.name)}</h1></section>
    <section class="panel calendar-settings-form-panel">{error_block(errors)}<form class="record-form calendar-settings-form" method="post" action="/calendar/settings/calendars/{calendar.id}" data-dirty-form><input type="hidden" name="return_to" value="{escape(return_to)}"><label><span>Name</span><input name="name" required value="{escape(calendar.name)}"></label><label><span>Colour</span><input class="calendar-colour-picker" name="colour" type="color" value="{escape(calendar.colour)}"></label>{timezone_picker("timezone", calendar.timezone)}<label><span>Default duration (minutes)</span><input name="default_event_duration_minutes" type="number" min="1" value="{calendar.default_event_duration_minutes}" required></label>{calendar_reminder_fields(configured_timings, allow_months=calendar.kind == "birthday")}<div class="actions"><a class="button secondary" href="{escape(return_to)}">Cancel</a><button class="button" type="submit">Save Calendar</button></div></form></section>{status_panel}'''


def _calendar_settings_status_controls(calendar: CalendarRecord, return_to: str) -> str:
    if calendar.kind == "birthday":
        return ""
    hidden_return = f'<input type="hidden" name="return_to" value="{escape(return_to)}">'
    controls = []
    if not calendar.is_default and not calendar.is_archived:
        controls.append(
            f'<form method="post" action="/calendar/settings/calendars/{calendar.id}/default" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="Make this the default Calendar for new Events.">{hidden_return}<button class="button secondary" type="submit">Make default</button></form>'
        )
    archive_action = "unarchive" if calendar.is_archived else "archive"
    archive_label = "Unarchive" if calendar.is_archived else "Archive"
    controls.append(
        f'<form method="post" action="/calendar/settings/calendars/{calendar.id}/{archive_action}" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="{archive_label} this Calendar. Existing Event assignments are retained.">{hidden_return}<button class="button secondary" type="submit">{archive_label}</button></form>'
    )
    if not calendar.is_default:
        controls.append(
            f'<form method="post" action="/calendar/settings/calendars/{calendar.id}/delete" data-confirm-object="{escape(calendar.name)}" data-confirm-consequence="Permanently delete this empty Calendar. Assigned Events prevent deletion.">{hidden_return}<button class="button danger" type="submit">Delete</button></form>'
        )
    return "".join(controls)


def _calendar_url(parameters: list[tuple[str, str]]) -> str:
    return "/calendar?" + urlencode(parameters)


def _calendar_settings_url(path: str, return_to: str) -> str:
    return f"/calendar/settings{path}?{urlencode({'return_to': return_to})}"


def _calendar_url_with_query(query: str) -> str:
    return "/calendar?" + query


def default_event_values(calendars: list[CalendarRecord]) -> dict[str, str]:
    default = next(calendar for calendar in calendars if calendar.is_default and calendar.kind == "event")
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
        for calendar in calendars if calendar.kind == "event"
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


def _legacy_recurrence_fields(recurrence: RecurrenceDefinition | None) -> str:
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


def _recurrence_fields(values: dict[str, str], recurrence: RecurrenceDefinition | None) -> str:
    anchor = _recurrence_anchor(values)
    weekday = anchor.strftime("%A")
    ordinal = (anchor.day - 1) // 7 + 1
    monthly_options = [(f"monthly_{ordinal}_{anchor.weekday()}", f"Monthly on the {_ordinal_label(ordinal)} {weekday}")]
    if ordinal == 4:
        monthly_options.append((f"monthly_last_{anchor.weekday()}", f"Monthly on the last {weekday}"))
    elif ordinal == 5:
        monthly_options = [(f"monthly_last_{anchor.weekday()}", f"Monthly on the last {weekday}")]
    options = [("none", "Does not repeat"), ("daily", "Daily"), (f"weekly_{anchor.weekday()}", f"Weekly on {weekday}"), *monthly_options, ("yearly", f"Annually on {anchor.strftime('%-d %B')}"), ("weekdays", "Every weekday, Monday - Friday")]
    selected = _recurrence_preset(recurrence, anchor, options)
    choices = "".join(f'<button type="button" role="option" data-recurrence-choice value="{value}" aria-selected="{"true" if value == selected else "false"}">{escape(label)}</button>' for value, label in options)
    custom = f'<button type="button" role="option" data-recurrence-choice value="custom" aria-selected="{"true" if selected == "custom" else "false"}">Custom</button>'
    label = next(label for value, label in options if value == selected) if selected != "custom" else "Custom"
    return f'<fieldset class="calendar-recurrence"><legend>Recurrence</legend><input type="hidden" name="recurrence_preset" value="{escape(selected)}" data-recurrence-value><details class="recurrence-picker" data-recurrence-picker><summary class="button secondary"><span data-recurrence-label>{escape(label)}</span><span class="menu-chevron" aria-hidden="true">▾</span></summary><div class="recurrence-options" role="listbox" aria-label="Repeat options">{choices}{custom}</div></details><small class="field-help">Annual repeats on 29 February occur on 28 February in non-leap years.</small></fieldset>{_custom_recurrence_dialog(recurrence, anchor)}'


def _recurrence_anchor(values: dict[str, str]) -> date:
    raw_value = values.get("start_date", "") if values.get("all_day") == "1" else values.get("start_local", "")[:10]
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return date.today()


def _ordinal_label(value: int) -> str:
    return ("first", "second", "third", "fourth", "fifth")[value - 1]


def _recurrence_preset(recurrence: RecurrenceDefinition | None, anchor: date, options: list[tuple[str, str]]) -> str:
    if recurrence is None:
        return "none"
    rule = recurrence.rule
    expected = {"daily": ("daily", 1, (), 0, -1), f"weekly_{anchor.weekday()}": ("weekly", 1, (anchor.weekday(),), 0, -1), "yearly": ("yearly", 1, (), 0, -1), "weekdays": ("weekly", 1, (0, 1, 2, 3, 4), 0, -1)}
    for value, signature in expected.items():
        if (rule.frequency, rule.interval, rule.weekdays, rule.monthly_ordinal, rule.monthly_weekday) == signature:
            return value
    for value, _ in options:
        if value.startswith("monthly_"):
            _, ordinal, weekday = value.split("_")
            monthly_ordinal = -1 if ordinal == "last" else int(ordinal)
            if (rule.frequency, rule.interval, rule.weekdays, rule.monthly_ordinal, rule.monthly_weekday) == ("monthly", 1, (), monthly_ordinal, int(weekday)):
                return value
    return "custom"


def _legacy_custom_recurrence_dialog(recurrence: RecurrenceDefinition | None, anchor: date) -> str:
    rule = recurrence.rule if recurrence else None
    frequency = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}.get(rule.frequency if rule else "", "week")
    interval = rule.interval if rule else 1
    selected_weekdays = set(rule.weekdays) if rule and rule.weekdays else {anchor.weekday()}
    weekday_buttons = "".join(
        f'<label class="custom-weekday"><input type="checkbox" name="recurrence_custom_weekdays" value="{day}"{" checked" if day in selected_weekdays else ""}><span>{label}</span></label>'
        for day, label in enumerate(("M", "T", "W", "T", "F", "S", "S"))
    )
    pattern = "ordinal" if rule and rule.monthly_ordinal else "day"
    ordinal = rule.monthly_ordinal if rule and rule.monthly_ordinal in (1, 2, 3, 4) else (anchor.day - 1) // 7 + 1
    weekday = rule.monthly_weekday if rule and rule.monthly_weekday in range(7) else anchor.weekday()
    ordinal_options = "".join(f'<option value="{value}"{" selected" if value == ordinal else ""}>{label}</option>' for value, label in ((1, "first"), (2, "second"), (3, "third"), (4, "fourth")))
    weekday_options = "".join(f'<option value="{value}"{" selected" if value == weekday else ""}>{label}</option>' for value, label in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")))
    ending = "on" if rule and rule.until_date else "never"
    return f'''<dialog class="confirmation-dialog custom-recurrence-dialog" data-custom-recurrence-dialog aria-labelledby="custom-recurrence-title"><h2 id="custom-recurrence-title">Custom recurrence</h2><div class="custom-recurrence-fields"><label class="custom-repeat-every"><span>Repeat every</span><input name="recurrence_custom_interval" type="number" min="1" max="999" step="1" value="{interval}" required><select name="recurrence_custom_frequency" data-custom-frequency><option value="day"{" selected" if frequency == "day" else ""}>day</option><option value="week"{" selected" if frequency == "week" else ""}>week</option><option value="month"{" selected" if frequency == "month" else ""}>month</option><option value="year"{" selected" if frequency == "year" else ""}>year</option></select></label><section data-custom-weekdays{" hidden" if frequency != "week" else ""}><h3>Repeat on</h3><div class="custom-weekday-options">{weekday_buttons}</div></section><section data-custom-monthly{" hidden" if frequency != "month" else ""}><label><span>Repeat</span><select name="recurrence_custom_monthly_pattern" data-custom-monthly-pattern><option value="day"{" selected" if pattern == "day" else ""}>on day {anchor.day} of the month</option><option value="ordinal"{" selected" if pattern == "ordinal" else ""}>on an ordinal weekday</option></select></label><label data-custom-monthly-ordinal{" hidden" if pattern != "ordinal" else ""}><span>Repeat on the</span><span class="custom-monthly-ordinal"><select name="recurrence_custom_monthly_ordinal">{ordinal_options}</select><select name="recurrence_custom_monthly_weekday">{weekday_options}</select></span></label></section><section class="custom-recurrence-ends"><h3>Ends</h3><label><input type="radio" name="recurrence_custom_ends" value="never"{" checked" if ending == "never" else ""}> Never</label><label class="custom-end-row"><input type="radio" name="recurrence_custom_ends" value="on"{" checked" if ending == "on" else ""}> On <input name="recurrence_custom_until" type="date" value="{escape(rule.until_date if rule else "")}" data-custom-end-on></label><label class="custom-end-row"><input type="radio" name="recurrence_custom_ends" value="after"> After <span class="custom-occurrence-count"><input name="recurrence_custom_count" type="number" min="1" max="500" step="1" value="1" data-custom-end-after> occurrences</span></label></section></div><div class="actions"><button class="button secondary" type="button" data-custom-recurrence-cancel>Cancel</button><button class="button" type="button" data-custom-recurrence-confirm>OK</button></div></dialog>'''


def _custom_recurrence_dialog(recurrence: RecurrenceDefinition | None, anchor: date) -> str:
    rule = recurrence.rule if recurrence else None
    frequency = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}.get(rule.frequency if rule else "", "week")
    interval = rule.interval if rule else 1
    selected_weekdays = set(rule.weekdays) if rule and rule.weekdays else {anchor.weekday()}
    weekday_buttons = "".join(f'<label class="custom-weekday"><input type="checkbox" name="recurrence_custom_weekdays" value="{day}"{" checked" if day in selected_weekdays else ""}><span>{label}</span></label>' for day, label in enumerate(("M", "T", "W", "T", "F", "S", "S")))
    ordinal = (anchor.day - 1) // 7 + 1
    is_last_weekday = (anchor + timedelta(days=7)).month != anchor.month
    pattern = "last" if rule and rule.monthly_ordinal == -1 and is_last_weekday else "ordinal" if rule and rule.monthly_ordinal and ordinal <= 4 else "day"
    monthly_options = f'<option value="day"{" selected" if pattern == "day" else ""}>on day {anchor.day} of the month</option>'
    if ordinal <= 4:
        monthly_options += f'<option value="ordinal"{" selected" if pattern == "ordinal" else ""}>on the {_ordinal_label(ordinal)} {anchor.strftime("%A")}</option>'
    if is_last_weekday:
        monthly_options += f'<option value="last"{" selected" if pattern == "last" else ""}>on the last {anchor.strftime("%A")}</option>'
    ending = "on" if rule and rule.until_date else "never"
    return f'''<dialog class="confirmation-dialog custom-recurrence-dialog" data-custom-recurrence-dialog aria-labelledby="custom-recurrence-title"><h2 id="custom-recurrence-title">Custom recurrence</h2><div class="custom-recurrence-fields"><label class="custom-repeat-every"><span>Repeat every</span><input name="recurrence_custom_interval" type="number" min="1" max="999" step="1" value="{interval}" required><select name="recurrence_custom_frequency" data-custom-frequency><option value="day"{" selected" if frequency == "day" else ""}>day</option><option value="week"{" selected" if frequency == "week" else ""}>week</option><option value="month"{" selected" if frequency == "month" else ""}>month</option><option value="year"{" selected" if frequency == "year" else ""}>year</option></select></label><section data-custom-weekdays{" hidden" if frequency != "week" else ""}><h3>Repeat on</h3><div class="custom-weekday-options">{weekday_buttons}</div></section><section data-custom-monthly{" hidden" if frequency != "month" else ""}><label><span>Repeat</span><select name="recurrence_custom_monthly_pattern">{monthly_options}</select></label></section><section class="custom-recurrence-ends"><h3>Ends</h3><label><input type="radio" name="recurrence_custom_ends" value="never"{" checked" if ending == "never" else ""}> Never</label><label class="custom-end-row"><input type="radio" name="recurrence_custom_ends" value="on"{" checked" if ending == "on" else ""}> On <input name="recurrence_custom_until" type="date" value="{escape(rule.until_date if rule else "")}" data-custom-end-on></label><label class="custom-end-row"><input type="radio" name="recurrence_custom_ends" value="after"> After <span class="custom-occurrence-count"><input name="recurrence_custom_count" type="number" min="1" max="500" step="1" value="1" data-custom-end-after> occurrences</span></label></section></div><div class="actions"><button class="button secondary" type="button" data-custom-recurrence-cancel>Cancel</button><button class="button" type="button" data-custom-recurrence-confirm>OK</button></div></dialog>'''
