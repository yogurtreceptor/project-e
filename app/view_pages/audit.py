from html import escape

from app.audit import AuditFilters


def system_audit_page(events: list, filters: AuditFilters) -> str:
    event_options = _options(("create", "edit", "delete", "restore", "permanent_delete", "merge", "validation", "inference", "import", "manual_override"), filters.event_type)
    kind_options = _options(("entity", "relationship", "taxonomy_entry", "finding"), filters.record_kind)
    rows = "".join(
        f"<tr><td>{escape(event.occurred_at)}</td><td>{escape(event.subject_kind.replace('_', ' ').title())}</td><td>{escape(event.action.replace('_', ' ').title())}</td><td>{escape(event.notes or '—')}</td><td>{escape(event.actor)}</td></tr>"
        for event in events
    )
    content = f"<table><thead><tr><th>When</th><th>Record type</th><th>Action</th><th>Details</th><th>Actor</th></tr></thead><tbody>{rows}</tbody></table>" if rows else '<p class="empty">No audit events match these filters.</p>'
    return f'''<section class="page-heading split"><div><p class="eyebrow">System Tools</p><h1>Audit</h1><p>Platform-wide operational history. Entity timelines continue to show real-world dates separately.</p></div><a class="button secondary" href="/system-tools">Back to System Tools</a></section>
    <section class="panel filter-panel"><form method="get" action="/system-tools/audit"><label><span>Action</span><select name="event_type"><option value="">All actions</option>{event_options}</select></label><label><span>Record type</span><select name="record_kind"><option value="">All record types</option>{kind_options}</select></label><div class="actions"><button class="button" type="submit">Apply</button><a class="button secondary" href="/system-tools/audit">Clear</a></div></form></section>
    <section class="panel">{content}</section>'''


def _options(values: tuple[str, ...], selected: str) -> str:
    return "".join(f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(value.replace("_", " ").title())}</option>' for value in values)
