import json
from html import escape


def map_page(payload: dict[str, object], focused_entity_id: str = "") -> str:
    data_json = json.dumps(payload).replace("</", "<\\/")
    focused_json = json.dumps(str(focused_entity_id))
    layer_controls = "".join(
        f'<label class="inline-check"><input type="checkbox" data-layer-toggle="{escape(layer["id"])}"{" checked" if layer.get("enabled") else ""}> {escape(layer["label"])}</label>'
        for layer in payload["layers"]
    )
    marker_count = len(payload["markers"])
    empty = '<p class="empty map-empty">No entities with coordinates yet.</p>' if marker_count == 0 else ""
    marker_links = "".join(
        f'<li><a href="{escape(marker["url"])}">{escape(marker["title"])}</a><span>{escape(marker["entityLabel"])} at {escape(marker["locationTitle"])}</span></li>'
        for marker in payload["markers"]
    )
    marker_list = f'<section class="panel map-marker-list"><h2>Mapped entities</h2><ul>{marker_links}</ul></section>' if marker_links else ""
    return f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <section class="page-heading split">
        <div>
            <h1>Map</h1>
            <p>{marker_count} mapped entities from canonical records and location relationships.</p>
        </div>
        <a class="button" href="/locations/new">Create Location</a>
    </section>
    <section class="panel map-toolbar">
        <div class="map-layers">{layer_controls}</div>
    </section>
    <section class="map-shell">
        <div id="eddy-map" class="eddy-map" aria-label="Entity map"></div>
        {empty}
    </section>
    {marker_list}
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    (() => {{
        const payload = {data_json};
        const focusedEntityId = {focused_json};
        const mapElement = document.getElementById('eddy-map');
        if (!mapElement || !window.L) return;
        const center = payload.defaultCenter;
        const map = L.map(mapElement).setView([center.latitude, center.longitude], center.zoom);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);
        const layerGroups = new Map();
        payload.layers.forEach((layer) => {{
            const group = L.layerGroup();
            if (layer.enabled) group.addTo(map);
            layerGroups.set(layer.id, group);
        }});
        const bounds = [];
        const visibleBounds = [];
        payload.markers.forEach((item) => {{
            const marker = L.marker([item.latitude, item.longitude]);
            marker.bindPopup(`
                <strong>${{escapeHtml(item.title)}}</strong><br>
                <span>${{escapeHtml(item.entityLabel)}} at ${{escapeHtml(item.locationTitle)}}</span><br>
                <small>${{escapeHtml(item.address || '')}}</small><br>
                <a href="${{item.url}}">Open entity</a>
            `);
            const group = layerGroups.get(item.layerId);
            if (group) group.addLayer(marker);
            bounds.push([item.latitude, item.longitude]);
            const layer = payload.layers.find((candidate) => candidate.id === item.layerId);
            if (!layer || layer.enabled) visibleBounds.push([item.latitude, item.longitude]);
            if (focusedEntityId && String(item.entityId) === focusedEntityId) marker.openPopup();
        }});
        if (visibleBounds.length) map.fitBounds(visibleBounds, {{ padding: [28, 28], maxZoom: 15 }});
        else if (bounds.length) map.fitBounds(bounds, {{ padding: [28, 28], maxZoom: 15 }});
        document.querySelectorAll('[data-layer-toggle]').forEach((control) => {{
            control.addEventListener('change', () => {{
                const group = layerGroups.get(control.dataset.layerToggle);
                if (!group) return;
                if (control.checked) group.addTo(map);
                else map.removeLayer(group);
            }});
        }});
        function escapeHtml(value) {{
            return String(value).replace(/[&<>'"]/g, (char) => ({{
                '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
            }}[char]));
        }}
    }})();
    </script>
    """
