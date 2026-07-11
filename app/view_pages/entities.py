from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import RelationshipRecord
from app.journal import JournalEntry
from app.view_pages.common import format_relationship_dates
from app.view_pages.dashboard import favourite_form
from app.view_pages.forms import (
    address_lookup_field,
    address_lookup_script,
    entity_form_fields,
    duplicate_warning,
    error_block,
    existing_location_action,
    file_upload_field,
    input_field,
)


def entity_list_page(definition: EntityDefinition, records: list[EntityRecord], query: str = "", favourites_only: bool = False) -> str:
    rows = []
    secondary_heading = "DOB" if definition.type == "person" else "Notes"
    for record in records:
        if definition.type == "person":
            description = escape(record.metadata.get("birthday", "")) or "Not recorded"
        else:
            description = escape(record.notes) if record.notes else "No notes yet."
        rows.append(
            f"""
            <tr>
                <td><a href="/{definition.slug}/{record.id}">{escape(record.title)}</a></td>
                <td>{description}</td>
                <td class="row-actions">
                    <a href="/{definition.slug}/{record.id}/edit">Edit</a>
                    <form method="post" action="/{definition.slug}/{record.id}/delete" data-confirm-object="{escape(record.title)}" data-confirm-consequence="Move this record to the Recycle Bin. It can be restored later.">
                        <button class="link-button" type="submit">Delete</button>
                    </form>
                </td>
            </tr>
            """
        )

    empty = f'<p class="empty">No {escape(definition.plural.lower())} yet.</p>' if not rows else ""
    table = (
        f"""
        <table>
            <thead><tr><th>Name</th><th>{secondary_heading}</th><th></th></tr></thead>
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
    integrity_warnings: list = None,
    history: list = None,
    audit_events: list = None,
    journal_entries: list[JournalEntry] | None = None,
) -> str:
    integrity_warnings = integrity_warnings or []
    history = history or []
    audit_events = audit_events or []
    journal_entries = journal_entries or []
    warning_html = ""
    if integrity_warnings:
        items = "".join(f"<li>{escape(item.message)}</li>" for item in integrity_warnings)
        warning_html = f'<section class="warnings"><h2>Data integrity warnings</h2><ul>{items}</ul></section>'
    return f"""
    <article class="entity-profile">
        {entity_profile_header(record)}
        {warning_html}
        <div class="profile-grid">
            <div class="profile-main">
                {entity_overview_section(record)}
                {entity_geography_section(record, relationships)}
                {entity_relationships_panel(record, relationships)}
                {related_entities_section(record, relationships)}
                {person_journal_section(record, journal_entries) if record.type == 'person' else entity_notes_section(record)}
            </div>
            <aside class="profile-side">
                {document_file_section(record)}
                {linked_documents_section(record, relationships)}
                {timeline_section(record, relationships)}
                {audit_history_section(history, audit_events)}
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
            <a class="button secondary" href="/{definition.slug}/{record.id}/merge">Merge duplicate</a>
            <a class="button" href="/{definition.slug}/{record.id}/edit">Edit</a>
            <form method="post" action="/{definition.slug}/{record.id}/delete" data-confirm-object="{escape(record.title)}" data-confirm-consequence="Move this record to the Recycle Bin. It can be restored later.">
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
                    <td><a href="/relationships/{relationship.id}">{escape(relationship.display_label_from(record.id))}</a></td>
                    <td>{escape(relationship.status)}</td>
                    <td>{format_relationship_dates(relationship)}</td>
                    <td class="row-actions">
                        <a href="/relationships/{relationship.id}/edit?context_entity_id={record.id}">Edit</a><form method="post" action="/relationships/{relationship.id}/delete?context_entity_id={record.id}"><button class="link-button" type="submit">Delete</button></form>
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


def person_journal_section(record: EntityRecord, entries: list[JournalEntry]) -> str:
    bubbles = []
    for entry in entries:
        edited = (
            f'<span class="journal-edited">Edited {escape(entry.updated_at)}</span>'
            if entry.is_edited
            else ""
        )
        bubbles.append(
            f"""
            <article class="journal-entry">
                <p>{escape(entry.body)}</p>
                <footer>
                    <time datetime="{escape(entry.created_at)}">{escape(entry.created_at)}</time>
                    {edited}
                    <span class="journal-actions">
                        <a href="/people/{record.id}/journal/{entry.id}/edit">Edit</a>
                        <form method="post" action="/people/{record.id}/journal/{entry.id}/archive">
                            <button class="link-button journal-archive" type="submit">Archive</button>
                        </form>
                        <form method="post" action="/people/{record.id}/journal/{entry.id}/delete">
                            <button class="link-button journal-delete" type="submit">Delete</button>
                        </form>
                    </span>
                </footer>
            </article>
            """
        )
    content = "".join(bubbles) if bubbles else '<p class="empty">No journal entries yet.</p>'
    return f"""
    <section class="panel profile-section journal-section">
        <h2>Journal</h2>
        <form class="journal-create" method="post" action="/people/{record.id}/journal">
            <label><span>New entry</span><textarea name="body" rows="3" required></textarea></label>
            <button class="button" type="submit">Add entry</button>
        </form>
        <div class="journal-stream">{content}</div>
    </section>
    """


def journal_edit_page(record: EntityRecord, entry: JournalEntry, error: str = "") -> str:
    error_html = f'<div class="errors"><p>{escape(error)}</p></div>' if error else ""
    return f"""
    <section class="page-heading"><h1>Edit journal entry</h1><p>{escape(record.title)}</p></section>
    {error_html}
    <section class="panel">
        <form class="record-form" method="post" action="/people/{record.id}/journal/{entry.id}/edit">
            <label><span>Entry</span><textarea name="body" rows="6" required>{escape(entry.body)}</textarea></label>
            <div class="actions"><button class="button" type="submit">Save</button><a class="button secondary" href="/people/{record.id}">Cancel</a></div>
        </form>
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


def timeline_section(record: EntityRecord, relationships: list[RelationshipRecord], history: list = None) -> str:
    from app.timeline import registry
    events = registry.derive(record, relationships)
    items = "".join(f"<li><span>{escape(event.date)}</span> {escape(event.title)}</li>" for event in events)
    if not items: items = '<li><span>Not yet</span> No dated real-world events.</li>'
    return f"""<section class="panel profile-section"><h2>Timeline</h2><p class="muted">Real-world events only; audit history is separate.</p><ol class="timeline-list">{items}</ol></section>"""


def audit_history_section(history: list = None, audit_events: list = None) -> str:
    history = history or []
    audit_events = audit_events or []
    generic_items = [
        f"<li><span>{escape(event.occurred_at)}</span> {escape(event.event_type.replace('_', ' ').title())}{': ' + escape(event.notes) if event.notes else ''} <small>by {escape(event.actor)} · {escape(event.provenance)}</small></li>"
        for event in audit_events
    ]
    legacy_items = [
        f"<li><span>{escape(row['created_at'])}</span> {escape(row['event_type'].replace('_', ' ').title())} <small>Legacy edit history</small></li>"
        for row in history
    ]
    items = "".join(generic_items + legacy_items)
    if not items:
        items = '<li><span>Not yet</span> No changes recorded.</li>'
    return f"""<section class="panel profile-section"><h2>Change History</h2><p class="muted">Operational audit events only; real-world history is shown in Timeline.</p><ol class="timeline-list">{items}</ol></section>"""


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


def entity_form_page(
    definition: EntityDefinition,
    values: dict[str, str],
    errors: list[str],
    action: str,
    entity_id: int | None = None,
    duplicate_matches: list | None = None,
    field_options: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    form_action = (
        f"/{definition.slug}/{entity_id}/edit" if entity_id else f"/{definition.slug}/new"
    )
    error_html = error_block(errors)
    duplicate_html = duplicate_warning(duplicate_matches or [], definition.type == "document")

    fields = []
    if definition.type == "location":
        fields.append(address_lookup_field())
    fields.append(entity_form_fields(definition, values, field_options=field_options))
    if definition.type == "document":
        fields.append(file_upload_field(values))

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
        {duplicate_html}
        <form class="record-form{location_class}" method="post" action="{form_action}"{enctype}>
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="/{definition.slug}">Cancel</a>
                <button class="button" type="submit"{' name="confirm_duplicate" value="1"' if duplicate_matches else ''}>{'Save anyway' if duplicate_matches else 'Save'}</button>
            </div>
        </form>
    </section>
    {address_lookup_script() if definition.type == "location" else ""}
    """
