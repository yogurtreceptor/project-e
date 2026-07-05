from html import escape


def portability_page(error: str = "", message: str = "") -> str:
    error_html = f'<div class="warnings"><p>{escape(error)}</p></div>' if error else ""
    message_html = f'<div class="notice"><p>{escape(message)}</p></div>' if message else ""
    return f"""<section class="page-heading"><p class="eyebrow">System Tools</p>
    <h1>Import and export</h1>
    <p>Move a complete, checksummed copy of canonical records, relationships, provenance, audit history, and stored documents.</p></section>
    {error_html}{message_html}
    <section class="panel"><h2>Export</h2>
    <p>Download a versioned ZIP bundle. Export is read-only and creates a consistent SQLite snapshot.</p>
    <a class="button" href="/system-tools/portability/export">Download export</a></section>
    <section class="panel"><h2>Import</h2>
    <p>Import requires an empty database and document store. The bundle is validated and previewed before confirmation; applying it creates a recovery backup first.</p>
    <form class="record-form" method="post" enctype="multipart/form-data" action="/system-tools/portability/preview">
      <label><span>Project E bundle</span><input type="file" name="upload" accept=".zip,application/zip" required></label>
      <div class="actions"><button class="button" type="submit">Validate and preview</button></div>
    </form></section>"""


def import_preview_page(preview, token: str) -> str:
    return f"""<section class="page-heading"><p class="eyebrow">Import preview</p>
    <h1>Confirm portable import</h1><p>The bundle passed manifest, checksum, SQLite integrity, schema, endpoint, and document checks.</p></section>
    <section class="panel"><dl class="metadata">
      <div><dt>Exported</dt><dd>{escape(preview.exported_at)}</dd></div>
      <div><dt>Entities</dt><dd>{preview.entities} ({preview.deleted_entities} recycled)</dd></div>
      <div><dt>Relationships</dt><dd>{preview.relationships} ({preview.deleted_relationships} recycled)</dd></div>
      <div><dt>Stored documents</dt><dd>{preview.documents}</dd></div>
    </dl>
    <div class="warnings"><strong>Import is consequential.</strong> It is allowed only into an empty target and will create a recovery backup before replacing local storage.</div>
    <form method="post" action="/system-tools/portability/import">
      <input type="hidden" name="token" value="{escape(token)}">
      <label class="inline-check"><input type="checkbox" name="confirm" value="yes" required> I reviewed this preview and want to import the bundle.</label>
      <div class="actions"><a class="button secondary" href="/system-tools/portability">Cancel</a><button class="button danger" type="submit">Confirm import</button></div>
    </form></section>"""
