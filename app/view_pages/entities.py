from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import RelationshipRecord
from app.journal import JournalEntry
from app.view_pages.common import format_relationship_dates
from app.view_pages.dashboard import favourite_form
from app.view_pages.icons import icon
from app.view_pages.forms import (
    address_lookup_field,
    address_lookup_script,
    associate_field_errors,
    entity_form_fields,
    entity_error_fields,
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
        count = len(integrity_warnings)
        warning_html = f'<div class="status-row warning" role="status"><span>{count} data integrity warning{"s" if count != 1 else ""} may affect this record.</span> <a href="/data-quality">Details</a></div>'
    return f"""
    <article class="entity-profile">
        {entity_profile_header(record)}
        {warning_html}
        <div class="profile-grid">
            <div class="profile-main">
                {domain_overview_section(record, relationships)}
                {'' if record.type in {'person', 'document', 'project'} else entity_geography_section(record, relationships)}
                {relationship_summary_section(record, relationships) if record.type in {'person', 'document', 'project'} else entity_relationships_panel(record, relationships)}
                {'' if record.type in {'person', 'document', 'project'} else related_entities_section(record, relationships)}
                {person_journal_section(record, journal_entries) if record.type == 'person' else entity_notes_section(record)}
            </div>
            <aside class="profile-side">
                {'' if record.type == 'document' else document_file_section(record)}
                {linked_documents_section(record, relationships)}
                {timeline_section(record, relationships)}
                {audit_history_section(history, audit_events) if record.type not in {'person', 'document', 'project'} else ''}
                {metadata_section(record, relationships) if record.type not in {'person', 'document', 'project'} else ''}
            </aside>
        </div>
    </article>
    """


def domain_overview_section(record, relationships):
    if record.type == "person": return person_overview_section(record, relationships)
    if record.type == "document": return document_overview_section(record)
    if record.type == "project": return project_overview_section(record)
    return entity_overview_section(record)

def definition_list(items):
    items = [(label, value) for label, value in items if value]
    return "<dl>" + "".join(f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>" for label, value in items) + "</dl>" if items else '<p class="empty">No details recorded yet.</p>'

def person_overview_section(record, relationships):
    locations=[]
    for relationship in relationships:
        location=relationship.other_entity(record.id)
        if location.type != "location": continue
        address=location.metadata.get("formatted_address") or ", ".join(v for v in (location.metadata.get("address_line_1", ""), location.metadata.get("suburb", ""), location.metadata.get("city", ""), location.metadata.get("state", ""), location.metadata.get("country", "")) if v)
        locations.append(f'<li><a href="/{location.slug}/{location.id}">{escape(location.title)}</a><span>{escape(relationship.display_label_from(record.id))}{": " + escape(address) if address else ""}</span></li>')
    location_content=f'<ul class="entity-link-list">{"".join(locations)}</ul>' if locations else f'<p class="empty">No linked locations yet. <a href="/relationships/new?source_entity_id={record.id}&amp;target_type=location&amp;context_entity_id={record.id}">Link a location</a>.</p>'
    contact=definition_list([("Birthday",record.metadata.get("birthday","")),("Phone",record.metadata.get("phone","")),("Email",record.metadata.get("email","")),("Alias",record.metadata.get("alias","")),("Nickname",record.metadata.get("nickname",""))])
    supporting=definition_list([(field.label, record.display_field_value(field)) for field in record.definition.fields if field.name in {"height", "weight", "languages", "nationalities", "ethnicities"}])
    supporting_html = "" if "No details recorded" in supporting else f"<h2>Personal details</h2>{supporting}"
    return f'<section class="panel profile-section person-overview"><h2>Contact</h2>{contact}{supporting_html}<div class="section-heading split"><h2>Locations</h2><a href="/map?entity_id={record.id}">View on map</a></div>{location_content}</section>'

def document_overview_section(record):
    file_name=record.metadata.get("file_name",""); mime=record.metadata.get("mime_type","")
    if file_name:
        open_action=f'<a class="button" href="/documents/{record.id}/download?open=1" target="_blank">Open</a>' if mime.startswith(("text/","image/")) else ""
        actions=f'<div class="actions document-file-actions">{open_action}<a class="button secondary" href="/documents/{record.id}/download" download>Download</a></div>'
    else: actions='<p class="empty">No uploaded file recorded.</p>'
    facts=definition_list([("Purpose",record.metadata.get("document_type","")),("Identifier",record.metadata.get("identifier","")),("Document date",record.metadata.get("document_date","")),("Expiry date",record.metadata.get("expiry_date",""))])
    return f'<section class="panel profile-section document-overview"><div class="section-heading split"><h2>Document</h2>{actions}</div>{facts}</section>'

def project_overview_section(record):
    status=record.metadata.get("status",""); badge=f'<span class="badge">{escape(status)}</span>' if status else '<span class="muted">Not recorded</span>'
    milestones=definition_list([("Started",record.metadata.get("started_at","")),("Target",record.metadata.get("target_date","")),("Completed",record.metadata.get("ended_at",""))])
    kind=definition_list([("Project type",record.metadata.get("project_type",""))])
    return f'<section class="panel profile-section project-overview"><div class="section-heading split"><h2>Status</h2>{badge}</div><h2>Milestones</h2>{milestones}{kind}</section>'

def relationship_summary_section(record, relationships):
    rows=[]
    for relationship in relationships:
        other=relationship.other_entity(record.id)
        rows.append(f'<li><a href="/{other.slug}/{other.id}">{escape(other.title)}</a><span><a href="/relationships/{relationship.id}">{escape(relationship.display_label_from(record.id))}</a></span></li>')
    content=f'<ul class="entity-link-list">{"".join(rows)}</ul>' if rows else '<p class="empty">No relationships yet.</p>'
    return f'<section class="panel profile-section relationship-summary" id="relationships"><div class="section-heading split"><h2>Relationships</h2><a class="icon-button" href="/relationships/new?source_entity_id={record.id}&amp;context_entity_id={record.id}" aria-label="Add relationship" title="Add relationship">{icon("add")}</a></div>{content}</section>'


def entity_profile_header(record: EntityRecord) -> str:
    definition = record.definition
    view_links = [
        ("Overview", f"/{definition.slug}/{record.id}"),
        ("Relationships", "#relationships"),
        ("Timeline", f"/timeline?entity_id={record.id}"),
    ]
    if record.type == "person":
        view_links.append(("Family Tree", f"/relationships/family-tree?person={record.id}"))
    if record.type in {"person", "organisation", "location", "asset"}:
        view_links.append(("Map", f"/map?entity_id={record.id}"))
    representation_links = "".join(
        f'<li><a href="{href}">{escape(label)}</a></li>' for label, href in view_links
    )
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/{definition.slug}">{escape(definition.plural)}</a></li><li aria-current="page">{escape(record.title)}</li></ol></nav>
    <section class="entity-hero panel">
        <div class="entity-identity">
            <p class="eyebrow">{escape(definition.singular)}</p>
            <h1>{escape(record.title)}</h1>
        </div>
        <div class="actions entity-actions">
            <details class="action-menu views-menu"><summary class="button secondary">Views</summary><div class="menu-panel"><strong>Record views</strong><ul>{representation_links}</ul><strong>Administrative</strong><ul><li><a href="/system-tools/audit?record_kind=entity&amp;record_id={record.id}">Audit</a></li></ul></div></details>
            <a class="button" href="/{definition.slug}/{record.id}/edit">Edit</a>
            <form method="post" action="/{definition.slug}/{record.id}/delete" data-confirm-object="{escape(record.title)}" data-confirm-consequence="Move this record to the Recycle Bin. It can be restored later.">
                <button class="button secondary" type="submit">Delete</button>
            </form>
            <details class="action-menu"><summary class="button quiet" aria-label="More record actions" title="More record actions">{icon("overflow")}</summary><div class="menu-panel"><ul><li>{favourite_form(record)}</li><li><a href="/relationships/new?source_entity_id={record.id}&amp;context_entity_id={record.id}">Add relationship</a></li><li><a href="/{definition.slug}/{record.id}/merge">Merge duplicate</a></li></ul></div></details>
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
    <section class="panel relationships-panel profile-section" id="relationships">
        <div class="section-heading split">
            <h2>Relationships</h2>
            <a class="icon-button" href="/relationships/new?source_entity_id={record.id}&context_entity_id={record.id}" aria-label="Add relationship" title="Add relationship">{icon("add")}</a>
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
    return_to: str | None = None,
) -> str:
    form_action = (
        f"/{definition.slug}/{entity_id}/edit" if entity_id else f"/{definition.slug}/new"
    )
    error_fields = entity_error_fields(definition, values, errors)
    error_html = error_block(errors, error_fields)
    duplicate_html = duplicate_warning(duplicate_matches or [], definition.type == "document")

    fields = []
    if definition.type == "location":
        fields.append(address_lookup_field())
    fields.append(
        associate_field_errors(
            entity_form_fields(definition, values, field_options=field_options),
            errors,
            error_fields,
        )
    )
    if definition.type == "document":
        fields.append(file_upload_field(values))

    location_class = " location-form" if definition.type == "location" else ""
    enctype = ' enctype="multipart/form-data"' if definition.type == "document" else ""
    cancel_href = return_to or (f"/{definition.slug}/{entity_id}" if entity_id else f"/{definition.slug}")
    return f"""
    <nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/{definition.slug}">{escape(definition.plural)}</a></li>{f'<li><a href="/{definition.slug}/{entity_id}">Record</a></li>' if entity_id else ''}<li aria-current="page">{escape(action)}</li></ol></nav>
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
        <form class="record-form{location_class}" method="post" action="{form_action}"{enctype} data-dirty-form>
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="{escape(cancel_href)}" data-dirty-cancel>Cancel</a>
                <button class="button" type="submit"{' name="confirm_duplicate" value="1"' if duplicate_matches else ''}>{'Save anyway' if duplicate_matches else 'Save'}</button>
            </div>
        </form>
    </section>
    {address_lookup_script() if definition.type == "location" else ""}
    """
