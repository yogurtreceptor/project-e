import json
from html import escape
from urllib.parse import urlencode


SEARCH_GROUPS = (
    ("canonical", "Canonical records"),
    ("coordinates", "Entered coordinates"),
    ("online", "Online provider results"),
)


def map_page(
    payload: dict[str, object],
    focused_entity_id: str = "",
    selected_key: str = "",
) -> str:
    selected_key = selected_key if selected_key in payload["selections"] else ""
    if not selected_key and str(focused_entity_id).isdigit():
        selected_key = selection_for_entity(payload, int(focused_entity_id))
    payload = dict(payload)
    payload["selectedKey"] = selected_key
    data_json = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")

    place_count = len(payload["places"])
    record_count = sum(int(place["recordCount"]) for place in payload["places"])
    query = str(payload["query"])
    online_checked = " checked" if payload["providerStatus"]["requested"] else ""
    provider_status = payload["providerStatus"]
    provider_class = " map-capability-error" if provider_status["state"] == "error" else ""
    selected = payload["selections"].get(selected_key)

    return f"""
    <section class="map-page-heading">
        <div>
            <p class="eyebrow">Spatial workspace</p>
            <h1>Map</h1>
            <p>{place_count} canonical place{"s" if place_count != 1 else ""} represent {record_count} mapped record{"s" if record_count != 1 else ""} without requiring network access.</p>
        </div>
        <a class="button secondary" href="/locations/new">Create Location</a>
    </section>
    <section class="map-workspace" data-map-workspace>
        <header class="map-search-region">
            <form method="get" action="/map" class="map-search-form" role="search">
                <label for="map-search-input">Search places and canonical records</label>
                <div class="map-search-row">
                    <input id="map-search-input" type="search" name="q" value="{escape(query)}" placeholder="Name, address, or latitude, longitude" autocomplete="off">
                    <button class="button" type="submit">Search</button>
                    <a class="button secondary" href="/map">Clear</a>
                </div>
                <label class="inline-check map-online-choice"><input type="checkbox" name="online" value="1"{online_checked}> Include optional online place results for this search</label>
                <p class="form-help">Off by default. When selected, only the entered search text is sent to OpenStreetMap Nominatim; Project E does not add canonical names, notes or Relationships.</p>
            </form>
            <div class="map-capability-status{provider_class}" role="status">
                <strong>{escape(provider_status["name"])} · {escape(provider_status["execution"])}</strong>
                <span>{escape(provider_status["explanation"])}</span>
                {f'<span>{escape(provider_status["attribution"])}</span>' if provider_status["requested"] else ''}
            </div>
        </header>

        <div class="map-workspace-body">
            <aside class="map-sidebar" aria-label="Map results and details" data-map-sidebar>
                <section data-map-pane="results"{'' if selected is None else ' hidden'}>
                    {search_results_html(payload)}
                    {textual_places_html(payload)}
                </section>
                <section data-map-pane="details" aria-labelledby="map-details-heading"{'' if selected is not None else ' hidden'}>
                    <button class="button secondary map-back-button" type="button" data-map-back>Back to {"results" if query else "places"}</button>
                    <div data-map-details>{map_details_html(selected) if selected is not None else ''}</div>
                </section>
            </aside>

            <section class="map-canvas-panel" aria-labelledby="map-canvas-heading">
                <header class="map-command-bar">
                    <div>
                        <h2 id="map-canvas-heading">Canonical coordinate map</h2>
                        <p>No basemap is installed; canonical positions remain usable offline.</p>
                    </div>
                    <div class="map-command-actions" aria-label="Map controls">
                        <button type="button" class="button secondary map-icon-button" data-map-zoom-in aria-label="Zoom in" title="Zoom in">+</button>
                        <button type="button" class="button secondary map-icon-button" data-map-zoom-out aria-label="Zoom out" title="Zoom out">−</button>
                        <button type="button" class="button secondary" data-map-reset>Gold Coast</button>
                        <button type="button" class="button secondary" data-map-clear-selection{'' if selected is not None else ' hidden'}>Clear selection</button>
                        <button type="button" class="button secondary" data-map-toggle-sidebar aria-expanded="true">Hide sidebar</button>
                    </div>
                </header>

                <details class="map-layer-menu">
                    <summary>Layers and map availability</summary>
                    <div class="map-layer-groups">
                        <fieldset>
                            <legend>Base view</legend>
                            {base_view_controls(payload)}
                        </fieldset>
                        <fieldset>
                            <legend>Canonical records</legend>
                            {canonical_layer_controls(payload)}
                        </fieldset>
                        <fieldset>
                            <legend>Provider and workflow overlays</legend>
                            {context_layer_controls(payload)}
                        </fieldset>
                    </div>
                </details>

                <div class="eddy-map" role="region" tabindex="0" aria-label="Pan and zoom canonical coordinate map" aria-describedby="map-keyboard-help map-map-status" data-map-stage>
                    <div class="map-coordinate-grid" aria-hidden="true"></div>
                    <div class="map-pin-layer" data-map-pin-layer></div>
                    <p class="map-loading-state" data-map-loading role="status">Loading canonical places for this viewport…</p>
                    <div class="map-compass" aria-hidden="true"><span>N</span><i></i></div>
                </div>
                <p id="map-keyboard-help" class="map-keyboard-help">Keyboard: focus the map, use arrow keys to pan, plus or minus to zoom, and Home to return to Gold Coast. Tab reaches pins. Blank map space never creates a pin.</p>
                <div class="map-legend" aria-label="Map symbol legend">
                    <span><i class="map-legend-symbol map-legend-place">◆</i> Canonical place</span>
                    <span><i class="map-legend-symbol map-legend-selected">★</i> Selected place</span>
                    <span><i class="map-legend-symbol map-legend-cluster">3</i> Multiple nearby places</span>
                </div>
                <footer id="map-map-status" class="map-attribution-status">
                    <strong>Local canonical overlay.</strong>
                    <span data-map-viewport-status>Viewport data loads only from this Project E server.</span>
                    <span>Basemap unavailable—no code or tiles were requested from a third party.</span>
                </footer>
            </section>
        </div>
    </section>
    <script id="map-workspace-data" type="application/json">{data_json}</script>
    <script src="/static/map-workspace.js" defer></script>
    """


def selection_for_entity(payload: dict[str, object], entity_id: int) -> str:
    for place in payload["places"]:
        if any(int(record["entityId"]) == entity_id for record in place["records"]):
            return str(place["id"])
    key = f"entity:{entity_id}"
    return key if key in payload["selections"] else ""


def map_selection_href(payload: dict[str, object], selection_key: str) -> str:
    values = {"selected": selection_key}
    if payload["query"]:
        values["q"] = str(payload["query"])
    if payload["providerStatus"]["requested"]:
        values["online"] = "1"
    return f"/map?{urlencode(values)}"


def search_results_html(payload: dict[str, object]) -> str:
    query = str(payload["query"])
    results = payload["searchResults"]
    if not query:
        return "<header class=\"map-sidebar-heading\"><p class=\"eyebrow\">Browse</p><h2>Canonical places</h2><p>Select one place without changing its records.</p></header>"
    if not results:
        return f"""
        <header class="map-sidebar-heading"><p class="eyebrow">Results</p><h2>Search results</h2></header>
        <div class="empty-state"><h3>No matches</h3><p>No canonical record, entered coordinate or enabled online result matched <strong>{escape(query)}</strong>.</p></div>
        """
    sections = []
    for group_id, label in SEARCH_GROUPS:
        grouped = [result for result in results if result["group"] == group_id]
        if not grouped:
            continue
        items = "".join(search_result_item(payload, result) for result in grouped)
        sections.append(
            f'<section class="map-result-group" aria-labelledby="map-results-{group_id}"><h3 id="map-results-{group_id}">{label}</h3><ol>{items}</ol></section>'
        )
    return f"""
    <header class="map-sidebar-heading"><p class="eyebrow">Results</p><h2>Search results</h2><p>{len(results)} stable result{"s" if len(results) != 1 else ""}. Panning and zooming do not rerun this search.</p></header>
    {''.join(sections)}
    """


def search_result_item(payload: dict[str, object], result: dict[str, object]) -> str:
    href = map_selection_href(payload, str(result["selectionKey"]))
    return f"""
    <li>
        <a href="{escape(href)}" data-map-selection="{escape(str(result['selectionKey']))}" data-map-latitude="{escape(str(result['latitude'] if result['latitude'] is not None else ''))}" data-map-longitude="{escape(str(result['longitude'] if result['longitude'] is not None else ''))}">
            <strong>{escape(str(result["title"]))}</strong>
            <span>{escape(str(result["typeLabel"]))}</span>
            <small>{escape(str(result["sourceLabel"]))} · {escape(str(result["coverageState"]))}</small>
        </a>
    </li>
    """


def textual_places_html(payload: dict[str, object]) -> str:
    places = payload["places"]
    if not places:
        return '<div class="empty-state map-place-empty"><h3>No mapped canonical places</h3><p>Add a representative point to a Location to show it here.</p></div>'
    items = "".join(textual_place_item(payload, place) for place in places)
    label = "All mapped canonical places" if payload["query"] else "Mapped canonical places"
    return f"""
    <details class="map-text-alternative"{' open' if not payload['query'] else ''}>
        <summary>{label} ({len(places)})</summary>
        <p class="form-help">Text alternative to every canonical pin and grouped record on the map.</p>
        <ol>{items}</ol>
    </details>
    """


def textual_place_item(payload: dict[str, object], place: dict[str, object]) -> str:
    href = map_selection_href(payload, str(place["id"]))
    record_groups: dict[str, list[dict[str, object]]] = {}
    for record in place["records"]:
        record_groups.setdefault(str(record["entityLabel"]), []).append(record)
    records_html = "".join(
        textual_record_group_html(label, records)
        for label, records in record_groups.items()
    )
    return f"""
    <li class="map-text-place">
        <a href="{escape(href)}" data-map-selection="{escape(str(place['id']))}" data-map-latitude="{place['latitude']}" data-map-longitude="{place['longitude']}"><strong>{escape(str(place["title"]))}</strong></a>
        <span>{escape(str(place["address"])) if place["address"] else format_coordinates(place)}</span>
        <details><summary>{place["recordCount"]} grouped record{"s" if int(place["recordCount"]) != 1 else ""}</summary><ul>{records_html}</ul></details>
    </li>
    """


def textual_record_group_html(
    label: str, records: list[dict[str, object]]
) -> str:
    items = []
    for record in records:
        multiple = (
            f' <span>· shown at {record["placeCount"]} places</span>'
            if int(record["placeCount"]) > 1
            else ""
        )
        items.append(
            f'<li><a href="{escape(str(record["url"]))}">{escape(str(record["title"]))}</a>{multiple}</li>'
        )
    return f'<li><strong>{escape(label)}</strong><ul>{"".join(items)}</ul></li>'


def map_details_html(selection: dict[str, object] | None) -> str:
    if selection is None:
        return ""
    address = f'<p class="map-detail-address">{escape(str(selection["address"]))}</p>' if selection.get("address") else ""
    coordinates = (
        f'<p class="map-detail-coordinates"><strong>Coordinates</strong> {format_coordinates(selection)}</p>'
        if selection.get("latitude") is not None and selection.get("longitude") is not None
        else '<p class="map-detail-warning"><strong>Not mapped.</strong> This canonical record has no current representative point or Location projection.</p>'
    )
    metadata = "".join(
        f'<li><strong>{escape(label)}</strong><span>{escape(str(value))}</span></li>'
        for label, value in (
            ("Source", selection.get("sourceLabel", "")),
            ("Coverage", selection.get("coverageState", "")),
            ("Geometry confidence", selection.get("geometryConfidence", "")),
            ("Geometry source", selection.get("geometrySource", "")),
        )
        if value
    )
    records = selection.get("records", [])
    if records:
        record_items = "".join(map_detail_record_html(record) for record in records)
        records_html = f'<section class="map-detail-records"><h3>Canonical records at this place</h3><ul>{record_items}</ul></section>'
    else:
        records_html = '<p class="map-detail-warning">Selection only. Browsing does not create or change a canonical Location.</p>'
    return f"""
    <header class="map-details-header"><p class="eyebrow">Selected</p><h2 id="map-details-heading">{escape(str(selection["title"]))}</h2>{address}</header>
    {coordinates}
    <ul class="map-detail-metadata">{metadata}</ul>
    {records_html}
    <div class="map-detail-actions" aria-label="Selection actions">
        <button class="button secondary" type="button" disabled title="Journey planning is not yet available">Directions from</button>
        <button class="button secondary" type="button" disabled title="Journey planning is not yet available">Directions to</button>
    </div>
    """


def map_detail_record_html(record: dict[str, object]) -> str:
    placement = (
        f' · shown at {record["placeCount"]} places'
        if int(record.get("placeCount", 1)) > 1
        else ""
    )
    return f'<li><a href="{escape(str(record["url"]))}"><strong>{escape(str(record["title"]))}</strong></a><span>{escape(str(record["entityLabel"]))}{placement}</span></li>'


def format_coordinates(item: dict[str, object]) -> str:
    return f'{float(item["latitude"]):.6f}, {float(item["longitude"]):.6f}'


def base_view_controls(payload: dict[str, object]) -> str:
    return "".join(
        f'<label class="map-unavailable-option"><input type="radio" name="map-base-view" value="{escape(str(view["id"]))}" disabled> <span><strong>{escape(str(view["label"]))}</strong><small>Unavailable · {escape(str(view["explanation"]))}</small></span></label>'
        for view in payload["baseViews"]
    )


def canonical_layer_controls(payload: dict[str, object]) -> str:
    return "".join(
        f'<label><input type="checkbox" data-map-layer="{escape(str(layer["id"]))}"{" checked" if layer["enabled"] else ""}> <span><strong>{escape(str(layer["label"]))}</strong><small>Project E · Local canonical projection · Current</small></span></label>'
        for layer in payload["layers"]
    )


def context_layer_controls(payload: dict[str, object]) -> str:
    return "".join(
        f'<label class="map-unavailable-option"><input type="checkbox" disabled> <span><strong>{escape(str(layer["label"]))}</strong><small>Unavailable · {escape(str(layer["explanation"]))}</small></span></label>'
        for layer in payload["contextLayers"]
    )
