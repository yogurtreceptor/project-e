from html import escape

from app.entities import ENTITY_DEFINITIONS


def taxonomies_page(entries_by_key: dict, error: str = "") -> str:
    error_html = f'<div class="errors"><p>{escape(error)}</p></div>' if error else ""
    sections = []
    for taxonomy_key, title in (("organisation_classification", "Organisation classifications"), ("relationship_type", "Relationship types")):
        entries = entries_by_key[taxonomy_key]
        rows = []
        for entry in entries:
            indent = "&nbsp;&nbsp;&nbsp;" * entry.depth
            state = " <span class=\"tag\">Archived</span>" if not entry.active else ""
            action = "" if not entry.active else f'<form method="post" action="/taxonomies/{entry.id}/archive" onsubmit="return confirm(\'Archive this taxonomy entry? Existing records will retain it.\')"><button class="link-button" type="submit">Archive</button></form>'
            rows.append(f'<tr data-search-text="{escape(entry.path.casefold())}"><td>{indent}{escape(entry.label)}{state}</td><td>{escape(entry.path)}</td><td>{action}</td></tr>')
        parent_options = ['<option value="">Top-level Type</option>'] + [f'<option value="{e.id}">{escape(e.path)}</option>' for e in entries if e.active and e.depth < 2]
        relationship_fields = ""
        if taxonomy_key == "relationship_type":
            entity_options = "".join(f'<option value="{d.type}">{escape(d.singular)}</option>' for d in ENTITY_DEFINITIONS)
            relationship_fields = f'''<div class="taxonomy-relationship-fields"><label><span>Source entity type</span><select name="source_entity_type">{entity_options}</select></label><label><span>Target entity type</span><select name="target_entity_type">{entity_options}</select></label><label class="inline-check"><input type="checkbox" name="directional" value="1" checked> Directional</label><label><span>Source role</span><input name="source_role" required></label><label><span>Target role</span><input name="target_role" required></label><label><span>Source display phrase</span><input name="source_label" placeholder="employee of" required></label><label><span>Inverse display phrase</span><input name="target_label" placeholder="employer of" required></label></div>'''
        sections.append(f'''<section class="panel taxonomy-section"><h2>{escape(title)}</h2><label><span>Search paths</span><input type="search" data-taxonomy-table-search placeholder="Type to filter..."></label><table><thead><tr><th>Entry</th><th>Full path</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table><details><summary>Add taxonomy entry</summary><form class="record-form" method="post" action="/taxonomies/new"><input type="hidden" name="taxonomy_key" value="{taxonomy_key}"><label><span>Parent</span><select name="parent_id">{''.join(parent_options)}</select></label><label><span>Label</span><input name="label" required></label>{relationship_fields}<button class="button" type="submit">Add entry</button></form></details></section>''')
    return f'''<section class="page-heading"><p class="eyebrow">Reusable classifications</p><h1>Taxonomies</h1><p>Manage three-level paths. Archived entries remain visible on existing records.</p></section>{error_html}{''.join(sections)}<script>(()=>{{document.querySelectorAll('[data-taxonomy-table-search]').forEach(q=>q.addEventListener('input',()=>{{const v=q.value.trim().toLocaleLowerCase();q.closest('section').querySelectorAll('tbody tr').forEach(r=>r.hidden=!!v&&!r.dataset.searchText.includes(v));}}));}})();</script>'''
