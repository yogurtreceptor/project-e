from html import escape

from app.entities import ENTITY_DEFINITIONS


TAXONOMY_SECTIONS = (
    ("organisation_classification", "Organisation classifications", "Reusable paths applied to Organisation records."),
    ("relationship_type", "Relationship types", "Paths plus direction and inverse-label behavior used by relationships."),
)


def taxonomies_page(entries_by_key: dict, error: str = "") -> str:
    error_html = f'<div class="errors"><p>{escape(error)}</p></div>' if error else ""
    sections = [taxonomy_section(key, title, description, entries_by_key.get(key, [])) for key, title, description in TAXONOMY_SECTIONS]
    return f"""
    <section class="page-heading split">
      <div><p class="eyebrow">System Tools</p><h1>Taxonomies</h1><p>Manage reusable three-level classification paths. Archived branches remain visible on existing records.</p></div>
      <a class="button secondary" href="/system-tools">Back to System Tools</a>
    </section>
    {error_html}
    <div class="taxonomy-management">{''.join(sections)}</div>
    {taxonomy_management_script()}
    """


def taxonomy_section(key: str, title: str, description: str, entries: list) -> str:
    active_count = sum(entry.active for entry in entries)
    archived_count = len(entries) - active_count
    rows = "".join(taxonomy_entry_row(entry) for entry in entries)
    if not rows:
        rows = '<div class="taxonomy-manager-empty">No taxonomy entries yet. Add the first Type below.</div>'
    relationship_fields = relationship_definition_fields() if key == "relationship_type" else ""
    parent_options = ['<option value="">Top-level Type</option>'] + [
        f'<option value="{entry.id}">{escape(entry.path)}</option>'
        for entry in entries if entry.active and entry.depth < 2
    ]
    return f"""
    <section class="panel taxonomy-manager" data-taxonomy-manager>
      <header class="taxonomy-manager-header">
        <div><h2>{escape(title)}</h2><p>{escape(description)}</p></div>
        <div class="taxonomy-counts"><span>{active_count} active</span><span>{archived_count} archived</span></div>
      </header>
      <div class="taxonomy-manager-toolbar">
        <label><span>Filter {escape(title.lower())}</span><input type="search" data-taxonomy-table-search placeholder="Search labels or complete paths..."></label>
        <label class="inline-check taxonomy-archive-toggle"><input type="checkbox" data-taxonomy-show-archived> Show archived</label>
      </div>
      <div class="taxonomy-tree" data-taxonomy-tree>{rows}</div>
      <p class="taxonomy-manager-empty" data-taxonomy-no-match hidden>No entries match this filter.</p>
      <details class="taxonomy-create-panel">
        <summary>Add {escape(title.rstrip('s').lower())}</summary>
        <form class="record-form" method="post" action="/taxonomies/new">
          <input type="hidden" name="taxonomy_key" value="{escape(key)}">
          <div class="taxonomy-create-basics">
            <label><span>Parent path</span><select name="parent_id">{''.join(parent_options)}</select></label>
            <label><span>Entry label</span><input name="label" required placeholder="Enter a concise label"></label>
          </div>
          <p class="field-help">Choose no parent for a Type, a Type for a Subtype, or a Subtype for a Specific subtype.</p>
          {relationship_fields}
          <div class="actions"><button class="button" type="submit">Add entry</button></div>
        </form>
      </details>
    </section>
    """


def taxonomy_entry_row(entry) -> str:
    archived = not entry.active
    status = '<span class="status-badge archived">Archived</span>' if archived else '<span class="status-badge active">Active</span>'
    action = "" if archived else (
        f'<form method="post" action="/taxonomies/{entry.id}/archive" '
        f'onsubmit="return confirm(\'Archive this taxonomy entry? Existing records will retain it.\')">'
        '<button class="link-button" type="submit">Archive</button></form>'
    )
    return f"""
    <div class="taxonomy-tree-row{' is-archived' if archived else ''}" data-taxonomy-row
         data-archived="{'true' if archived else 'false'}" data-search-text="{escape(entry.path.casefold())}"
         style="--taxonomy-depth:{entry.depth}">
      <div class="taxonomy-tree-entry"><span class="taxonomy-tree-branch" aria-hidden="true"></span><strong>{escape(entry.label)}</strong><span class="taxonomy-level">{('Type', 'Subtype', 'Specific subtype')[entry.depth]}</span></div>
      <div class="taxonomy-tree-path">{escape(entry.path)}</div>
      <div class="taxonomy-tree-status">{status}</div>
      <div class="taxonomy-tree-action">{action}</div>
    </div>
    """


def relationship_definition_fields() -> str:
    entity_options = "".join(f'<option value="{definition.type}">{escape(definition.singular)}</option>' for definition in ENTITY_DEFINITIONS)
    return f"""
    <fieldset class="taxonomy-relationship-fields"><legend>Relationship behavior</legend>
      <p class="field-help">Define the canonical direction and the role shown from each endpoint.</p>
      <div class="taxonomy-create-basics"><label><span>Source entity type</span><select name="source_entity_type">{entity_options}</select></label><label><span>Target entity type</span><select name="target_entity_type">{entity_options}</select></label></div>
      <label class="inline-check"><input type="checkbox" name="directional" value="1" checked> Source and target roles differ</label>
      <div class="taxonomy-label-grid"><label><span>Source role</span><input name="source_role" placeholder="Employee" required></label><label><span>Target role</span><input name="target_role" placeholder="Employer" required></label><label><span>Source display phrase</span><input name="source_label" placeholder="employee of" required></label><label><span>Inverse display phrase</span><input name="target_label" placeholder="employer of" required></label></div>
    </fieldset>
    """


def taxonomy_management_script() -> str:
    return """
    <script>(()=>{document.querySelectorAll('[data-taxonomy-manager]').forEach(manager=>{
      const search=manager.querySelector('[data-taxonomy-table-search]');
      const showArchived=manager.querySelector('[data-taxonomy-show-archived]');
      const rows=[...manager.querySelectorAll('[data-taxonomy-row]')];
      const noMatch=manager.querySelector('[data-taxonomy-no-match]');
      const filter=()=>{const query=search.value.trim().toLocaleLowerCase();let visible=0;rows.forEach(row=>{const matchesText=!query||row.dataset.searchText.includes(query);const matchesArchive=showArchived.checked||row.dataset.archived!=='true';row.hidden=!(matchesText&&matchesArchive);if(!row.hidden)visible+=1;});if(noMatch)noMatch.hidden=visible!==0;};
      search.addEventListener('input',filter);showArchived.addEventListener('change',filter);filter();
    });})();</script>
    """
