from html import escape

from app.entities import ENTITY_DEFINITIONS
from app.view_pages.icons import DOMAIN_ICONS, icon


def layout(
    title: str,
    content: str,
    active_slug: str | None = None,
    show_save_toast: bool = False,
) -> str:
    def nav_link(href, label, icon_name, current=False):
        state = ' class="active" aria-current="page"' if current else ""
        return f'<a{state} href="{href}" title="{escape(label)}">{icon(icon_name)}<span class="nav-label">{escape(label)}</span></a>'

    entity_nav = "".join(
        nav_link(f"/{definition.slug}", definition.plural, DOMAIN_ICONS[definition.slug], definition.slug == active_slug)
        for definition in ENTITY_DEFINITIONS
    )
    connection_nav = "".join((
        nav_link("/relationships", "Relationships", "relationships", active_slug == "relationships"),
        nav_link("/calendar", "Calendar", "timeline", active_slug == "calendar"),
        nav_link("/tasks", "Tasks", "project", active_slug == "tasks"),
        nav_link("/inbox", "Inbox", "system", active_slug == "inbox"),
        nav_link("/timeline", "Timeline", "timeline", active_slug == "timeline"),
        nav_link("/map", "Map", "map", active_slug == "map"),
    ))
    tools = (("/search", "Search", "search", "Search"), ("/data-quality", "Data Quality", "system", "Data Quality Centre"), ("/taxonomies", "Taxonomies", "system", "Taxonomies"), ("/recycle-bin", "Recycle Bin", "delete", "Recycle Bin"), ("/system-tools/audit", "Audit", "system", "System Audit"), ("/system-tools/portability", "Import and Export", "system", "Import and export"))
    tool_nav = "".join(nav_link(href, label, icon_name, title == page_title) for href, label, icon_name, page_title in tools)
    save_toast = (
        '<div class="save-toast" role="status" aria-live="polite">Changes saved</div>'
        if show_save_toast else ""
    )
    save_cleanup = (
        """<script>(() => {
        const url = new URL(window.location.href);
        if (!url.searchParams.has("saved")) return;
        url.searchParams.delete("saved");
        history.replaceState(history.state, "", url.pathname + url.search + url.hash);
    })();</script>"""
        if show_save_toast else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} - Project E</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    {save_toast}
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <div class="app-shell" data-app-shell>
      <header class="site-header">
        <a class="brand" href="/" title="Project E — Home">{icon("e-mark", "Project E", "brand-mark")}<span class="brand-name">Project E</span></a>
        <a class="global-search-link" href="/search">{icon("search")}<span>Search</span></a>
      </header>
      <aside class="sidebar" aria-label="Browse">
        <button class="sidebar-super-key" type="button" aria-haspopup="dialog" aria-controls="super-key-dialog" data-super-key-open title="Go with Super Key">{icon("super-key")}<span class="nav-label">Super Key <kbd>Ctrl/Cmd K</kbd></span></button>
        <nav class="browse-nav" aria-label="Browse">
          {nav_link("/", "Home", "home", active_slug is None)}
          <section class="nav-group" aria-labelledby="information-nav-label"><h2 id="information-nav-label">{icon("information")}<span class="nav-label">Information</span></h2><div class="nav-children">{entity_nav}</div></section>
          <section class="nav-group" aria-labelledby="connections-nav-label"><h2 id="connections-nav-label">{icon("connections")}<span class="nav-label">Connections and views</span></h2><div class="nav-children">{connection_nav}</div></section>
          <section class="nav-group" aria-labelledby="tools-nav-label"><a class="nav-group-heading{' active-parent' if active_slug == 'system-tools' else ''}" id="tools-nav-label" href="/system-tools" aria-expanded="{'true' if active_slug == 'system-tools' else 'false'}" title="System Tools">{icon("system")}<span class="nav-label">System Tools</span></a><div class="nav-children">{tool_nav}</div></section>
        </nav>
        <button class="sidebar-toggle" type="button" aria-expanded="true" title="Collapse Browse" data-sidebar-toggle>{icon("overflow")}<span class="nav-label">Collapse</span></button>
      </aside>
      <main id="main-content" tabindex="-1">{content}</main>
    </div>
    <dialog class="super-key-dialog" id="super-key-dialog" data-super-key-dialog aria-labelledby="super-key-title">
        <form class="super-key-form" data-super-key-form>
            <div class="super-key-heading"><div><p class="eyebrow">Go</p><h2 id="super-key-title">Super Key</h2></div><button class="button quiet icon-button" type="button" data-super-key-close aria-label="Close Super Key" title="Close">{icon("close")}</button></div>
            <label for="super-key-input">Destination alias</label>
            <input id="super-key-input" name="destination" type="text" autocomplete="off" spellcheck="false" aria-describedby="super-key-help super-key-feedback" data-super-key-input>
            <p class="help-text" id="super-key-help">Try <code>map</code> or <code>bin</code>. On a Person page, try <code>tree</code>.</p>
            <p class="super-key-feedback" id="super-key-feedback" aria-live="polite" data-super-key-feedback></p>
        </form>
    </dialog>
    <dialog class="dirty-form-dialog" data-dirty-form-dialog aria-labelledby="dirty-form-title" aria-describedby="dirty-form-message">
        <form method="dialog">
            <h2 id="dirty-form-title">Discard unsaved changes?</h2>
            <p id="dirty-form-message">Changes on this form have not been saved.</p>
            <div class="actions"><button class="button secondary" value="cancel" data-dirty-keep>Keep editing</button><button class="button danger" type="button" data-dirty-discard>Discard changes</button></div>
        </form>
    </dialog>
    <dialog class="confirmation-dialog" data-confirmation-dialog aria-labelledby="confirmation-title" aria-describedby="confirmation-consequence">
        <form method="dialog">
            <h2 id="confirmation-title">Confirm action</h2>
            <p data-confirmation-object></p>
            <p id="confirmation-consequence" data-confirmation-consequence></p>
            <div class="actions">
                <button class="button secondary" value="cancel">Cancel</button>
                <button class="button danger" type="button" data-confirmation-confirm>Confirm</button>
            </div>
        </form>
    </dialog>
    <script src="/static/shell.js"></script>
    <script src="/static/super-key.js"></script>
    <script src="/static/taxonomy.js"></script>
    <script src="/static/confirmation.js"></script>
    <script src="/static/dirty-form.js"></script>
    <script src="/static/event-form.js"></script>
    {save_cleanup}
</body>
</html>"""
