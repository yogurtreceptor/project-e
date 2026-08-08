import json
from html import escape
from urllib.parse import urlencode


SEARCH_GROUPS = (
    ("canonical", "Canonical records"),
    ("installed", "Installed map results"),
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
    pack_status = payload.get(
        "packStatus", {"state": "unavailable", "manageUrl": "/map/packs"}
    )
    pack_available = pack_status.get("state") == "available"
    selected = payload["selections"].get(selected_key)
    map_title = "Normal local map" if pack_available else "Canonical coordinate map"
    map_description = (
        f'{escape(str(pack_status["title"]))} {escape(str(pack_status["version"]))} · '
        f'{escape(str(pack_status["coverageLabel"]))} · Local'
        if pack_available
        else "No basemap is installed; canonical positions remain usable offline."
    )
    map_assets = (
        '<link rel="stylesheet" href="/static/vendor/maplibre-6.2.0/maplibre-gl.css">'
        if pack_available
        else ""
    )

    return f"""
    {map_assets}
    <section class="map-page-heading">
        <div>
            <p class="eyebrow">Spatial workspace</p>
            <h1>Map</h1>
            <p>{place_count} canonical place{"s" if place_count != 1 else ""} represent {record_count} mapped record{"s" if record_count != 1 else ""} without requiring network access.</p>
        </div>
        <div class="actions"><a class="button secondary" href="/map/lists">Map lists</a><a class="button secondary" href="/map/packs">Manage Spatial Packs</a><a class="button secondary" href="/locations/new">Create Location</a></div>
    </section>
    <section class="map-workspace" data-map-workspace>
        <header class="map-search-region">
            <form method="get" action="/map" class="map-search-form" role="search">
                <label for="map-search-input">Search installed places and canonical records</label>
                <div class="map-search-row">
                    <input id="map-search-input" type="search" name="q" value="{escape(query)}" placeholder="Name, address, or latitude, longitude" autocomplete="off">
                    <button class="button" type="submit">Search</button>
                    <a class="button secondary" href="/map">Clear</a>
                </div>
                <label class="inline-check map-online-choice"><input type="checkbox" name="online" value="1"{online_checked}> Include optional online place results for this search</label>
                <p class="form-help">Off by default. When selected, only the entered search text is sent to OpenStreetMap Nominatim; Project E does not add canonical names, notes or Relationships.</p>
            </form>
            <div class="map-capability-stack">
                {pack_capability_status(pack_status)}
                <div class="map-capability-status{provider_class}" role="status">
                    <strong>{escape(provider_status["name"])} · {escape(provider_status["execution"])}</strong>
                    <span>{escape(provider_status["explanation"])}</span>
                    {f'<span>{escape(provider_status["attribution"])}</span>' if provider_status["requested"] else ''}
                </div>
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
                    <div data-map-details>{map_details_html(selected, payload.get("mapLists", []), map_selection_href(payload, selected_key)) if selected is not None else ''}</div>
                </section>
            </aside>

            <section class="map-canvas-panel" aria-labelledby="map-canvas-heading">
                <header class="map-command-bar">
                    <div>
                        <h2 id="map-canvas-heading">{map_title}</h2>
                        <p>{map_description}</p>
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

                <div class="eddy-map{' has-local-basemap' if pack_available else ''}" role="region" tabindex="0" aria-label="Pan and zoom {'normal local map with canonical places' if pack_available else 'canonical coordinate map'}" aria-describedby="map-keyboard-help map-map-status" data-map-stage>
                    <div class="map-basemap" data-map-basemap aria-hidden="true"></div>
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
                    {map_pack_footer(pack_status)}
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
        <div class="empty-state"><h3>No matches</h3><p>No canonical record, installed map feature, entered coordinate or enabled online result matched <strong>{escape(query)}</strong>.</p></div>
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


def map_details_html(
    selection: dict[str, object] | None,
    map_lists: list[dict[str, object]] | None = None,
    return_to: str = "/map",
) -> str:
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
    provider_feature = selection.get("providerFeature")
    if isinstance(provider_feature, dict):
        provider_metadata = (
            ("Pack version", provider_feature.get("packVersion", "")),
            ("Source layer", provider_feature.get("sourceLayer", "")),
            ("Provider feature", provider_feature.get("featureId", "")),
        )
        metadata += "".join(
            f'<li><strong>{escape(label)}</strong><span>{escape(str(value))}</span></li>'
            for label, value in provider_metadata
            if value
        )
    records = selection.get("records", [])
    if records:
        record_items = "".join(map_detail_record_html(record) for record in records)
        records_html = f'<section class="map-detail-records"><h3>Canonical records at this place</h3><ul>{record_items}</ul></section>'
    else:
        records_html = '<p class="map-detail-warning">Selection only. Browsing does not create or change a canonical Location.</p>'
    actions = provider_feature_actions(selection, map_lists or [], return_to)
    return f"""
    <header class="map-details-header"><p class="eyebrow">Selected</p><h2 id="map-details-heading">{escape(str(selection["title"]))}</h2>{address}</header>
    {coordinates}
    <ul class="map-detail-metadata">{metadata}</ul>
    {records_html}
    <div class="map-detail-actions" aria-label="Selection actions">
        {actions}
        <button class="button secondary" type="button" disabled title="Journey planning is not yet available">Directions from</button>
        <button class="button secondary" type="button" disabled title="Journey planning is not yet available">Directions to</button>
    </div>
    """


def provider_feature_actions(
    selection: dict[str, object],
    map_lists: list[dict[str, object]],
    return_to: str,
) -> str:
    if not isinstance(selection.get("providerFeature"), dict):
        return ""
    hidden = provider_feature_hidden_fields(selection)
    review = f"""
    <form method="post" action="/map/provider-location/review" class="map-detail-action-form">
        {hidden}<input type="hidden" name="return_to" value="{escape(return_to)}">
        <button class="button" type="submit">Review Save as Location</button>
    </form>
    """
    options = "".join(
        f'<option value="{int(item["id"])}">{escape(str(item["name"]))} ({int(item["memberCount"])})</option>'
        for item in map_lists
    )
    bookmark = (
        f"""
        <form method="post" action="/map/lists/add" class="map-detail-action-form map-list-add-form">
            {hidden}<input type="hidden" name="return_to" value="{escape(return_to)}">
            <label><span>Add external feature to</span><select name="list_id">{options}</select></label>
            <button class="button secondary" type="submit">Add</button>
        </form>
        """
        if options
        else ""
    )
    return review + bookmark + '<a class="button secondary" href="/map/lists">Map lists</a>'


def provider_feature_hidden_fields(selection: dict[str, object]) -> str:
    provider = selection.get("providerFeature")
    if not isinstance(provider, dict):
        return ""
    values = {
        "provider_key": provider.get("providerKey", ""),
        "feature_id": provider.get("featureId", ""),
        "feature_version": provider.get("packVersion", ""),
        "title": selection.get("title", ""),
        "description": provider.get("description", selection.get("address", "")),
        "feature_type": provider.get("featureType", "Place"),
        "source_name": provider.get("sourceName", selection.get("sourceLabel", "")),
        "source_layer": provider.get("sourceLayer", ""),
        "latitude": selection.get("latitude", ""),
        "longitude": selection.get("longitude", ""),
        "geometry_confidence": provider.get("geometryConfidence", ""),
        "formatted_address": provider.get("formattedAddress", ""),
        "address_line_1": provider.get("addressLine1", ""),
        "address_line_2": provider.get("addressLine2", ""),
        "suburb": provider.get("suburb", ""),
        "city": provider.get("city", ""),
        "state": provider.get("state", ""),
        "post_code": provider.get("postCode", ""),
        "country": provider.get("country", ""),
    }
    return "".join(
        f'<input type="hidden" name="{name}" value="{escape(str(value))}">'
        for name, value in values.items()
    )


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
    controls = []
    for view in payload["baseViews"]:
        available = bool(view["available"])
        controls.append(
            f'<label class="{"" if available else "map-unavailable-option"}"><input type="radio" name="map-base-view" value="{escape(str(view["id"]))}"'
            f'{" checked" if view.get("enabled", False) else ""}{"" if available else " disabled"}> '
            f'<span><strong>{escape(str(view["label"]))}</strong><small>{"Local · " if available else "Unavailable · "}{escape(str(view["explanation"]))}</small></span></label>'
        )
    return "".join(controls)


def canonical_layer_controls(payload: dict[str, object]) -> str:
    return "".join(
        f'<label><input type="checkbox" data-map-layer="{escape(str(layer["id"]))}"{" checked" if layer["enabled"] else ""}> <span><strong>{escape(str(layer["label"]))}</strong><small>Project E · Local canonical projection · Current</small></span></label>'
        for layer in payload["layers"]
    )


def context_layer_controls(payload: dict[str, object]) -> str:
    controls = []
    for layer in payload["contextLayers"]:
        available = bool(layer["available"])
        controls.append(
            f'<label class="{"" if available else "map-unavailable-option"}"><input type="checkbox" data-map-context-layer="{escape(str(layer["id"]))}"'
            f'{" checked" if layer.get("enabled", False) else ""}{"" if available else " disabled"}> '
            f'<span><strong>{escape(str(layer["label"]))}</strong><small>{"Local · " if available else "Unavailable · "}{escape(str(layer["explanation"]))}</small></span></label>'
        )
    return "".join(controls)


def pack_capability_status(pack: dict[str, object]) -> str:
    state = str(pack.get("state", "unavailable"))
    if state == "available":
        search_note = (
            "Installed search ready"
            if pack.get("searchState") == "available"
            else "Installed search unavailable; canonical search still works"
        )
        return f"""
        <div class="map-capability-status map-capability-local" role="status">
            <strong>{escape(str(pack["title"]))} {escape(str(pack["version"]))} · Local</strong>
            <span>{escape(str(pack["coverageLabel"]))} · {search_note}</span>
            <a href="{escape(str(pack["manageUrl"]))}">Inspect coverage, sources and versions</a>
        </div>
        """
    if state == "error":
        return f"""
        <div class="map-capability-status map-capability-error" role="alert">
            <strong>Installed map unavailable</strong><span>{escape(str(pack.get("error", "Installed pack state is invalid.")))}</span>
            <a href="{escape(str(pack["manageUrl"]))}">Inspect Spatial Packs</a>
        </div>
        """
    return f"""
    <div class="map-capability-status" role="status">
        <strong>Normal map · Not installed</strong>
        <span>Canonical coordinates remain available without tiles.</span>
        <a href="{escape(str(pack["manageUrl"]))}">Install or inspect a Spatial Pack</a>
    </div>
    """


def map_pack_footer(pack: dict[str, object]) -> str:
    if pack.get("state") != "available":
        return "<span>Basemap unavailable—no code or tiles were requested from a third party.</span>"
    return (
        f'<strong>{escape(str(pack["title"]))} {escape(str(pack["version"]))} · Local.</strong>'
        f'<span>{escape(str(pack["coverageLabel"]))} · Produced {escape(str(pack["producedAt"]))}.</span>'
        f'<span>{escape(str(pack["attribution"]))}.</span>'
        '<span data-map-render-status>Starting the local basemap renderer…</span>'
        '<span>Coordinates outside pack coverage remain visible over the coordinate grid.</span>'
    )
