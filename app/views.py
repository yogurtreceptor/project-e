from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord


def layout(title: str, content: str, active_slug: str | None = None) -> str:
    nav_items = "".join(
        '<a class="{class_name}" href="/{slug}">{label}</a>'.format(
            class_name="active" if definition.slug == active_slug else "",
            slug=definition.slug,
            label=escape(definition.plural),
        )
        for definition in ENTITY_DEFINITIONS
    )
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
    </header>
    <main>{content}</main>
</body>
</html>"""


def dashboard_page(counts: dict[str, int]) -> str:
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

    return """
    <section class="page-heading">
        <h1>Operation Eddy</h1>
        <p>Local-first structured information for people, organisations and locations.</p>
    </section>
    <div class="grid">""" + "".join(cards) + "</div>"


def entity_list_page(definition: EntityDefinition, records: list[EntityRecord]) -> str:
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

    empty = (
        f'<p class="empty">No {escape(definition.plural.lower())} yet.</p>'
        if not rows
        else ""
    )
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

    return f"""
    <section class="page-heading split">
        <div>
            <h1>{escape(definition.plural)}</h1>
            <p>Browse canonical {escape(definition.plural.lower())} records.</p>
        </div>
        <a class="button" href="/{definition.slug}/new">Create {escape(definition.singular)}</a>
    </section>
    <section class="panel">{empty}{table}</section>
    """


def entity_detail_page(record: EntityRecord) -> str:
    definition = record.definition
    fields = []
    for field, raw_value in record.field_items():
        value = raw_value or "Not recorded"
        fields.append(f"<dt>{escape(field.label)}</dt><dd>{escape(value)}</dd>")

    return f"""
    <section class="page-heading split">
        <div>
            <p class="eyebrow">{escape(definition.singular)}</p>
            <h1>{escape(record.title)}</h1>
            <p>{escape(record.summary) if record.summary else 'No summary yet.'}</p>
        </div>
        <div class="actions">
            <a class="button secondary" href="/{definition.slug}">Back</a>
            <a class="button" href="/{definition.slug}/{record.id}/edit">Edit</a>
        </div>
    </section>
    <section class="panel">
        <h2>Details</h2>
        <dl>{''.join(fields)}</dl>
    </section>
    <section class="panel">
        <h2>Notes</h2>
        <p class="notes">{escape(record.notes) if record.notes else 'No notes yet.'}</p>
    </section>
    <section class="panel metadata">
        <h2>Metadata</h2>
        <dl>
            <dt>Created</dt><dd>{escape(record.created_at)}</dd>
            <dt>Updated</dt><dd>{escape(record.updated_at)}</dd>
        </dl>
    </section>
    """


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
    error_html = ""
    if errors:
        error_html = (
            '<div class="errors"><strong>Check the form</strong><ul>'
            + "".join(f"<li>{escape(error)}</li>" for error in errors)
            + "</ul></div>"
        )

    fields = [
        input_field("display_name", f"{definition.singular} name", values),
        input_field("summary", "Summary", values),
    ]
    for field in definition.fields:
        fields.append(input_field(field.name, field.label, values, field.multiline))
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


def not_found_page() -> str:
    return '<section class="panel"><h1>Not found</h1><p>The requested page does not exist.</p></section>'


def input_field(
    name: str, label: str, values: dict[str, str], multiline: bool = False
) -> str:
    value = escape(str(values.get(name, "")))
    if multiline:
        control = f'<textarea id="{name}" name="{name}" rows="5">{value}</textarea>'
    else:
        control = f'<input id="{name}" name="{name}" value="{value}">'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'
