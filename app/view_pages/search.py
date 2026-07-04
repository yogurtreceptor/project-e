from html import escape

from app.entities import ENTITY_DEFINITIONS
from app.structured_filters import FILTERS


def search_page(query: str, entity_type: str, favourites_only: bool, results: list[dict[str, object]], filter_key: str = "", filter_value: str = "") -> str:
    type_options = ['<option value="">All entity types</option>']
    for definition in ENTITY_DEFINITIONS:
        selected = " selected" if definition.type == entity_type else ""
        type_options.append(f'<option value="{definition.type}"{selected}>{escape(definition.plural)}</option>')
    checked = " checked" if favourites_only else ""
    filter_options = ['<option value="">No structured filter</option>']
    for item in FILTERS:
        selected = " selected" if item.key == filter_key else ""
        filter_options.append(f'<option value="{item.key}"{selected}>{escape(item.label)}</option>')
    if results:
        cards = "".join(search_result_card(result) for result in results)
    else:
        cards = '<p class="empty">No matching entities yet.</p>'
    return f"""
    <section class="page-heading split">
        <div><p class="eyebrow">System Tools</p><h1>Search</h1>
        <p>Find entities by their fields, notes and relationship context.</p></div>
        <a class="button secondary" href="/system-tools">Back to System Tools</a>
    </section>
    <section class="panel search-panel">
        <form method="get" action="/search">
            <input name="q" value="{escape(query)}" placeholder="Search entities and relationships">
            <select name="type">{''.join(type_options)}</select>
            <select name="filter">{''.join(filter_options)}</select>
            <input name="filter_value" value="{escape(filter_value)}" placeholder="Month or year (when required)">
            <label class="inline-check"><input type="checkbox" name="favourites" value="1"{checked}> Favourites only</label>
            <button class="button" type="submit">Search</button>
            <a class="button secondary" href="/search">Clear</a>
        </form>
    </section>
    <section class="search-results">{cards}</section>
    """


def search_result_card(result: dict[str, object]) -> str:
    entity = result["entity"]
    matched_relationships = result["matched_relationships"]
    relationship_count = result["relationship_count"]
    relationship_html = ""
    if matched_relationships:
        relationship_items = "".join(
            f'<li><a href="/relationships/{relationship.id}">{escape(relationship.label_from(entity.id))}</a> <a href="/{relationship.other_entity(entity.id).slug}/{relationship.other_entity(entity.id).id}">{escape(relationship.other_entity(entity.id).title)}</a></li>'
            for relationship in matched_relationships[:4]
        )
        relationship_html = f'<div class="matched-relationships"><strong>Relationship matches</strong><ul>{relationship_items}</ul></div>'
    favourite = '<span class="pill">Favourite</span>' if entity.is_favourite else ""
    return f"""
    <article class="panel search-result-card">
        <div>
            <p class="eyebrow">{escape(entity.definition.singular)}</p>
            <h2><a href="/{entity.slug}/{entity.id}">{escape(entity.title)}</a></h2>
            <p>{escape(entity.notes) if entity.notes else 'No notes yet.'}</p>
            <div class="result-meta">{favourite}<span>{relationship_count} relationships</span></div>
        </div>
        {relationship_html}
    </article>
    """
