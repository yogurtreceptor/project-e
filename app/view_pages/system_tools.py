def system_tools_page() -> str:
    tools = (
        ("/search", "Search", "Find entities by fields, notes, structured filters and relationship context."),
        ("/data-quality", "Data Quality", "Review explainable integrity findings derived from canonical records."),
        ("/taxonomies", "Taxonomies", "Manage reusable Organisation classifications and Relationship types."),
        ("/recycle-bin", "Recycle Bin", "Restore deleted records or permanently remove them after confirmation."),
    )
    cards = "".join(
        f'<a class="panel system-tool-card" href="{href}"><h2>{title}</h2><p>{description}</p><span>Open tool →</span></a>'
        for href, title, description in tools
    )
    return f'<section class="page-heading"><p class="eyebrow">Platform maintenance</p><h1>System Tools</h1><p>Search, review and maintain local platform data.</p></section><section class="grid system-tools-grid">{cards}</section>'
