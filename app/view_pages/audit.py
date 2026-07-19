from html import escape

from app.audit import AuditFilters


def system_audit_page(events: list, filters: AuditFilters) -> str:
    event_options = _options(("create", "edit", "delete", "restore", "permanent_delete", "merge", "validation", "inference", "import", "manual_override"), filters.event_type)
    kind_options = _options(("entity", "relationship", "taxonomy_entry", "finding"), filters.record_kind)
    scope_input = f'<input type="hidden" name="record_id" value="{filters.record_id}">' if filters.record_id is not None else ""
    kind_control = (f'<input type="hidden" name="record_kind" value="{escape(filters.record_kind)}"><div class="readonly-field"><span>Record type</span><strong>{escape(filters.record_kind.title())}</strong></div>' if filters.record_id is not None else f'<label><span>Record type</span><select name="record_kind"><option value="">All record types</option>{kind_options}</select></label>')
    scope_text = f' Filtered to {escape(filters.record_kind or "record")} {filters.record_id}.' if filters.record_id is not None else ""
    rows = "".join(
        f"<tr><td>{escape(event.occurred_at)}</td><td>{escape(event.subject_kind.replace('_', ' ').title())}</td><td>{escape(event.action.replace('_', ' ').title())}</td><td>{escape(event.notes or '—')}</td><td>{escape(event.actor)}</td></tr>"
        for event in events
    )
    content = f'<div class="table-scroll" tabindex="0" role="region" aria-label="Audit events"><table class="table-compact"><thead><tr><th>When</th><th>Record type</th><th>Action</th><th>Details</th><th>Actor</th></tr></thead><tbody>{rows}</tbody></table></div>' if rows else '<div class="empty-state"><h2>No matching audit events</h2><p>No audit events match these filters.</p><a class="button secondary" href="/system-tools/audit">Clear filters</a></div>'
    return f'''<section class="page-heading split"><div><p class="eyebrow">System Tools</p><h1>Audit</h1><p>Platform-wide operational history. Entity timelines continue to show real-world dates separately.{scope_text}</p></div><a class="button secondary" href="/system-tools">Back to System Tools</a></section>
    <section class="panel filter-panel"><form method="get" action="/system-tools/audit">{scope_input}<label><span>Action</span><select name="event_type"><option value="">All actions</option>{event_options}</select></label>{kind_control}<div class="actions"><button class="button" type="submit">Apply</button><a class="button secondary" href="/system-tools/audit">Clear</a></div></form></section>
    <section class="panel">{content}</section>'''


def _options(values: tuple[str, ...], selected: str) -> str:
    return "".join(f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(value.replace("_", " ").title())}</option>' for value in values)
