from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityRecord


def dashboard_page(counts: dict[str, int], relationship_count: int, recent_entities: list[EntityRecord], favourite_entities: list[EntityRecord]) -> str:
    cards = []
    for definition in ENTITY_DEFINITIONS:
        count = counts.get(definition.type, 0)
        cards.append(
            f"""
            <section class="panel entity-card">
                <div>
                    <h2>{escape(definition.plural)}</h2>
                    <p>{count} records</p>
                </div>
                <div class="actions">
                    <a class="button secondary" href="/{definition.slug}">Browse</a>
                    <a class="button" href="/{definition.slug}/new">Create</a>
                </div>
            </section>
            """
        )
    cards.append(
        f"""
        <section class="panel entity-card">
            <div>
                <h2>Relationships</h2>
                <p>{relationship_count} records</p>
            </div>
            <div class="actions">
                <a class="button secondary" href="/relationships">Browse</a>
            </div>
        </section>
        """
    )

    return """
    <section class="page-heading">
        <h1>Operation Eddy</h1>
        <p>Local-first structured information centred on entities and relationships.</p>
    </section>
    <section class="panel dashboard-search">
        <form method="get" action="/search">
            <input name="q" placeholder="Search people, organisations, locations, notes and relationships">
            <button class="button" type="submit">Search</button>
        </form>
    </section>
    <div class="grid">""" + "".join(cards) + "</div>" + dashboard_discovery_sections(recent_entities, favourite_entities)


def dashboard_discovery_sections(recent_entities: list[EntityRecord], favourite_entities: list[EntityRecord]) -> str:
    return f"""
    <div class="dashboard-discovery">
        <section class="panel">
            <div class="section-heading split">
                <h2>Recent Entities</h2>
                <a href="/search">Browse all</a>
            </div>
            {entity_link_list(recent_entities, 'No recently viewed entities yet.')}
        </section>
        <section class="panel">
            <div class="section-heading split">
                <h2>Favourites</h2>
                <a href="/search?favourites=1">View favourites</a>
            </div>
            {entity_link_list(favourite_entities, 'No favourites yet.')}
        </section>
    </div>
    """


def entity_link_list(records: list[EntityRecord], empty_text: str) -> str:
    if not records:
        return f'<p class="empty">{escape(empty_text)}</p>'
    items = "".join(
        f'<li><a href="/{record.slug}/{record.id}">{escape(record.title)}</a><span>{escape(record.definition.singular)}</span></li>'
        for record in records
    )
    return f'<ul class="entity-link-list">{items}</ul>'


def favourite_form(record: EntityRecord) -> str:
    next_value = "0" if record.is_favourite else "1"
    label = "Unfavourite" if record.is_favourite else "Favourite"
    button_class = "button secondary favourite active" if record.is_favourite else "button secondary favourite"
    return f"""
    <form method="post" action="/{record.slug}/{record.id}/favourite">
        <input type="hidden" name="is_favourite" value="{next_value}">
        <button class="{button_class}" type="submit">{label}</button>
    </form>
    """
