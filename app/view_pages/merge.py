from html import escape

from app.entities import EntityRecord


def merge_select_page(survivor: EntityRecord, candidates: list[EntityRecord], error: str = "") -> str:
    options = "".join(f'<option value="{item.id}">{escape(item.title)}</option>' for item in candidates)
    error_html = f'<div class="warnings"><p>{escape(error)}</p></div>' if error else ""
    empty = '<p class="empty">There are no other records of this type to merge.</p>' if not candidates else ""
    form = f"""
    <form class="record-form" method="get" action="/{survivor.slug}/{survivor.id}/merge">
        <label><span>Duplicate record</span><select name="duplicate_id">{options}</select></label>
        <div class="actions"><button class="button" type="submit">Preview merge</button></div>
    </form>""" if candidates else ""
    return f"""
    <section class="page-heading"><p class="eyebrow">Data maintenance</p><h1>Merge into {escape(survivor.title)}</h1>
    <p>Select the duplicate to retire. Nothing changes until the preview is confirmed.</p></section>
    <section class="panel">{error_html}{empty}{form}</section>"""


def merge_preview_page(preview) -> str:
    rows = []
    for field in preview.fields:
        conflict = ' <span class="pill">Conflict preserved in history</span>' if field.conflict else ""
        rows.append(f"<tr><th>{escape(field.label)}</th><td>{escape(field.survivor_value) or '—'}</td><td>{escape(field.duplicate_value) or '—'}</td><td>{escape(field.result_value) or '—'}{conflict}</td></tr>")
    return f"""
    <section class="page-heading"><p class="eyebrow">Merge preview</p><h1>{escape(preview.duplicate.title)} → {escape(preview.survivor.title)}</h1>
    <p>Review the exact field and relationship effects before committing.</p></section>
    <section class="panel"><table><thead><tr><th>Field</th><th>Survivor</th><th>Duplicate</th><th>Result</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
    <section class="panel"><h2>Relationship changes</h2><p>{preview.relationships_to_repoint} relationship(s) will be reviewed and repointed; {preview.duplicate_relationships_to_remove} duplicate or self-referencing relationship(s) will be removed.</p>
    <p>The duplicate snapshot, conflicts, and prior history will remain in the survivor’s edit history.</p>
    <form method="post" action="/{preview.survivor.slug}/{preview.survivor.id}/merge"><input type="hidden" name="duplicate_id" value="{preview.duplicate.id}">
    <div class="actions"><a class="button secondary" href="/{preview.survivor.slug}/{preview.survivor.id}">Cancel</a><button class="button danger" type="submit">Confirm merge</button></div></form></section>"""
