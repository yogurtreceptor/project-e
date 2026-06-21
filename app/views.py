import json
from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import DATE_PRECISIONS, RELATIONSHIP_STATUSES, RELATIONSHIP_TYPES, RelationshipRecord, relationship_types_for_pair


INLINE_RELATIONSHIP_ENTITY_TYPES = {"person", "organisation", "location"}


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
    map_class = "active" if active_slug == "map" else ""
    nav_items = entity_nav + f'<a class="{relationship_class}" href="/relationships">Relationships</a><a class="{search_class}" href="/search">Search</a><a class="{map_class}" href="/map">Map</a>'
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
        description = escape(record.notes) if record.notes else "No notes yet."
        rows.append(
            f"""
            <tr>
                <td><a href="/{definition.slug}/{record.id}">{escape(record.title)}</a></td>
                <td>{description}</td>
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
            <thead><tr><th>Name</th><th>Notes</th><th></th></tr></thead>
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
) -> str:
    return f"""
    <article class="entity-profile">
        {entity_profile_header(record)}
        <div class="profile-grid">
            <div class="profile-main">
                {entity_overview_section(record)}
                {entity_geography_section(record, relationships)}
                {entity_relationships_panel(record, relationships)}
                {related_entities_section(record, relationships)}
                {entity_notes_section(record)}
            </div>
            <aside class="profile-side">
                {document_file_section(record)}
                {linked_documents_section(record, relationships)}
                {timeline_section(record, relationships)}
                {metadata_section(record, relationships)}
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
        value = record.display_field_value(field)
        if value:
            items.append(f"<dt>{escape(field.label)}</dt><dd>{escape(value)}</dd>")
    content = f"<dl>{''.join(items)}</dl>" if items else '<p class="empty">No structured overview yet.</p>'
    return f"""
    <section class="panel profile-section">
        <h2>Overview</h2>
        {content}
    </section>
    """



def entity_geography_section(record: EntityRecord, relationships: list[RelationshipRecord]) -> str:
    if record.type in {"project", "document"}:
        return ""

    if record.type == "asset":
        latitude = record.metadata.get("latitude", "")
        longitude = record.metadata.get("longitude", "")
        if latitude and longitude:
            return f"""
            <section class="panel profile-section geography-section">
                <div class="section-heading split">
                    <h2>Geography</h2>
                    <a href="/map?entity_id={record.id}">View on map</a>
                </div>
                <dl>
                    <dt>Coordinates</dt><dd>{escape(latitude)}, {escape(longitude)}</dd>
                </dl>
            </section>
            """

    if record.type == "location":
        latitude = record.metadata.get("latitude", "")
        longitude = record.metadata.get("longitude", "")
        coordinates = f"{escape(latitude)}, {escape(longitude)}" if latitude and longitude else "Not recorded"
        address = record.metadata.get("formatted_address") or ", ".join(
            part
            for part in (
                record.metadata.get("address_line_1", ""),
                record.metadata.get("suburb", ""),
                record.metadata.get("city", ""),
                record.metadata.get("state", ""),
                record.metadata.get("country", ""),
            )
            if part
        )
        map_href = f"/map?entity_id={record.id}"
        return f"""
        <section class="panel profile-section geography-section">
            <div class="section-heading split">
                <h2>Geography</h2>
                <a href="{map_href}">View on map</a>
            </div>
            <dl>
                <dt>Address</dt><dd>{escape(address) if address else 'Not recorded'}</dd>
                <dt>Coordinates</dt><dd>{coordinates}</dd>
                <dt>Source</dt><dd>{escape(record.metadata.get('source', '')) if record.metadata.get('source') else 'Not recorded'}</dd>
            </dl>
        </section>
        """

    location_relationships = [
        relationship
        for relationship in relationships
        if relationship.type.category == "Location" and relationship.other_entity(record.id).type == "location"
    ]
    if not location_relationships:
        return f"""
        <section class="panel profile-section geography-section">
            <div class="section-heading split">
                <h2>Geography</h2>
                <a href="/relationships/new?source_entity_id={record.id}&target_type=location&context_entity_id={record.id}">Link location</a>
            </div>
            <p class="empty">No linked location yet.</p>
        </section>
        """

    rows = []
    for relationship in location_relationships:
        location = relationship.other_entity(record.id)
        latitude = location.metadata.get("latitude", "")
        longitude = location.metadata.get("longitude", "")
        coordinate_status = f"{escape(latitude)}, {escape(longitude)}" if latitude and longitude else "No coordinates"
        rows.append(
            f"""
            <tr>
                <td><a href="/{location.slug}/{location.id}">{escape(location.title)}</a></td>
                <td>{coordinate_status}</td>
                <td><a href="/map?entity_id={record.id}">View on map</a></td>
            </tr>
            """
        )
    return f"""
    <section class="panel profile-section geography-section">
        <div class="section-heading split">
            <h2>Geography</h2>
            <a href="/relationships/new?source_entity_id={record.id}&target_type=location&context_entity_id={record.id}">Link location</a>
        </div>
        <table>
            <thead><tr><th>Location</th><th>Coordinates</th><th></th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
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


def document_file_section(record: EntityRecord) -> str:
    if record.type != "document":
        return ""
    file_name = record.metadata.get("file_name", "")
    file_size = record.metadata.get("file_size", "")
    mime_type = record.metadata.get("mime_type", "")
    if file_name:
        content = f"""
        <dl>
            <dt>File</dt><dd><a href="/documents/{record.id}/download">{escape(file_name)}</a></dd>
            <dt>Size</dt><dd>{escape(file_size) if file_size else 'Not recorded'}</dd>
            <dt>MIME type</dt><dd>{escape(mime_type) if mime_type else 'Not recorded'}</dd>
        </dl>
        """
    else:
        content = '<p class="empty">No uploaded file recorded.</p>'
    return f"""
    <section class="panel profile-section">
        <h2>File</h2>
        {content}
    </section>
    """


def linked_documents_section(record: EntityRecord, relationships: list[RelationshipRecord]) -> str:
    if record.type == "document":
        return ""
    documents = [
        relationship.other_entity(record.id)
        for relationship in relationships
        if relationship.other_entity(record.id).type == "document"
    ]
    if documents:
        items = "".join(
            f'<li><a href="/{document.slug}/{document.id}">{escape(document.title)}</a><span>{escape(document.metadata.get("document_type", "") or "Document")}</span></li>'
            for document in documents
        )
        content = f'<ul class="entity-link-list">{items}</ul>'
    else:
        content = '<p class="empty">No linked documents yet.</p>'
    return f"""
    <section class="panel profile-section">
        <div class="section-heading split">
            <h2>Documents</h2>
            <a href="/relationships/new?source_entity_id={record.id}&target_type=document&context_entity_id={record.id}">Link document</a>
        </div>
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
) -> str:
    return f"""
    <section class="panel profile-section metadata">
        <h2>Metadata</h2>
        <dl>
            <dt>Entity ID</dt><dd>{record.id}</dd>
            <dt>Type</dt><dd>{escape(record.definition.singular)}</dd>
            <dt>Relationships</dt><dd>{len(relationships)}</dd>
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
    ]
    if definition.type == "location":
        fields.append(address_lookup_field())
    for field in definition.fields:
        if field.editable:
            fields.append(entity_field_control(field, values))
        else:
            fields.append(hidden_field(field.name, values))
    if definition.type == "document":
        fields.append(file_upload_field(values))
    fields.append(input_field("notes", "Notes", values, multiline=True))

    location_class = " location-form" if definition.type == "location" else ""
    enctype = ' enctype="multipart/form-data"' if definition.type == "document" else ""
    return f"""
    <section class="page-heading split">
        <div>
            <p class="eyebrow">{escape(definition.singular)}</p>
            <h1>{escape(action)} {escape(definition.singular)}</h1>
        </div>
        {existing_location_action(definition)}
    </section>
    <section class="panel">
        {error_html}
        <form class="record-form{location_class}" method="post" action="{form_action}"{enctype}>
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="/{definition.slug}">Cancel</a>
                <button class="button" type="submit">Save</button>
            </div>
        </form>
    </section>
    {address_lookup_script() if definition.type == "location" else ""}
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
    source_entity = context_entity
    if source_entity is None and values.get("source_entity_id"):
        source_entity = next((entity for entity in entities if str(entity.id) == str(values.get("source_entity_id"))), None)
    selected_target = next((entity for entity in entities if str(entity.id) == str(values.get("target_entity_id"))), None)
    target_type_for_options = selected_target.type if selected_target else target_type
    fields = []
    if context_entity is not None:
        fields.append(f'<div class="readonly-field"><span>Current entity</span><strong>{escape(context_entity.title)}</strong></div>')
        source_value = escape(str(values.get("source_entity_id", context_entity.id)))
        fields.append(f'<input type="hidden" name="source_entity_id" value="{source_value}">')
    else:
        fields.append(select_field("source_entity_id", "Source entity", entity_options(entities), values))
    fields.extend([
        connected_entity_field(target_entities, values),
        relationship_inline_entity_section(target_type),
        select_field("type", "Relationship category / type", relationship_type_options(source_entity, target_type_for_options), values),
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
    {relationship_form_script(entities, target_type)}
    """


def connected_entity_field(entities: list[EntityRecord], values: dict[str, str]) -> str:
    search = input_field(
        "connected_entity_search",
        "Search existing connected entities",
        {},
        input_type="search",
        attrs=' placeholder="Type to filter existing entities"',
    )
    select = select_field("target_entity_id", "Choose existing connected entity", entity_options(entities), values)
    return f"""
    <fieldset class="relationship-step">
        <legend>Connected entity</legend>
        <label class="inline-check"><input type="radio" name="target_mode" value="existing" checked> Use existing entity</label>
        {search}
        {select}
    </fieldset>
    """


def relationship_inline_entity_section(target_type: str | None = None) -> str:
    definitions = [
        definition
        for definition in ENTITY_DEFINITIONS
        if definition.type in INLINE_RELATIONSHIP_ENTITY_TYPES and (not target_type or definition.type == target_type)
    ]
    type_options = [(definition.type, definition.singular) for definition in definitions]
    selected_type = target_type or (definitions[0].type if definitions else "")
    values = {"new_entity_type": selected_type}
    fieldsets = []
    for definition in definitions:
        fields = [input_field("new_display_name", f"{definition.singular} name", {})]
        compact_fields = inline_fields_for_definition(definition)
        for field in compact_fields:
            fields.append(input_field(f"new_{field.name}", field.label, {}, multiline=field.multiline, input_type=field.input_type))
        fields.append(input_field("new_notes", "Notes", {}, multiline=True))
        fieldsets.append(
            f"""
            <div class="inline-entity-fields" data-inline-entity-type="{escape(definition.type)}">
                {''.join(fields)}
            </div>
            """
        )
    if not definitions:
        return ""
    return f"""
    <fieldset class="relationship-step inline-create">
        <legend>Create connected entity inline</legend>
        <label class="inline-check"><input type="radio" name="target_mode" value="create_new"> Create new entity</label>
        {select_field("new_entity_type", "New entity type", type_options, values)}
        {''.join(fieldsets)}
    </fieldset>
    """


def inline_fields_for_definition(definition: EntityDefinition):
    if definition.type == "person":
        return [field for field in definition.fields if field.name in {"given_name", "family_name", "email", "phone"}]
    if definition.type == "organisation":
        return [field for field in definition.fields if field.name in {"organisation_type", "website", "email", "phone"}]
    if definition.type == "location":
        return [field for field in definition.fields if field.name in {"formatted_address", "city", "state", "country"}]
    return []


def entity_options(entities: list[EntityRecord]) -> list[tuple[str, str]]:
    return [(str(entity.id), f"{entity.title} ({entity.definition.singular})") for entity in entities]


def relationship_type_options(
    source_entity: EntityRecord | None = None,
    target_type: str | None = None,
) -> list[tuple[str, str]]:
    if source_entity is not None and target_type:
        relationship_types = relationship_types_for_pair(source_entity.type, target_type)
    else:
        relationship_types = RELATIONSHIP_TYPES
    return [
        (relationship_type.key, relationship_option_text(relationship_type))
        for relationship_type in relationship_types
    ]


def relationship_option_text(relationship_type) -> str:
    subtype = relationship_type.display_label
    if relationship_type.category and subtype and relationship_type.category != subtype:
        return f"{relationship_type.category}: {subtype}"
    return subtype or relationship_type.label


def relationship_form_script(entities: list[EntityRecord], target_type: str | None = None) -> str:
    entity_data = [
        {"id": str(entity.id), "type": entity.type, "label": f"{entity.title} ({entity.definition.singular})"}
        for entity in entities
    ]
    type_data = [
        {
            "key": relationship_type.key,
            "label": relationship_option_text(relationship_type),
            "pairs": relationship_type.pairs,
        }
        for relationship_type in RELATIONSHIP_TYPES
    ]
    return f"""
    <script>
    (() => {{
        const entities = {json.dumps(entity_data).replace("</", "<\\/")};
        const relationshipTypes = {json.dumps(type_data).replace("</", "<\\/")};
        const forcedTargetType = {json.dumps(target_type or "")};
        const source = document.getElementById('source_entity_id');
        const target = document.getElementById('target_entity_id');
        const type = document.getElementById('type');
        const search = document.getElementById('connected_entity_search');
        const newType = document.getElementById('new_entity_type');
        const targetModes = Array.from(document.querySelectorAll('input[name="target_mode"]'));
        const entityTypeById = new Map(entities.map((entity) => [entity.id, entity.type]));

        const selectedMode = () => {{
            const selected = targetModes.find((item) => item.checked);
            return selected ? selected.value : 'existing';
        }};
        const currentSourceType = () => {{
            if (!source) return '';
            return entityTypeById.get(source.value) || '';
        }};
        const currentTargetType = () => {{
            if (selectedMode() === 'create_new') return newType ? newType.value : '';
            if (!target) return forcedTargetType || '';
            return entityTypeById.get(target.value) || forcedTargetType || '';
        }};
        const supportsPair = (relationshipType, sourceType, targetType) => {{
            if (!sourceType || !targetType) return true;
            if (!relationshipType.pairs.length) return true;
            return relationshipType.pairs.some((pair) =>
                (pair[0] === sourceType && pair[1] === targetType) ||
                (pair[0] === targetType && pair[1] === sourceType)
            );
        }};
        const refreshTypes = () => {{
            if (!type) return;
            const current = type.value;
            const sourceType = currentSourceType();
            const targetType = currentTargetType();
            let valid = relationshipTypes;
            if (sourceType && targetType) {{
                const specific = relationshipTypes.filter((relationshipType) => relationshipType.pairs.length && supportsPair(relationshipType, sourceType, targetType));
                valid = specific.length ? specific : relationshipTypes.filter((relationshipType) => !relationshipType.pairs.length);
            }}
            type.innerHTML = '<option value="">Select...</option>';
            valid.forEach((relationshipType) => {{
                const option = document.createElement('option');
                option.value = relationshipType.key;
                option.textContent = relationshipType.label;
                if (relationshipType.key === current) option.selected = true;
                type.appendChild(option);
            }});
            if (current && !valid.some((relationshipType) => relationshipType.key === current)) type.value = '';
        }};
        const filterTargets = () => {{
            if (!target || !search) return;
            const current = target.value;
            const term = search.value.trim().toLowerCase();
            target.innerHTML = '<option value="">Select...</option>';
            entities
                .filter((entity) => (!forcedTargetType || entity.type === forcedTargetType) && (!term || entity.label.toLowerCase().includes(term)))
                .forEach((entity) => {{
                    const option = document.createElement('option');
                    option.value = entity.id;
                    option.textContent = entity.label;
                    if (entity.id === current) option.selected = true;
                    target.appendChild(option);
                }});
            refreshTypes();
        }};
        const refreshInlineFields = () => {{
            const activeType = newType ? newType.value : '';
            document.querySelectorAll('[data-inline-entity-type]').forEach((section) => {{
                const active = section.dataset.inlineEntityType === activeType && selectedMode() === 'create_new';
                section.hidden = section.dataset.inlineEntityType !== activeType;
                section.querySelectorAll('input, textarea, select').forEach((field) => {{
                    field.disabled = !active;
                }});
            }});
            if (target) target.disabled = selectedMode() === 'create_new';
            if (search) search.disabled = selectedMode() === 'create_new';
            refreshTypes();
        }};
        if (search) search.addEventListener('input', filterTargets);
        if (source) source.addEventListener('change', refreshTypes);
        if (target) target.addEventListener('change', refreshTypes);
        if (newType) newType.addEventListener('change', refreshInlineFields);
        targetModes.forEach((item) => item.addEventListener('change', refreshInlineFields));
        filterTargets();
        refreshInlineFields();
    }})();
    </script>
    """


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
            <p>{escape(entity.notes) if entity.notes else 'No notes yet.'}</p>
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
    attrs: str = "",
) -> str:
    value = escape(str(values.get(name, "")))
    if multiline:
        control = f'<textarea id="{name}" name="{name}" rows="5">{value}</textarea>'
    else:
        control = f'<input id="{name}" name="{name}" type="{escape(input_type)}" value="{value}"{attrs}>'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'


def entity_field_control(field, values: dict[str, str]) -> str:
    field_values = values
    if field.default and not str(values.get(field.name, "")):
        field_values = {**values, field.name: field.default}
    if field.options and field.allow_custom:
        return custom_value_field(field.name, field.label, field.options, field_values)
    if field.options:
        return select_field(field.name, field.label, [(option, option) for option in field.options], field_values)
    attrs = ""
    if field.name == "value":
        attrs = ' min="0" step="1" inputmode="numeric" pattern="[0-9]*"'
    elif field.input_type == "number":
        attrs = ' step="any"'
    return input_field(field.name, field.label, field_values, field.multiline, field.input_type, attrs)


def custom_value_field(
    name: str,
    label: str,
    options: tuple[str, ...],
    values: dict[str, str],
) -> str:
    value = escape(str(values.get(name, "")))
    list_id = f"{name}_options"
    option_html = "".join(f'<option value="{escape(option)}"></option>' for option in options)
    control = f'<input id="{name}" name="{name}" list="{list_id}" value="{value}"><datalist id="{list_id}">{option_html}</datalist>'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'


def hidden_field(name: str, values: dict[str, str]) -> str:
    return f'<input type="hidden" name="{escape(name)}" value="{escape(str(values.get(name, "")))}">'


def file_upload_field(values: dict[str, str]) -> str:
    current_file = values.get("file_name", "")
    current = f'<p class="empty">Current file: {escape(current_file)}</p>' if current_file else ""
    return f"""
    <label for="upload"><span>Upload file</span><input id="upload" name="upload" type="file"></label>
    {current}
    """


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


def existing_location_action(definition: EntityDefinition) -> str:
    if definition.type != "location":
        return ""
    return '<a class="button secondary" href="/locations">Existing Locations</a>'


def address_lookup_field() -> str:
    return """
    <div class="address-lookup-field">
        <label for="address_search"><span>Address lookup</span>
            <input id="address_search" name="address_search" type="search" autocomplete="off" placeholder="Enter a full or near-full address">
        </label>
        <div class="address-lookup-actions">
            <button class="button secondary" id="address_search_button" type="button">Search Address</button>
            <span class="address-lookup-status" id="address_lookup_status" role="status"></span>
        </div>
        <div class="address-results" id="address_results"></div>
    </div>
    """


def address_lookup_script() -> str:
    return """
    <script>
    (() => {
        const search = document.getElementById('address_search');
        const button = document.getElementById('address_search_button');
        const resultsList = document.getElementById('address_results');
        const status = document.getElementById('address_lookup_status');
        if (!search || !button || !resultsList || !status) return;
        const fields = ['formatted_address', 'address_line_1', 'address_line_2', 'suburb', 'city', 'state', 'post_code', 'country', 'latitude', 'longitude', 'source'];
        const setStatus = (message) => {
            status.textContent = message;
        };
        const fill = (result) => {
            fields.forEach((name) => {
                const input = document.getElementById(name);
                if (input && result[name] !== undefined) input.value = result[name];
            });
            if (result.label) search.value = result.label;
            setStatus('Address fields filled. You can still edit them manually.');
        };
        const renderResults = (results) => {
            resultsList.innerHTML = '';
            if (!results.length) {
                resultsList.innerHTML = '<p class="empty">No matching addresses found. Try a fuller address, nearby suburb, or enter details manually.</p>';
                return;
            }
            const list = document.createElement('ul');
            results.forEach((result) => {
                const item = document.createElement('li');
                const choose = document.createElement('button');
                choose.type = 'button';
                choose.className = 'link-button address-result-button';
                choose.textContent = result.label || result.formatted_address || 'Unnamed result';
                choose.addEventListener('click', () => fill(result));
                item.appendChild(choose);
                if (result.latitude && result.longitude) {
                    const coordinates = document.createElement('span');
                    coordinates.textContent = `${result.latitude}, ${result.longitude}`;
                    item.appendChild(coordinates);
                }
                list.appendChild(item);
            });
            resultsList.appendChild(list);
        };
        const lookup = async () => {
            const query = search.value.trim();
            if (query.length < 3) {
                setStatus('Enter at least 3 characters.');
                return;
            }
            button.disabled = true;
            setStatus('Searching...');
            resultsList.innerHTML = '';
            try {
                const response = await fetch(`/geocoding/search?q=${encodeURIComponent(query)}`);
                const payload = await response.json();
                renderResults(payload.results || []);
                if (payload.error) setStatus('Lookup unavailable. You can enter the address manually.');
                else setStatus((payload.results || []).length ? 'Choose a result to fill the address fields.' : 'No results found.');
            } catch (error) {
                renderResults([]);
                setStatus('Lookup unavailable. You can enter the address manually.');
            } finally {
                button.disabled = false;
            }
        };
        button.addEventListener('click', lookup);
        search.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                lookup();
            }
        });
    })();
    </script>
    """


def map_page(payload: dict[str, object], focused_entity_id: str = "") -> str:
    data_json = json.dumps(payload).replace("</", "<\\/")
    focused_json = json.dumps(str(focused_entity_id))
    layer_controls = "".join(
        f'<label class="inline-check"><input type="checkbox" data-layer-toggle="{escape(layer["id"])}"{" checked" if layer.get("enabled") else ""}> {escape(layer["label"])}</label>'
        for layer in payload["layers"]
    )
    marker_count = len(payload["markers"])
    empty = '<p class="empty map-empty">No entities with coordinates yet.</p>' if marker_count == 0 else ""
    marker_links = "".join(
        f'<li><a href="{escape(marker["url"])}">{escape(marker["title"])}</a><span>{escape(marker["entityLabel"])} at {escape(marker["locationTitle"])}</span></li>'
        for marker in payload["markers"]
    )
    marker_list = f'<section class="panel map-marker-list"><h2>Mapped entities</h2><ul>{marker_links}</ul></section>' if marker_links else ""
    return f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <section class="page-heading split">
        <div>
            <h1>Map</h1>
            <p>{marker_count} mapped entities from canonical records and location relationships.</p>
        </div>
        <a class="button" href="/locations/new">Create Location</a>
    </section>
    <section class="panel map-toolbar">
        <div class="map-layers">{layer_controls}</div>
    </section>
    <section class="map-shell">
        <div id="eddy-map" class="eddy-map" aria-label="Entity map"></div>
        {empty}
    </section>
    {marker_list}
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    (() => {{
        const payload = {data_json};
        const focusedEntityId = {focused_json};
        const mapElement = document.getElementById('eddy-map');
        if (!mapElement || !window.L) return;
        const center = payload.defaultCenter;
        const map = L.map(mapElement).setView([center.latitude, center.longitude], center.zoom);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);
        const layerGroups = new Map();
        payload.layers.forEach((layer) => {{
            const group = L.layerGroup();
            if (layer.enabled) group.addTo(map);
            layerGroups.set(layer.id, group);
        }});
        const bounds = [];
        const visibleBounds = [];
        payload.markers.forEach((item) => {{
            const marker = L.marker([item.latitude, item.longitude]);
            marker.bindPopup(`
                <strong>${{escapeHtml(item.title)}}</strong><br>
                <span>${{escapeHtml(item.entityLabel)}} at ${{escapeHtml(item.locationTitle)}}</span><br>
                <small>${{escapeHtml(item.address || '')}}</small><br>
                <a href="${{item.url}}">Open entity</a>
            `);
            const group = layerGroups.get(item.layerId);
            if (group) group.addLayer(marker);
            bounds.push([item.latitude, item.longitude]);
            const layer = payload.layers.find((candidate) => candidate.id === item.layerId);
            if (!layer || layer.enabled) visibleBounds.push([item.latitude, item.longitude]);
            if (focusedEntityId && String(item.entityId) === focusedEntityId) marker.openPopup();
        }});
        if (visibleBounds.length) map.fitBounds(visibleBounds, {{ padding: [28, 28], maxZoom: 15 }});
        else if (bounds.length) map.fitBounds(bounds, {{ padding: [28, 28], maxZoom: 15 }});
        document.querySelectorAll('[data-layer-toggle]').forEach((control) => {{
            control.addEventListener('change', () => {{
                const group = layerGroups.get(control.dataset.layerToggle);
                if (!group) return;
                if (control.checked) group.addTo(map);
                else map.removeLayer(group);
            }});
        }});
        function escapeHtml(value) {{
            return String(value).replace(/[&<>'"]/g, (char) => ({{
                '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
            }}[char]));
        }}
    }})();
    </script>
    """
