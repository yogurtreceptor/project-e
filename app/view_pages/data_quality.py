from html import escape

def data_quality_page(findings):
    rows = []
    for finding in findings:
        records = ", ".join(map(str, finding.entity_ids)) or "—"
        rows.append(f"<tr><td>{escape(finding.severity)}</td><td>{escape(finding.category.replace('_', ' '))}</td><td>{escape(finding.explanation)}</td><td>{records}</td><td>{escape(finding.status)}</td><td>Review · Open record · Ignore · Mark intentional</td></tr>")
    body = "".join(rows) or '<tr><td colspan="6">No findings.</td></tr>'
    return f'<section class="page-heading split"><div><p class="eyebrow">System Tools</p><h1>Data Quality Centre</h1><p>Explainable findings derived from canonical graph data.</p></div><a class="button secondary" href="/system-tools">Back to System Tools</a></section><section class="panel"><table><thead><tr><th>Severity</th><th>Category</th><th>Explanation</th><th>Records</th><th>Status</th><th>Actions</th></tr></thead><tbody>{body}</tbody></table></section>'
