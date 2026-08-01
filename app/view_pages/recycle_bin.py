from html import escape

from app.entities import EntityRecord


def recycle_bin_page(records: list[EntityRecord], relationships: list = None) -> str:
    relationships = relationships or []
    rows = "".join(
        f"""<tr><td>{escape(record.title)}</td><td>{escape(record.definition.singular)}</td>
        <td>{escape(record.deleted_at)}</td><td class="row-actions">
        <form method="post" action="/recycle-bin/{record.id}/restore"><button class="link-button" type="submit">Restore</button></form>
        <a class="button quiet" href="/recycle-bin/{record.id}/permanent-delete">Permanently delete</a>
        </td></tr>"""
        for record in records
    )
    relationship_rows = "".join(
        f'''<tr><td>{escape(record.source.title)} — {escape(record.target.title)}</td><td>{escape(record.type.label)}</td><td>{escape(record.deleted_at)}</td><td class="row-actions"><form method="post" action="/recycle-bin/relationships/{record.id}/restore"><button class="link-button" type="submit">Restore</button></form></td></tr>'''
        for record in relationships
    )
    all_rows = rows + relationship_rows
    content = (
        f'<div class="table-scroll" tabindex="0" role="region" aria-label="Recycled records"><table><thead><tr><th>Name</th><th>Type</th><th>Deleted</th><th><span class="visually-hidden">Actions</span></th></tr></thead><tbody>{all_rows}</tbody></table></div>'
        if all_rows else '<div class="empty-state"><h2>Recycle Bin is empty</h2><p>Deleted records will appear here until restored or permanently removed.</p></div>'
    )
    return f"""<section class="page-heading split"><div><p class="eyebrow">System Tools</p><h1>Recycle Bin</h1>
    <p>Deleted entities and relationships are hidden throughout the platform but can be restored here. Archived records remain active platform records and do not appear here.</p></div><a class="button secondary" href="/system-tools">Back to System Tools</a></section>
    <section class="panel">{content}</section>"""


def permanent_delete_confirmation_page(record: EntityRecord, dependencies: dict[str, int]) -> str:
    relationship_count = dependencies["relationships"]
    active_relationships = dependencies.get("active_relationships", relationship_count)
    recycled_relationships = dependencies.get("recycled_relationships", 0)
    journal_count = dependencies["journal_entries"]
    warning = ""
    if relationship_count or journal_count:
        parts = []
        if relationship_count:
            relationship_detail = f"{active_relationships} active, {recycled_relationships} recycled"
            parts.append(f"{relationship_count} relationship{'s' if relationship_count != 1 else ''} ({relationship_detail})")
        if journal_count:
            parts.append(f"{journal_count} journal entr{'ies' if journal_count != 1 else 'y'}")
        warning = f'<div class="status-row warning"><strong>Dependencies will also be permanently removed:</strong> {escape(" and ".join(parts))}.</div>'
    return f"""<section class="page-heading"><h1>Permanently delete {escape(record.title)}?</h1></section>
    <section class="panel">{warning}<p>This cannot be undone. The record, its relationships, and dependent data will be removed. Audit history will be preserved.</p>
    <form method="post" action="/recycle-bin/{record.id}/permanent-delete">
      <label class="inline-check"><input type="checkbox" name="confirm" value="yes" required> I understand this deletion is permanent.</label>
      <div class="actions"><button class="button danger" type="submit">Permanently delete</button><a class="button secondary" href="/recycle-bin">Cancel</a></div>
    </form></section>"""
