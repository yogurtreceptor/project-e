"""Read-only Event projections used by Search and related-record navigation."""

from datetime import date, datetime, timedelta
from html import escape

from app.calendar_service import CalendarRecord
from app.event_service import EventRecord
from app.relationships import RelationshipRecord
from app.view_pages.entities import audit_history_section


def event_projection_page(
    event: EventRecord,
    calendar: CalendarRecord | None,
    relationships: list[RelationshipRecord],
    history: list,
    audit_events: list,
) -> str:
    """Render a canonical Event without exposing the deferred Calendar editor."""
    calendar_name = calendar.name if calendar is not None else "Unavailable Calendar"
    calendar_colour = calendar.colour if calendar is not None else "#6B7280"
    status = "Cancelled" if event.is_cancelled else "Planned"
    if event.is_archived:
        status += " · Archived"
    relationship_items = "".join(
        f'<li><a href="/{other.slug}/{other.id}">{escape(other.title)}</a>'
        f'<span><a href="/relationships/{relationship.id}">'
        f'{escape(relationship.display_label_from(event.id))}</a></span></li>'
        for relationship in relationships
        for other in (relationship.other_entity(event.id),)
    )
    related = (
        f'<ul class="entity-link-list">{relationship_items}</ul>'
        if relationship_items
        else '<p class="empty">No relationships yet.</p>'
    )
    return f"""
    <article class="entity-profile event-projection">
        <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/search?type=event">Search</a></li><li aria-current="page">{escape(event.title)}</li></ol></nav>
        <section class="entity-hero panel">
            <div class="entity-identity"><p class="eyebrow">Event</p><h1>{escape(event.title)}</h1></div>
            <div class="actions entity-actions"><a class="button secondary" href="/search?type=event">Search Events</a></div>
        </section>
        <div class="profile-grid"><div class="profile-main">
            <section class="panel profile-section"><h2>Event details</h2><dl>
                <dt>Calendar</dt><dd><span class="badge" style="border-color: {escape(calendar_colour)}">{escape(calendar_name)}</span></dd>
                <dt>Status</dt><dd>{escape(status)}</dd>
                {event_time_details(event)}
            </dl></section>
            <section class="panel profile-section" id="relationships"><h2>Relationships</h2>{related}</section>
            <section class="panel profile-section"><h2>Notes</h2><p class="notes">{escape(event.notes) if event.notes else 'No notes yet.'}</p></section>
        </div><aside class="profile-side">{audit_history_section(history, audit_events)}</aside></div>
    </article>
    """


def event_time_details(event: EventRecord) -> str:
    if event.is_all_day:
        end_date = (
            date.fromisoformat(event.end_date_exclusive) - timedelta(days=1)
        ).isoformat()
        return (
            f"<dt>All day</dt><dd>Yes</dd><dt>Dates</dt>"
            f"<dd>{escape(event.start_date)} to {escape(end_date)}</dd>"
            f"<dt>Date precision</dt><dd>{escape(event.date_precision.title())}</dd>"
        )
    starts = _display_local_instant(event.start_utc, event.timezone)
    ends = _display_local_instant(event.end_utc, event.timezone)
    return (
        f"<dt>All day</dt><dd>No</dd><dt>Starts</dt><dd>{escape(event.start_utc)}</dd>"
        f"<dt>Local schedule</dt><dd>{escape(starts)} to {escape(ends)}</dd>"
        f"<dt>Ends</dt><dd>{escape(event.end_utc)}</dd>"
        f"<dt>Originating timezone</dt><dd>{escape(event.timezone)}</dd>"
    )


def _display_local_instant(value: str, timezone_name: str) -> str:
    from zoneinfo import ZoneInfo
    instant = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    return instant.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")
