from html import escape

from app.entities import ENTITY_DEFINITIONS


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
    map_class = "active" if active_slug == "map" else ""
    timeline_class = "active" if active_slug == "timeline" else ""
    system_tools_class = "active" if active_slug == "system-tools" else ""
    nav_items = entity_nav + f'<a class="{relationship_class}" href="/relationships">Relationships</a><a class="{timeline_class}" href="/timeline">Timeline</a><a class="{map_class}" href="/map">Map</a><a class="{system_tools_class}" href="/system-tools">System Tools</a>'
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
    <script src="/static/taxonomy.js"></script>
</body>
</html>"""
