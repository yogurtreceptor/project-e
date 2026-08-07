"""Top-level HTTP route map for the server-rendered application."""

from urllib.parse import parse_qs, urlparse

from app import views
from app.entities import DEFINITIONS_BY_SLUG


def route_request(handler) -> None:
    parsed = urlparse(handler.path)
    parts = [part for part in parsed.path.split("/") if part]
    query = {
        key: ",".join(values) if key == "calendars" else values[0]
        for key, values in parse_qs(parsed.query).items()
    }

    if parsed.path.startswith("/static/"):
        handler.serve_static(parsed.path.removeprefix("/static/"))
        return
    if not parts:
        handler.handle_dashboard()
        return
    if parts[0] == "search":
        handler.handle_search(query)
        return
    if parts[0] == "system-tools" and len(parts) == 1:
        handler.respond_page(
            "System Tools", views.system_tools_page(), active_slug="system-tools"
        )
        return
    if parts[:2] == ["system-tools", "audit"] and len(parts) == 2:
        handler.handle_system_audit(query)
        return
    if parts[:2] == ["system-tools", "jobs"]:
        handler.route_scheduled_jobs(parts)
        return
    if parts[:2] == ["system-tools", "automation"]:
        handler.route_automation(parts)
        return
    if parts[:2] == ["system-tools", "portability"]:
        handler.handle_portability(parts)
        return
    if parts[0] == "timeline":
        handler.handle_timeline(query)
        return
    if parts[0] == "inbox":
        handler.route_inbox_request(parts, query)
        return
    if parts[0] == "recycle-bin":
        handler.route_recycle_bin_request(parts)
        return
    if parts[0] == "data-quality":
        handler.handle_data_quality()
        return
    if parts == ["map", "packs"] and handler.command == "GET":
        handler.handle_spatial_pack_manager(query)
        return
    if parts == ["map", "packs", "preview"] and handler.command == "POST":
        handler.handle_spatial_pack_preview()
        return
    if parts == ["map", "packs", "activate"] and handler.command == "POST":
        handler.handle_spatial_pack_activate()
        return
    if parts == ["map", "packs", "rollback"] and handler.command == "POST":
        handler.handle_spatial_pack_rollback()
        return
    if parts == ["map", "packs", "remove"] and handler.command == "POST":
        handler.handle_spatial_pack_remove()
        return
    if (
        len(parts) == 6
        and parts[:2] == ["map", "tiles"]
        and parts[5].endswith(".pbf")
        and handler.command == "GET"
    ):
        handler.handle_spatial_pack_tile(
            parts[2], parts[3], parts[4], parts[5].removesuffix(".pbf")
        )
        return
    if (
        len(parts) == 4
        and parts[:2] == ["map", "packs"]
        and parts[3] == "coverage.geojson"
        and handler.command == "GET"
    ):
        handler.handle_spatial_pack_coverage(parts[2])
        return
    if (
        len(parts) == 4
        and parts[:2] == ["map", "packs"]
        and parts[3] == "public-transport.geojson"
        and handler.command == "GET"
    ):
        handler.handle_spatial_pack_public_transport(parts[2])
        return
    if parts == ["map", "viewport"]:
        handler.handle_map_viewport(query)
        return
    if parts == ["map"]:
        handler.handle_map(query)
        return
    if parts[0] == "geocoding" and len(parts) == 2 and parts[1] == "search":
        handler.handle_geocoding_search(query)
        return
    if parts[0] == "relationships":
        handler.route_relationship_request(parts, query)
        return
    if parts[0] == "taxonomies":
        handler.route_taxonomy_request(parts)
        return
    if parts[0] == "events":
        if len(parts) == 2 and handler.command == "GET":
            handler.handle_event_projection(parts[1])
            return
        handler.respond_not_found()
        return
    if parts[0] == "calendar":
        handler.route_calendar_request(parts, query)
        return

    definition = DEFINITIONS_BY_SLUG.get(parts[0])
    if definition is None:
        handler.respond_not_found()
        return
    if len(parts) == 1:
        handler.handle_list(definition, query)
    elif len(parts) == 2 and parts[1] == "new":
        handler.handle_new(definition)
    elif len(parts) == 2:
        handler.handle_detail(definition, parts[1], query)
    elif (
        len(parts) == 3
        and parts[2] == "download"
        and definition.type == "document"
    ):
        handler.handle_document_download(parts[1])
    elif len(parts) == 3 and parts[2] == "merge":
        handler.handle_merge(definition, parts[1], query)
    elif len(parts) == 3 and parts[2] == "edit":
        handler.handle_edit(definition, parts[1])
    elif len(parts) == 3 and parts[2] == "delete":
        handler.handle_delete(definition, parts[1])
    elif len(parts) == 3 and parts[2] == "favourite":
        handler.handle_favourite(definition, parts[1])
    elif definition.type == "person" and len(parts) == 3 and parts[2] == "journal":
        handler.handle_journal_create(parts[1])
    elif definition.type == "person" and len(parts) == 5 and parts[2] == "journal":
        handler.handle_journal_action(parts[1], parts[3], parts[4])
    else:
        handler.respond_not_found()
