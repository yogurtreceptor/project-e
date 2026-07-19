from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityRecord
from app.timeline import TimelineEvent, TimelineFilters


def universal_timeline_page(
    events: list[TimelineEvent],
    filters: TimelineFilters,
    related_options: dict[str, list[EntityRecord]],
) -> str:
    entity_options = '<option value="">All entity types</option>' + "".join(
        _option(definition.type, definition.plural, filters.entity_type)
        for definition in ENTITY_DEFINITIONS
    )
    cards = "".join(_event_card(event) for event in events)
    active_filters = bool(filters.entity_type or filters.date_from or filters.date_to or filters.related_person_id or filters.related_organisation_id or filters.related_project_id)
    empty = "" if cards else ('<div class="empty-state"><h2>No matching events</h2><p>No timeline entries match these filters.</p><a class="button secondary" href="/timeline">Clear filters</a></div>' if active_filters else '<div class="empty-state"><h2>No timeline entries yet</h2><p>Dated entity facts and relationships contribute events here.</p></div>')
    return f"""
    <section class="page-heading">
        <h1>Universal Timeline</h1>
        <p>Real-world events derived from canonical records and relationships.</p>
    </section>
    <section class="panel filter-panel timeline-filters">
        <form method="get" action="/timeline">
            <label><span>Entity type</span><select name="type">{entity_options}</select></label>
            <label><span>From</span><input name="from" type="date" value="{escape(filters.date_from)}"></label>
            <label><span>To</span><input name="to" type="date" value="{escape(filters.date_to)}"></label>
            <label><span>Related person</span><select name="person">{_related_options(related_options['person'], filters.related_person_id)}</select></label>
            <label><span>Related organisation</span><select name="organisation">{_related_options(related_options['organisation'], filters.related_organisation_id)}</select></label>
            <label><span>Related project</span><select name="project">{_related_options(related_options['project'], filters.related_project_id)}</select></label>
            <div class="actions"><button class="button" type="submit">Apply</button><a class="button secondary" href="/timeline">Clear</a></div>
        </form>
    </section>
    <p class="collection-summary" role="status">{len(events)} event{"s" if len(events) != 1 else ""}.</p><section class="panel universal-timeline">{empty}<ol class="timeline-list">{cards}</ol></section>
    """


def _option(value: str, label: str, selected: str) -> str:
    selected_attribute = " selected" if value == selected else ""
    return f'<option value="{escape(value)}"{selected_attribute}>{escape(label)}</option>'


def _related_options(records: list[EntityRecord], selected_id: int | None) -> str:
    options = '<option value="">Any</option>'
    return options + "".join(
        _option(str(record.id), record.title, str(selected_id or "")) for record in records
    )


def _event_card(event: TimelineEvent) -> str:
    category = "Relationship" if event.category == "relationship" else event.origin_type.title()
    return f"""
    <li class="timeline-entry">
        <time datetime="{escape(event.date)}">{escape(event.date)}</time>
        <div><span class="timeline-kind">{escape(category)}</span>
        <a href="{escape(event.href)}">{escape(event.title)}</a>
        <p>{escape(event.origin_title)}</p></div>
    </li>"""
