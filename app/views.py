from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import DATE_PRECISIONS, RELATIONSHIP_STATUSES, RELATIONSHIP_TYPES, RelationshipRecord


def layout(title: str, content: str, active_slug: str | None = None) -> str:
    entity_nav = "".join(
        '<a class="{class_name}" href="/{slug}">{label}</a>'.format(
            class_name="active" if definition.slug == active_slug else "",
            slug=definition.slug,
            label=escape(definition.plural),
        )
        for definition in ENTITY_DEFINITIONS
    )
    relationship_class = "active" if active_slug == "relationships" else ""
    search_class = "active" if active_slug == "search" else ""
    nav_items = entity_nav + f'<a class="{relationship_class}" href="/relationships">Relationships</a><a class="{search_class}" href="/search">Search</a>'
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} - Operation Eddy</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <header class="site-header">
        <a class="brand" href="/">Operation Eddy</a>
        <nav>{nav_items}</nav>
        <form class="global-search" method="get" action="/search">
            <input name="q" placeholder="Search entities and relationships">
            <button type="submit">Search</button>
        </form>
    </header>
    <main>{content}</main>
</body>
</html>"""


def dashboard_page(counts: dict[str, int], relationship_count: int, recent_entities: list[EntityRecord], favourite_entities: list[EntityRecord]) -> str:
    cards = []
    for definition in ENTITY_DEFINITIONS:
        count = counts.get(definition.type, 0)
        cards.append(
            f"""
            <section class="panel entity-card">
                <div>
                    <h2>{escape(definition.plural)}</h2>
                    <p>{count} records</p>
                </div>
                <div class="actions">
                    <a class="button secondary" href="/{definition.slug}">Browse</a>
                    <a class="button" href="/{definition.slug}/new">Create</a>
                </div>
            </section>
            """
        )
    cards.append(
        f"""
        <section class="panel entity-card">
            <div>
                <h2>Relationships</h2>
                <p>{relationship_count} records</p>
            </div>
            <div class="actions">
                <a class="button secondary" href="/relationships">Browse</a>
            </div>
        </section>
        """
    )

    return """
    <section class="page-heading">
        <h1>Operation Eddy</h1>
        <p>Local-first structured information centred on entities and relationships.</p>
    </section>
    <section class="panel dashboard-search">
        <form method="get" action="/search">
            <input name="q" placeholder="Search people, organisations, locations, notes and relationships">
            <button class="button" type="submit">Search</button>
        </form>
    </section>
    <div class="grid">""" + "".join(cards) + "</div>" + dashboard_discovery_sections(recent_entities, favourite_entities)



def dashboard_discovery_sections(recent_entities: list[EntityRecord], favourite_entities: list[EntityRecord]) -> str:
    return f"""
    <div class="dashboard-discovery">
        <section class="panel">
            <div class="section-heading split">
                <h2>Recent Entities</h2>
                <a href="/search">Browse all</a>
            </div>
            {entity_link_list(recent_entities, 'No recently viewed entities yet.')}
        </section>
        <section class="panel">
            <div class="section-heading split">
                <h2>Favourites</h2>
                <a href="/search?favourites=1">View favourites</a>
            </div>
            {entity_link_list(favourite_entities, 'No favourites yet.')}
        </section>
    </div>
    """


def entity_link_list(records: list[EntityRecord], empty_text: str) -> str:
    if not records:
        return f'<p class="empty">{escape(empty_text)}</p>'
    items = "".join(
        f'<li><a href="/{record.slug}/{record.id}">{escape(record.title)}</a><span>{escape(record.definition.singular)}</span></li>'
        for record in records
    )
    return f'<ul class="entity-link-list">{items}</ul>'


def favourite_form(record: EntityRecord) -> str:
    next_value = "0" if record.is_favourite else "1"
    label = "Unfavourite" if record.is_favourite else "Favourite"
    button_class = "button secondary favourite active" if record.is_favourite else "button secondary favourite"
    return f"""
    <form method="post" action="/{record.slug}/{record.id}/favourite">
        <input type="hidden" name="is_favourite" value="{next_value}">
        <button class="{button_class}" type="submit">{label}</button>
    </form>
    """

def entity_list_page(definition: EntityDefinition, records: list[EntityRecord], query: str = "", favourites_only: bool = False) -> str:
    rows = []
    for record in records:
        summary = escape(record.summary) if record.summary else "No summary yet."
        rows.append(
            f"""
            <tr>
                <td><a href="/{definition.slug}/{record.id}">{escape(record.title)}</a></td>
                <td>{summary}</td>
                <td class="row-actions">
                    <a href="/{definition.slug}/{record.id}/edit">Edit</a>
                    <form method="post" action="/{definition.slug}/{record.id}/delete">
                        <button class="link-button" type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """
        )

    empty = f'<p class="empty">No {escape(definition.plural.lower())} yet.</p>' if not rows else ""
    table = (
        """
        <table>
            <thead><tr><th>Name</th><th>Summary</th><th></th></tr></thead>
            <tbody>"""
        + "".join(rows)
        + "</tbody></table>"
        if rows
        else ""
    )

    favourite_checked = " checked" if favourites_only else ""
    return f"""
    <section class="page-heading split">
        <div>
            <h1>{escape(definition.plural)}</h1>
            <p>Browse and filter canonical {escape(definition.plural.lower())} records.</p>
        </div>
        <a class="button" href="/{definition.slug}/new">Create {escape(definition.singular)}</a>
    </section>
    <section class="panel filter-panel">
        <form method="get" action="/{definition.slug}">
            <input name="q" value="{escape(query)}" placeholder="Filter {escape(definition.plural.lower())}">
            <label class="inline-check"><input type="checkbox" name="favourites" value="1"{favourite_checked}> Favourites only</label>
            <button class="button" type="submit">Apply</button>
            <a class="button secondary" href="/{definition.slug}">Clear</a>
        </form>
    </section>
    <section class="panel">{empty}{table}</section>
    """


def entity_detail_page(
    record: EntityRecord,
    relationships: list[RelationshipRecord],
    attachments: list[dict[str, str]],
) -> str:
    return f"""
    <article class="entity-profile">
        {entity_profile_header(record)}
        <div class="profile-grid">
            <div class="profile-main">
                {entity_overview_section(record)}
                {entity_relationships_panel(record, relationships)}
                {related_entities_section(record, relationships)}
                {entity_notes_section(record)}
            </div>
            <aside class="profile-side">
                {attachments_section(attachments)}
                {timeline_section(record, relationships)}
                {metadata_section(record, relationships, attachments)}
            </aside>
        </div>
    </article>
    """


def entity_profile_header(record: EntityRecord) -> str:
    definition = record.definition
    return f"""
    <section class="entity-hero panel">
        <div>
            <p class="eyebrow">{escape(definition.singular)}</p>
            <h1>{escape(record.title)}</h1>
            <p>{escape(record.summary) if record.summary else 'No summary yet.'}</p>
        </div>
        <div class="actions">
            <a class="button secondary" href="/{definition.slug}">Back</a>
            {favourite_form(record)}
            <a class="button secondary" href="/relationships/new?source_entity_id={record.id}&context_entity_id={record.id}">Create Relationship</a>
            <a class="button" href="/{definition.slug}/{record.id}/edit">Edit</a>
            <form method="post" action="/{definition.slug}/{record.id}/delete">
                <button class="button danger" type="submit">Delete</button>
            </form>
        </div>
    </section>
    """


def entity_overview_section(record: EntityRecord) -> str:
    fields = [field for field in record.definition.fields if field.overview]
    items = []
    for field in fields:
        value = record.field_value(field)
        if value:
            items.append(f"<dt>{escape(field.label)}</dt><dd>{escape(value)}</dd>")
    content = f"<dl>{''.join(items)}</dl>" if items else '<p class="empty">No structured overview yet.</p>'
    return f"""
    <section class="panel profile-section">
        <h2>Overview</h2>
        {content}
    </section>
    """


def entity_relationships_panel(record: EntityRecord, relationships: list[RelationshipRecord]) -> str:
    sections = []
    for definition in ENTITY_DEFINITIONS:
        grouped = [
            relationship
            for relationship in relationships
            if relationship.other_entity(record.id).definition.type == definition.type
        ]
        rows = []
        for relationship in grouped:
            other = relationship.other_entity(record.id)
            rows.append(
                f"""
                <tr>
                    <td><a href="/{other.slug}/{other.id}">{escape(other.title)}</a></td>
                    <td><a href="/relationships/{relationship.id}">{escape(relationship.label_from(record.id))}</a></td>
                    <td>{escape(relationship.status)}</td>
                    <td>{format_relationship_dates(relationship)}</td>
                    <td class="row-actions">
                        <a href="/relationships/{relationship.id}/edit?context_entity_id={record.id}">Edit</a>
                        <form method="post" action="/relationships/{relationship.id}/delete?context_entity_id={record.id}">
                            <button class="link-button" type="submit">Delete</button>
                        </form>
                    </td>
                </tr>
                """
            )
        content = (
            """
            <table>
                <thead><tr><th>Entity</th><th>Relationship</th><th>Status</th><th>Dates</th><th></th></tr></thead>
                <tbody>"""
            + "".join(rows)
            + "</tbody></table>"
            if rows
            else f'<p class="empty">No {escape(definition.plural.lower())} relationships yet.</p>'
        )
        sections.append(
            f"""
            <section class="relationship-group">
                <div class="section-heading split">
                    <h3>{escape(definition.plural)}</h3>
                    <a href="/relationships/new?source_entity_id={record.id}&target_type={definition.type}&context_entity_id={record.id}">Add {escape(definition.singular.lower())} relationship</a>
                </div>
                {content}
            </section>
            """
        )
    return f"""
    <section class="panel relationships-panel profile-section">
        <div class="section-heading split">
            <h2>Relationships</h2>
            <a href="/relationships/new?source_entity_id={record.id}&context_entity_id={record.id}">Add relationship</a>
        </div>
        {''.join(sections)}
    </section>
    """


def related_entities_section(record: EntityRecord, relationships: list[RelationshipRecord]) -> str:
    groups = []
    for definition in ENTITY_DEFINITIONS:
        related = [
            relationship.other_entity(record.id)
            for relationship in relationships
            if relationship.other_entity(record.id).definition.type == definition.type
        ]
        if not related:
            continue
        cards = "".join(
            f"""
            <a class="related-card" href="/{entity.slug}/{entity.id}">
                <strong>{escape(entity.title)}</strong>
                <span>{escape(entity.definition.singular)}</span>
            </a>
            """
            for entity in related
        )
        groups.append(f"<h3>{escape(definition.plural)}</h3><div class=\"related-grid\">{cards}</div>")
    content = "".join(groups) if groups else '<p class="empty">No related entities yet.</p>'
    return f"""
    <section class="panel profile-section">
        <h2>Related Entities</h2>
        {content}
    </section>
    """


def entity_notes_section(record: EntityRecord) -> str:
    return f"""
    <section class="panel profile-section">
        <h2>Notes</h2>
        <p class="notes">{escape(record.notes) if record.notes else 'No notes yet.'}</p>
    </section>
    """


def attachments_section(attachments: list[dict[str, str]]) -> str:
    if attachments:
        rows = "".join(
            f"<tr><td>{escape(item['file_name'])}</td><td>{escape(item['notes'])}</td></tr>"
            for item in attachments
        )
        content = f"<table><thead><tr><th>File</th><th>Notes</th></tr></thead><tbody>{rows}</tbody></table>"
    else:
        content = '<p class="empty">No attachments yet. Attachment records are ready; file upload comes later.</p>'
    return f"""
    <section class="panel profile-section">
        <h2>Attachments</h2>
        {content}
    </section>
    """


def timeline_section(record: EntityRecord, relationships: list[RelationshipRecord]) -> str:
    relationship_events = "".join(
        f"<li><span>{escape(relationship.created_at)}</span> Relationship added: {escape(relationship.label)}</li>"
        for relationship in relationships[:5]
    )
    if not relationship_events:
        relationship_events = '<li><span>Not yet</span> No relationship events recorded.</li>'
    return f"""
    <section class="panel profile-section">
        <h2>Timeline</h2>
        <ol class="timeline-list">
            <li><span>{escape(record.created_at)}</span> Entity created.</li>
            <li><span>{escape(record.updated_at)}</span> Entity modified.</li>
            {relationship_events}
        </ol>
    </section>
    """


def metadata_section(
    record: EntityRecord,
    relationships: list[RelationshipRecord],
    attachments: list[dict[str, str]],
) -> str:
    return f"""
    <section class="panel profile-section metadata">
        <h2>Metadata</h2>
        <dl>
            <dt>Entity ID</dt><dd>{record.id}</dd>
            <dt>Type</dt><dd>{escape(record.definition.singular)}</dd>
            <dt>Relationships</dt><dd>{len(relationships)}</dd>
            <dt>Attachments</dt><dd>{len(attachments)}</dd>
            <dt>Favourite</dt><dd>{'Yes' if record.is_favourite else 'No'}</dd>
            <dt>Created</dt><dd>{escape(record.created_at)}</dd>
            <dt>Updated</dt><dd>{escape(record.updated_at)}</dd>
            <dt>Last viewed</dt><dd>{escape(record.last_viewed_at) if record.last_viewed_at else 'Not recorded'}</dd>
        </dl>
    </section>
    """


def format_relationship_dates(relationship: RelationshipRecord) -> str:
    started = format_date_with_precision(relationship.started_at, relationship.started_at_precision)
    ended = format_date_with_precision(relationship.ended_at, relationship.ended_at_precision)
    if started == "Not recorded" and ended == "Not recorded":
        return "Not recorded"
    return f"{escape(started)} to {escape(ended)}"


def format_date_with_precision(value: str, precision: str) -> str:
    if not value:
        return "Not recorded"
    if precision == "approximate":
        return f"approx. {value}"
    if precision == "unknown":
        return f"date uncertain: {value}"
    return value


def entity_form_page(
    definition: EntityDefinition,
    values: dict[str, str],
    errors: list[str],
    action: str,
    entity_id: int | None = None,
) -> str:
    form_action = (
        f"/{definition.slug}/{entity_id}/edit" if entity_id else f"/{definition.slug}/new"
    )
    error_html = error_block(errors)

    fields = [
        input_field("display_name", f"{definition.singular} name", values),
        input_field("summary", "Summary", values),
    ]
    for field in definition.fields:
        fields.append(input_field(field.name, field.label, values, field.multiline, field.input_type))
    fields.append(input_field("notes", "Notes", values, multiline=True))

    return f"""
    <section class="page-heading">
        <p class="eyebrow">{escape(definition.singular)}</p>
        <h1>{escape(action)} {escape(definition.singular)}</h1>
    </section>
    <section class="panel">
        {error_html}
        <form class="record-form" method="post" action="{form_action}">
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="/{definition.slug}">Cancel</a>
                <button class="button" type="submit">Save</button>
            </div>
        </form>
    </section>
    """


def relationship_list_page(relationships: list[RelationshipRecord]) -> str:
    if not relationships:
        content = '<p class="empty">No relationships yet.</p>'
    else:
        rows = []
        for relationship in relationships:
            rows.append(
                f"""
                <tr>
                    <td><a href="/relationships/{relationship.id}">{escape(relationship.label)}</a></td>
                    <td><a href="/{relationship.source.slug}/{relationship.source.id}">{escape(relationship.source.title)}</a></td>
                    <td><a href="/{relationship.target.slug}/{relationship.target.id}">{escape(relationship.target.title)}</a></td>
                    <td>{escape(relationship.status)}</td>
                    <td class="row-actions">
                        <a href="/relationships/{relationship.id}/edit">Edit</a>
                        <form method="post" action="/relationships/{relationship.id}/delete">
                            <button class="link-button" type="submit">Delete</button>
                        </form>
                    </td>
                </tr>
                """
            )
        content = (
            """
            <table>
                <thead><tr><th>Type</th><th>Source</th><th>Target</th><th>Status</th><th></th></tr></thead>
                <tbody>"""
            + "".join(rows)
            + "</tbody></table>"
        )
    return f"""
    <section class="page-heading split">
        <div>
            <h1>Relationships</h1>
            <p>Browse first-class links between any entity types.</p>
        </div>
    </section>
    <section class="panel">{content}</section>
    """


def relationship_detail_page(relationship: RelationshipRecord) -> str:
    return f"""
    <section class="page-heading split">
        <div>
            <p class="eyebrow">Relationship</p>
            <h1>{escape(relationship.source.title)} {escape(relationship.label)} {escape(relationship.target.title)}</h1>
            <p>{escape(relationship.status)}</p>
        </div>
        <div class="actions">
            <a class="button secondary" href="/relationships">Back</a>
            <a class="button" href="/relationships/{relationship.id}/edit">Edit</a>
        </div>
    </section>
    <section class="panel">
        <h2>Connected entities</h2>
        <dl>
            <dt>Source</dt><dd><a href="/{relationship.source.slug}/{relationship.source.id}">{escape(relationship.source.title)}</a></dd>
            <dt>Target</dt><dd><a href="/{relationship.target.slug}/{relationship.target.id}">{escape(relationship.target.title)}</a></dd>
            <dt>Type</dt><dd>{escape(relationship.label)}</dd>
            <dt>Inverse</dt><dd>{escape(relationship.type.inverse_label)}</dd>
            <dt>Status</dt><dd>{escape(relationship.status)}</dd>
            <dt>Started</dt><dd>{escape(format_date_with_precision(relationship.started_at, relationship.started_at_precision))}</dd>
            <dt>Ended</dt><dd>{escape(format_date_with_precision(relationship.ended_at, relationship.ended_at_precision))}</dd>
        </dl>
    </section>
    <section class="panel">
        <h2>Notes</h2>
        <p class="notes">{escape(relationship.notes) if relationship.notes else 'No notes yet.'}</p>
    </section>
    <section class="panel metadata">
        <h2>Metadata</h2>
        <dl>
            <dt>Created</dt><dd>{escape(relationship.created_at)}</dd>
            <dt>Updated</dt><dd>{escape(relationship.updated_at)}</dd>
        </dl>
    </section>
    """


def relationship_form_page(
    values: dict[str, str],
    errors: list[str],
    entities: list[EntityRecord],
    action: str,
    relationship_id: int | None = None,
    context_entity: EntityRecord | None = None,
    target_type: str | None = None,
) -> str:
    query = []
    if context_entity is not None:
        query.append(f"context_entity_id={context_entity.id}")
    if target_type:
        query.append(f"target_type={target_type}")
    query_string = "?" + "&".join(query) if query else ""
    form_action = f"/relationships/{relationship_id}/edit{query_string}" if relationship_id else f"/relationships/new{query_string}"
    target_entities = [entity for entity in entities if not target_type or entity.type == target_type]
    fields = []
    if context_entity is not None:
        fields.append(f'<div class="readonly-field"><span>Current entity</span><strong>{escape(context_entity.title)}</strong></div>')
        source_value = escape(str(values.get("source_entity_id", context_entity.id)))
        fields.append(f'<input type="hidden" name="source_entity_id" value="{source_value}">')
    else:
        fields.append(select_field("source_entity_id", "Source entity", entity_options(entities), values))
    fields.extend([
        select_field("type", "Relationship type", relationship_type_options(), values),
        select_field("target_entity_id", "Connected entity", entity_options(target_entities), values),
        select_field("status", "Status", [(status, status.title()) for status in RELATIONSHIP_STATUSES], values),
        input_field("started_at", "Started", values, input_type="date"),
        select_field("started_at_precision", "Start date certainty", date_precision_options(), values),
        input_field("ended_at", "Ended", values, input_type="date"),
        select_field("ended_at_precision", "End date certainty", date_precision_options(), values),
        input_field("notes", "Notes", values, multiline=True),
    ])
    return f"""
    <section class="page-heading">
        <p class="eyebrow">Relationship</p>
        <h1>{escape(action)} Relationship</h1>
    </section>
    <section class="panel">
        {error_block(errors)}
        <form class="record-form" method="post" action="{form_action}">
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="{'/' + context_entity.slug + '/' + str(context_entity.id) if context_entity else '/relationships'}">Cancel</a>
                <button class="button" type="submit">Save</button>
            </div>
        </form>
    </section>
    """


def entity_options(entities: list[EntityRecord]) -> list[tuple[str, str]]:
    return [(str(entity.id), f"{entity.title} ({entity.definition.singular})") for entity in entities]


def relationship_type_options() -> list[tuple[str, str]]:
    return [(relationship_type.key, relationship_type.label) for relationship_type in RELATIONSHIP_TYPES]


def date_precision_options() -> list[tuple[str, str]]:
    return [(precision, precision.replace("_", " ").title()) for precision in DATE_PRECISIONS]



def search_page(query: str, entity_type: str, favourites_only: bool, results: list[dict[str, object]]) -> str:
    type_options = ['<option value="">All entity types</option>']
    for definition in ENTITY_DEFINITIONS:
        selected = " selected" if definition.type == entity_type else ""
        type_options.append(f'<option value="{definition.type}"{selected}>{escape(definition.plural)}</option>')
    checked = " checked" if favourites_only else ""
    if results:
        cards = "".join(search_result_card(result) for result in results)
    else:
        cards = '<p class="empty">No matching entities yet.</p>'
    return f"""
    <section class="page-heading">
        <h1>Search</h1>
        <p>Find entities by their fields, notes and relationship context.</p>
    </section>
    <section class="panel search-panel">
        <form method="get" action="/search">
            <input name="q" value="{escape(query)}" placeholder="Search entities and relationships">
            <select name="type">{''.join(type_options)}</select>
            <label class="inline-check"><input type="checkbox" name="favourites" value="1"{checked}> Favourites only</label>
            <button class="button" type="submit">Search</button>
            <a class="button secondary" href="/search">Clear</a>
        </form>
    </section>
    <section class="search-results">{cards}</section>
    """


def search_result_card(result: dict[str, object]) -> str:
    entity = result["entity"]
    matched_relationships = result["matched_relationships"]
    relationship_count = result["relationship_count"]
    relationship_html = ""
    if matched_relationships:
        relationship_items = "".join(
            f'<li><a href="/relationships/{relationship.id}">{escape(relationship.label_from(entity.id))}</a> <a href="/{relationship.other_entity(entity.id).slug}/{relationship.other_entity(entity.id).id}">{escape(relationship.other_entity(entity.id).title)}</a></li>'
            for relationship in matched_relationships[:4]
        )
        relationship_html = f'<div class="matched-relationships"><strong>Relationship matches</strong><ul>{relationship_items}</ul></div>'
    favourite = '<span class="pill">Favourite</span>' if entity.is_favourite else ""
    return f"""
    <article class="panel search-result-card">
        <div>
            <p class="eyebrow">{escape(entity.definition.singular)}</p>
            <h2><a href="/{entity.slug}/{entity.id}">{escape(entity.title)}</a></h2>
            <p>{escape(entity.summary) if entity.summary else 'No summary yet.'}</p>
            <div class="result-meta">{favourite}<span>{relationship_count} relationships</span></div>
        </div>
        {relationship_html}
    </article>
    """

def not_found_page() -> str:
    return '<section class="panel"><h1>Not found</h1><p>The requested page does not exist.</p></section>'


def error_block(errors: list[str]) -> str:
    if not errors:
        return ""
    return (
        '<div class="errors"><strong>Check the form</strong><ul>'
        + "".join(f"<li>{escape(error)}</li>" for error in errors)
        + "</ul></div>"
    )


def input_field(
    name: str,
    label: str,
    values: dict[str, str],
    multiline: bool = False,
    input_type: str = "text",
) -> str:
    value = escape(str(values.get(name, "")))
    if multiline:
        control = f'<textarea id="{name}" name="{name}" rows="5">{value}</textarea>'
    else:
        control = f'<input id="{name}" name="{name}" type="{escape(input_type)}" value="{value}">'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'


def select_field(
    name: str, label: str, options: list[tuple[str, str]], values: dict[str, str]
) -> str:
    current = str(values.get(name, ""))
    option_html = ['<option value="">Select...</option>']
    for value, text in options:
        selected = " selected" if value == current else ""
        option_html.append(
            f'<option value="{escape(value)}"{selected}>{escape(text)}</option>'
        )
    return f'<label for="{name}"><span>{escape(label)}</span><select id="{name}" name="{name}">{"".join(option_html)}</select></label>'
