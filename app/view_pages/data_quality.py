from html import escape


def data_quality_page(findings):
    rows = []
    for finding in findings:
        records = ", ".join(map(str, finding.entity_ids)) or "—"
        rows.append(f'<tr><td><span class="badge">{escape(finding.severity.title())}</span></td><td>{escape(finding.category.replace("_", " ").title())}</td><td>{escape(finding.explanation)}</td><td>{records}</td><td>{escape(finding.status.title())}</td></tr>')
    if rows:
        content = f'<div class="table-scroll" tabindex="0" role="region" aria-label="Data quality findings"><table class="table-compact"><thead><tr><th>Severity</th><th>Category</th><th>Explanation</th><th>Record IDs</th><th>Status</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    else:
        content = '<div class="empty-state"><h2>No data quality findings</h2><p>Current deterministic checks found no issues requiring review.</p></div>'
    return f'<section class="page-heading split"><div><p class="eyebrow">System Tools</p><h1>Data Quality Centre</h1><p>Explainable findings derived from canonical graph data.</p></div><a class="button secondary" href="/system-tools">Back to System Tools</a></section><section class="panel">{content}</section>'
