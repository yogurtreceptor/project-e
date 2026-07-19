import json
import sqlite3
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import views
from app.config import (BACKUP_DIR, DATABASE_PATH, DOCUMENT_STORAGE_DIR, IMPORT_STAGING_DIR, initialise_local_storage)
from app.db import (
    connect,
    count_entities,
    create_entity,
    create_relationship,
    delete_entity,
    restore_entity,
    restore_relationship,
    permanent_delete_entity,
    list_deleted_entities,
    list_deleted_relationships,
    entity_dependency_counts,
    delete_relationship,
    get_entity,
    get_entity_by_id,
    get_relationship,
    initialise_database,
    list_all_entities,
    list_entities,
    list_favourite_entities,
    list_recent_entities,
    list_relationships,
    list_relationships_for_entity,
    mark_entity_viewed,
    normalise_form_values,
    normalise_relationship_direction,
    normalise_relationship_values,
    search_entities,
    set_entity_favourite,
    update_entity,
    update_relationship,
    validate_entity_values,
    validate_relationship_values,
    list_journal_entries,
    get_journal_entry,
    create_journal_entry,
    update_journal_entry,
    archive_journal_entry,
    delete_journal_entry,
    list_reference_items,
    list_units,
)
from app.document_storage import (
    UploadedFile,
    delete_stored_document,
    format_file_size,
    safe_file_name,
    store_document_upload as persist_document_upload,
    stored_document_path as resolve_document_path,
)
from app.document_lifecycle import delete_unreferenced_document_file
from app.duplicate_detection import find_duplicate_entities
from app.entity_merge import list_entity_history, merge_entities, preview_entity_merge
from app.audit import AuditFilters, list_audit_events
from app.integrity import audit_relationships, warnings_for_entity
from app.entities import DEFINITIONS_BY_SLUG, EVENT_DEFINITION, EntityDefinition
from app.calendar_service import get_calendar, list_calendars
from app.event_service import EventInput, EventSchedule, EventUpdate, create_event, get_event, list_events, reschedule_event, update_event
from app.geo import build_map_payload, geocoder
from app.relationship_graph import connected_family_components, extract_family_graph, full_family_component
from app.relationship_inference import list_review_batches, recompute_inferences, review_suggestion, undo_suggestion_review
from app.graph_layout import layered_layout
from app.relationship_workflow import (
    create_inline_relationship_target as create_inline_target,
    inline_entity_values as build_inline_entity_values,
)
from app.timeline import TimelineFilters, registry as timeline_registry
from app.portability import (apply_import_bundle, consume_staged_bundle, create_bundle, create_recovery_backup, inspect_bundle, stage_bundle)


STATIC_DIR = Path(__file__).resolve().parent / "static"
class EddyRequestHandler(BaseHTTPRequestHandler):
    database_path = DATABASE_PATH
    document_storage_dir = DOCUMENT_STORAGE_DIR
    backup_dir = BACKUP_DIR
    import_staging_dir = IMPORT_STAGING_DIR

    def do_GET(self) -> None:
        self.route_request()

    def do_POST(self) -> None:
        self.route_request()

    def log_message(self, format: str, *args: object) -> None:
        print("%s - - %s" % (self.address_string(), format % args))

    def route_request(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        query = {
            key: ",".join(values) if key == "calendars" else values[0]
            for key, values in parse_qs(parsed.query).items()
        }

        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path.removeprefix("/static/"))
            return

        if not parts:
            self.handle_dashboard()
            return

        if parts[0] == "search":
            self.handle_search(query)
            return

        if parts[0] == "system-tools" and len(parts) == 1:
            self.respond_page("System Tools", views.system_tools_page(), active_slug="system-tools")
            return

        if parts[:2] == ["system-tools", "audit"] and len(parts) == 2:
            self.handle_system_audit(query)
            return

        if parts[:2] == ["system-tools", "portability"]:
            self.handle_portability(parts)
            return

        if parts[0] == "timeline":
            self.handle_timeline(query)
            return

        if parts[0] == "recycle-bin":
            self.route_recycle_bin_request(parts)
            return

        if parts[0] == "data-quality":
            self.handle_data_quality()
            return

        if parts[0] == "map":
            self.handle_map(query)
            return

        if parts[0] == "geocoding" and len(parts) == 2 and parts[1] == "search":
            self.handle_geocoding_search(query)
            return

        if parts[0] == "relationships":
            self.route_relationship_request(parts, query)
            return

        if parts[0] == "taxonomies":
            self.route_taxonomy_request(parts)
            return

        if parts[0] == "events":
            if len(parts) == 2 and self.command == "GET":
                self.handle_event_projection(parts[1])
                return
            self.respond_not_found()
            return

        if parts[0] == "calendar":
            self.route_calendar_request(parts, query)
            return

        definition = DEFINITIONS_BY_SLUG.get(parts[0])
        if definition is None:
            self.respond_not_found()
            return

        if len(parts) == 1:
            self.handle_list(definition, query)
        elif len(parts) == 2 and parts[1] == "new":
            self.handle_new(definition)
        elif len(parts) == 2:
            self.handle_detail(definition, parts[1], query)
        elif len(parts) == 3 and parts[2] == "download" and definition.type == "document":
            self.handle_document_download(parts[1])
        elif len(parts) == 3 and parts[2] == "merge":
            self.handle_merge(definition, parts[1], query)
        elif len(parts) == 3 and parts[2] == "edit":
            self.handle_edit(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "delete":
            self.handle_delete(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "favourite":
            self.handle_favourite(definition, parts[1])
        elif definition.type == "person" and len(parts) == 3 and parts[2] == "journal":
            self.handle_journal_create(parts[1])
        elif definition.type == "person" and len(parts) == 5 and parts[2] == "journal":
            self.handle_journal_action(parts[1], parts[3], parts[4])
        else:
            self.respond_not_found()

    def route_relationship_request(self, parts: list[str], query: dict[str, str]) -> None:
        if len(parts) == 1:
            self.handle_relationship_list()
        elif len(parts) == 2 and parts[1] == "new":
            self.handle_relationship_new(query)
        elif len(parts) == 2 and parts[1] == "family-tree":
            self.handle_family_tree(query)
        elif len(parts) == 2 and parts[1] == "inferences":
            self.handle_inference_queue()
        elif len(parts) == 4 and parts[1] == "inferences" and parts[3] == "review":
            self.handle_inference_review(parts[2])
        elif len(parts) == 4 and parts[1] == "inferences" and parts[3] == "undo":
            self.handle_inference_undo(parts[2])
        elif len(parts) == 2:
            self.handle_relationship_detail(parts[1], query)
        elif len(parts) == 3 and parts[2] == "edit":
            self.handle_relationship_edit(parts[1], query)
        elif len(parts) == 3 and parts[2] == "delete":
            self.handle_relationship_delete(parts[1], query)
        else:
            self.respond_not_found()

    def route_calendar_request(self, parts: list[str], query: dict[str, str]) -> None:
        if len(parts) == 1 and self.command == "GET":
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                events = list_events(connection)
                created_id = self.parse_entity_id(query.get("created", ""))
                created_event = get_event(connection, created_id) if created_id else None
                preview_id = self.parse_entity_id(query.get("preview", ""))
                preview_event = get_event(connection, preview_id) if preview_id else None
            anchor_date = self.calendar_anchor_date(query.get("date", ""))
            view = query.get("view", "month") if query.get("view") in {"month", "week"} else "month"
            selected_ids = {int(item) for item in query.get("calendars", "").split(",") if item.isdigit()}
            projection = views.calendar_projection(events, calendars, view=view, anchor_date=anchor_date, selected_calendar_ids=selected_ids, preview_event=preview_event)
            self.respond_page("Calendar", views.calendar_page(calendars, events, views.default_event_values(calendars), created_event=created_event, projection=projection), active_slug="calendar", show_save_toast=created_event is not None)
            return
        editing_id = self.parse_entity_id(parts[2]) if len(parts) == 4 and parts[1] == "events" and parts[3] == "edit" else None
        delete_id = self.parse_entity_id(parts[2]) if len(parts) == 4 and parts[1] == "events" and parts[3] == "delete" else None
        if delete_id is not None and self.command == "POST":
            self.handle_calendar_event_delete(delete_id)
            return
        if editing_id is not None and self.command == "GET":
            with connect(self.database_path) as connection:
                event = get_event(connection, editing_id, include_archived=True)
                calendars = list_calendars(connection, include_archived=True)
                events = list_events(connection)
                calendar = get_calendar(connection, event.calendar_id, include_archived=True) if event else None
            if event is None or calendar is None:
                self.respond_not_found(); return
            self.respond_page("Edit Event", views.calendar_page(calendars, events, views.event_form_values(event, calendar), editing_event=event), active_slug="calendar", show_save_toast=query.get("saved") == "1")
            return
        if len(parts) == 2 and parts[1] == "events" and self.command == "POST":
            self.handle_calendar_event_create()
            return
        if editing_id is not None and self.command == "POST":
            self.handle_calendar_event_edit(editing_id)
            return
        self.respond_not_found()

    def handle_calendar_event_create(self) -> None:
        values = self.read_form()
        try:
            with connect(self.database_path) as connection:
                event_id = create_event(connection, self.event_input_from_form(values))
        except (ValueError, sqlite3.Error) as error:
            self.respond_calendar_event_form(values, [str(error)])
            return
        self.redirect(f"/calendar?created={event_id}")

    def handle_calendar_event_edit(self, event_id: int) -> None:
        values = self.read_form()
        try:
            with connect(self.database_path) as connection:
                event = get_event(connection, event_id, include_archived=True)
                if event is None:
                    self.respond_not_found(); return
                event_input = self.event_input_from_form(values)
                update_event(connection, event_id, EventUpdate(event_input.title, event_input.calendar_id, event_input.notes))
                reschedule_event(connection, event_id, EventSchedule(event_input.all_day, event_input.timezone, event_input.start_local, event_input.end_local, start_date=event_input.start_date, end_date=event_input.end_date))
        except (ValueError, sqlite3.Error) as error:
            self.respond_calendar_event_form(values, [str(error)], event_id)
            return
        self.redirect(f"/calendar/events/{event_id}/edit?saved=1")

    def handle_calendar_event_delete(self, event_id: int) -> None:
        with connect(self.database_path) as connection:
            event = get_event(connection, event_id, include_archived=True)
            if event is None:
                self.respond_not_found()
                return
            delete_entity(connection, EVENT_DEFINITION, event_id)
        self.redirect("/calendar")

    @staticmethod
    def calendar_anchor_date(value: str):
        from datetime import date
        try:
            return date.fromisoformat(value) if value else date.today()
        except ValueError:
            return date.today()

    @staticmethod
    def event_input_from_form(values: dict[str, str]) -> EventInput:
        calendar_id = int(values["calendar_id"]) if values.get("calendar_id", "").isdigit() else None
        return EventInput(values.get("title", ""), values.get("all_day") == "1", calendar_id, values.get("notes", ""), values.get("timezone", ""), values.get("start_local", ""), values.get("end_local", ""), start_date=values.get("start_date", ""), end_date=values.get("end_date", ""))

    def respond_calendar_event_form(self, values: dict[str, str], errors: list[str], event_id: int | None = None) -> None:
        with connect(self.database_path) as connection:
            calendars = list_calendars(connection, include_archived=True)
            events = list_events(connection)
            event = get_event(connection, event_id, include_archived=True) if event_id else None
        self.respond_page("Edit Event" if event else "Calendar", views.calendar_page(calendars, events, values, errors, event), HTTPStatus.BAD_REQUEST, active_slug="calendar")

    def route_taxonomy_request(self, parts: list[str]) -> None:
        from app.taxonomy import archive_entry, create_entry, list_entries, load_relationship_catalog
        error = ""
        try:
            with connect(self.database_path) as connection:
                if self.command == "POST" and len(parts) == 2 and parts[1] == "new":
                    form = self.read_form()
                    relationship = form if form.get("taxonomy_key") == "relationship_type" else None
                    create_entry(connection, form.get("taxonomy_key", ""), form.get("label", ""), self.parse_entity_id(form.get("parent_id", "")), relationship)
                    load_relationship_catalog(connection)
                    connection.commit()
                    self.redirect("/taxonomies")
                    return
                if self.command == "POST" and len(parts) == 3 and parts[2] == "archive":
                    entry_id = self.parse_entity_id(parts[1])
                    if entry_id is None: raise ValueError("Taxonomy entry not found.")
                    archive_entry(connection, entry_id)
                    load_relationship_catalog(connection)
                    connection.commit()
                    self.redirect("/taxonomies")
                    return
                if self.command != "GET" or len(parts) != 1:
                    self.respond_not_found(); return
                entries = {key: list_entries(connection, key, include_archived=True) for key in ("organisation_classification", "relationship_type")}
        except (ValueError, KeyError, sqlite3.IntegrityError) as exc:
            error = str(exc)
            with connect(self.database_path) as connection:
                entries = {key: list_entries(connection, key, include_archived=True) for key in ("organisation_classification", "relationship_type")}
        self.respond_page("Taxonomies", views.taxonomies_page(entries, error), active_slug="system-tools")

    def route_recycle_bin_request(self, parts: list[str]) -> None:
        if len(parts) == 1 and self.command == "GET":
            with connect(self.database_path) as connection:
                records = list_deleted_entities(connection)
                relationships = list_deleted_relationships(connection)
            self.respond_page("Recycle Bin", views.recycle_bin_page(records, relationships), active_slug="system-tools")
            return
        if len(parts) == 4 and parts[1] == "relationships" and parts[3] == "restore" and self.command == "POST":
            relationship_id = self.parse_entity_id(parts[2])
            if relationship_id is None:
                self.respond_not_found()
                return
            with connect(self.database_path) as connection:
                restored = restore_relationship(connection, relationship_id)
            if not restored:
                self.respond_not_found()
                return
            self.redirect("/recycle-bin")
            return
        entity_id = self.parse_entity_id(parts[1]) if len(parts) >= 2 else None
        if entity_id is None:
            self.respond_not_found()
            return
        if len(parts) == 3 and parts[2] == "restore" and self.command == "POST":
            with connect(self.database_path) as connection:
                restored = restore_entity(connection, entity_id)
            if not restored:
                self.respond_not_found()
                return
            self.redirect("/recycle-bin")
            return
        if len(parts) == 3 and parts[2] == "permanent-delete":
            with connect(self.database_path) as connection:
                record = get_entity_by_id(connection, entity_id, include_deleted=True)
                if record is None or not record.is_deleted:
                    self.respond_not_found()
                    return
                if self.command == "GET":
                    dependencies = entity_dependency_counts(connection, entity_id)
                    self.respond_page("Confirm permanent deletion", views.permanent_delete_confirmation_page(record, dependencies), active_slug="system-tools")
                    return
                if self.command == "POST" and self.read_form().get("confirm") == "yes":
                    create_recovery_backup(self.database_path, self.document_storage_dir, self.backup_dir, "before-permanent-delete")
                    _record_type, file_path = permanent_delete_entity(connection, entity_id)
                    if file_path:
                        delete_unreferenced_document_file(connection, file_path, self.document_storage_dir)
                    self.redirect("/recycle-bin")
                    return
        self.respond_not_found()

    def handle_family_tree(self, query: dict[str, str]) -> None:
        selected_person_id = self.parse_entity_id(query.get("person", ""))
        with connect(self.database_path) as connection:
            relationships = list_relationships(connection)
        if selected_person_id is None:
            graph = full_family_component(relationships)
        else:
            components = connected_family_components(extract_family_graph(relationships))
            graph = next((component for component in components if any(node.id == selected_person_id for node in component.nodes)), full_family_component(relationships))
        selected_ids = frozenset((selected_person_id,)) if selected_person_id is not None else frozenset()
        self.respond_page("Family Tree", views.family_tree_page(layered_layout(graph, selected_ids=selected_ids)), active_slug="relationships")

    def handle_portability(self, parts: list[str]) -> None:
        try:
            if len(parts) == 2 and self.command == "GET":
                self.respond_page("Import and export", views.portability_page(), active_slug="system-tools")
                return
            if len(parts) == 3 and parts[2] == "export" and self.command == "GET":
                content = create_bundle(self.database_path, self.document_storage_dir)
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", 'attachment; filename="project-e-export.zip"')
                self.end_headers()
                self.wfile.write(content)
                return
            if len(parts) == 3 and parts[2] == "preview" and self.command == "POST":
                _values, upload = self.read_multipart_form()
                if upload is None:
                    raise ValueError("Choose a Project E ZIP bundle.")
                preview = inspect_bundle(upload.data)
                token = stage_bundle(upload.data, self.import_staging_dir)
                self.respond_page("Import preview", views.import_preview_page(preview, token), active_slug="system-tools")
                return
            if len(parts) == 3 and parts[2] == "import" and self.command == "POST":
                form = self.read_form()
                if form.get("confirm") != "yes":
                    raise ValueError("Import confirmation is required.")
                bundle = consume_staged_bundle(form.get("token", ""), self.import_staging_dir)
                apply_import_bundle(bundle, self.database_path, self.document_storage_dir, self.backup_dir)
                self.redirect("/system-tools/portability")
                return
        except (ValueError, OSError, sqlite3.Error) as error:
            self.respond_page("Import and export", views.portability_page(str(error)), HTTPStatus.BAD_REQUEST, active_slug="system-tools")
            return
        self.respond_not_found()

    def handle_dashboard(self) -> None:
        with connect(self.database_path) as connection:
            counts = count_entities(connection)
            relationship_count = len(list_relationships(connection))
            recent_entities = list_recent_entities(connection)
            favourite_entities = list_favourite_entities(connection)
        self.respond_page(
            "Dashboard",
            views.dashboard_page(counts, relationship_count, recent_entities, favourite_entities),
        )

    def handle_search(self, query: dict[str, str]) -> None:
        search_query = query.get("q", "")
        entity_type = query.get("type", "")
        favourites_only = query.get("favourites") == "1"
        filter_key = query.get("filter", "")
        filter_value = query.get("filter_value", "")
        with connect(self.database_path) as connection:
            results = search_entities(connection, search_query, entity_type, favourites_only, filter_key, filter_value)
        self.respond_page(
            "Search",
            views.search_page(search_query, entity_type, favourites_only, results, filter_key, filter_value),
            active_slug="system-tools",
        )

    def handle_timeline(self, query: dict[str, str]) -> None:
        filters = TimelineFilters(
            entity_type=query.get("type", "") if query.get("type", "") in {definition.type for definition in DEFINITIONS_BY_SLUG.values()} else "",
            date_from=query.get("from", ""),
            date_to=query.get("to", ""),
            related_person_id=self.parse_entity_id(query.get("person", "")),
            related_organisation_id=self.parse_entity_id(query.get("organisation", "")),
            related_project_id=self.parse_entity_id(query.get("project", "")),
        )
        with connect(self.database_path) as connection:
            records = list_all_entities(connection)
            relationships = list_relationships(connection)
        events = timeline_registry.derive_all(records, relationships, filters)
        related_options = {
            entity_type: [record for record in records if record.type == entity_type]
            for entity_type in ("person", "organisation", "project")
        }
        self.respond_page(
            "Universal Timeline",
            views.universal_timeline_page(events, filters, related_options),
            active_slug="timeline",
        )


    def handle_system_audit(self, query: dict[str, str]) -> None:
        filters = AuditFilters(event_type=query.get("event_type", ""), record_kind=query.get("record_kind", ""), record_id=int(query["record_id"]) if query.get("record_id", "").isdigit() else None)
        with connect(self.database_path) as connection:
            events = list_audit_events(connection, filters=filters)
        self.respond_page("System Audit", views.system_audit_page(events, filters), active_slug="system-tools")

    def handle_data_quality(self) -> None:
        from app.data_quality import registry
        with connect(self.database_path) as connection:
            findings = registry.evaluate(connection)
        self.respond_page("Data Quality Centre", views.data_quality_page(findings), active_slug="system-tools")

    def handle_map(self, query: dict[str, str]) -> None:
        with connect(self.database_path) as connection:
            payload = build_map_payload(connection)
        self.respond_page(
            "Map",
            views.map_page(payload, query.get("entity_id", "")),
            active_slug="map",
        )

    def handle_geocoding_search(self, query: dict[str, str]) -> None:
        if self.command != "GET":
            self.respond_not_found()
            return
        try:
            results = geocoder().search(query.get("q", ""))
            self.respond_json({"results": results})
        except Exception as error:
            self.respond_json({"results": [], "error": str(error)}, status=HTTPStatus.OK)

    def handle_list(self, definition: EntityDefinition, query: dict[str, str]) -> None:
        filter_query = query.get("q", "")
        favourites_only = query.get("favourites") == "1"
        with connect(self.database_path) as connection:
            records = list_entities(connection, definition, filter_query, favourites_only)
        self.respond_page(
            definition.plural,
            views.entity_list_page(definition, records, filter_query, favourites_only),
            active_slug=definition.slug,
        )

    def handle_detail(self, definition: EntityDefinition, raw_id: str, query: dict[str, str]) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return

        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            if record is not None:
                mark_entity_viewed(connection, entity_id)
                record = get_entity(connection, definition, entity_id)
            relationships = list_relationships_for_entity(connection, entity_id) if record else []
            integrity_warnings = warnings_for_entity(audit_relationships(connection), entity_id) if record else []
            history = list_entity_history(connection, entity_id) if record else []
            audit_events = list_audit_events(connection, "entity", entity_id) if record else []
            journal_entries = list_journal_entries(connection, "person", entity_id) if record and definition.type == "person" else []
        if record is None:
            self.respond_not_found()
            return

        self.respond_page(
            record.title,
            views.entity_detail_page(record, relationships, integrity_warnings, history, audit_events, journal_entries),
            active_slug=definition.slug,
            show_save_toast=query.get("saved") == "1",
        )

    def handle_event_projection(self, raw_id: str) -> None:
        event_id = self.parse_entity_id(raw_id)
        if event_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            event = get_event(connection, event_id, include_archived=True)
            if event is None:
                self.respond_not_found()
                return
            mark_entity_viewed(connection, event_id)
            calendar = get_calendar(connection, event.calendar_id, include_archived=True)
            relationships = list_relationships_for_entity(connection, event_id)
            history = list_entity_history(connection, event_id)
            audit_events = list_audit_events(connection, "entity", event_id)
        self.respond_page(
            event.title,
            views.event_projection_page(event, calendar, relationships, history, audit_events),
            active_slug="system-tools",
        )

    def handle_new(self, definition: EntityDefinition) -> None:
        if self.command == "POST":
            values, upload = self.read_entity_form(definition)
            if definition.type == "document" and upload is None:
                self.clear_document_file_values(values)
            with connect(self.database_path) as connection:
                errors = validate_entity_values(definition, values, connection)
            duplicate_matches = []
            if not errors:
                with connect(self.database_path) as connection:
                    duplicate_matches = find_duplicate_entities(connection, definition, values)
                if duplicate_matches and values.get("confirm_duplicate") != "1":
                    if upload is not None:
                        self.clear_document_file_values(values)
                    self.respond_form(
                        definition, values, errors, "Create",
                        duplicate_matches=duplicate_matches,
                    )
                    return
                stored_metadata = None
                if upload is not None:
                    stored_metadata = self.store_document_upload(upload)
                    values.update(stored_metadata)
                try:
                    with connect(self.database_path) as connection:
                        entity_id = create_entity(connection, definition, values)
                except Exception:
                    if stored_metadata is not None:
                        self.delete_document_file(stored_metadata.get("file_path", ""))
                    raise
                self.redirect(f"/{definition.slug}/{entity_id}?saved=1")
                return
            self.respond_form(definition, values, errors, "Create")
            return

        self.respond_form(definition, {}, [], "Create")

    def handle_edit(self, definition: EntityDefinition, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return

        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
        if record is None:
            self.respond_not_found()
            return

        if self.command == "POST":
            values, upload = self.read_entity_form(definition)
            if definition.type == "person":
                values["notes"] = record.notes
            if definition.type == "document" and upload is None:
                self.restore_document_file_values(values, record.metadata)
            with connect(self.database_path) as connection:
                errors = validate_entity_values(definition, values, connection)
            duplicate_matches = []
            if not errors:
                with connect(self.database_path) as connection:
                    duplicate_matches = find_duplicate_entities(
                        connection, definition, values, exclude_entity_id=entity_id
                    )
                if duplicate_matches and values.get("confirm_duplicate") != "1":
                    if upload is not None:
                        self.restore_document_file_values(values, record.metadata)
                    self.respond_form(
                        definition, values, errors, "Edit", entity_id,
                        duplicate_matches=duplicate_matches,
                    )
                    return
                previous_file_path = record.metadata.get("file_path", "")
                stored_metadata = None
                if upload is not None:
                    stored_metadata = self.store_document_upload(upload)
                    values.update(stored_metadata)
                try:
                    with connect(self.database_path) as connection:
                        update_entity(connection, definition, entity_id, values)
                except Exception:
                    if stored_metadata is not None:
                        self.delete_document_file(stored_metadata.get("file_path", ""))
                    raise
                current_file_path = values.get("file_path", "")
                if previous_file_path and previous_file_path != current_file_path:
                    with connect(self.database_path) as connection:
                        delete_unreferenced_document_file(
                            connection, previous_file_path, self.document_storage_dir
                        )
                self.redirect(f"/{definition.slug}/{entity_id}?saved=1")
                return
            self.respond_form(definition, values, errors, "Edit", entity_id)
            return

        self.respond_form(definition, record.to_form_values(), [], "Edit", entity_id)

    def handle_merge(self, definition: EntityDefinition, raw_id: str, query: dict[str, str]) -> None:
        survivor_id = self.parse_entity_id(raw_id)
        if survivor_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            survivor = get_entity(connection, definition, survivor_id)
            if survivor is None:
                self.respond_not_found()
                return
            duplicate_id = self.parse_entity_id(query.get("duplicate_id", "")) if self.command == "GET" else self.parse_entity_id(self.read_form().get("duplicate_id", ""))
            if duplicate_id is None:
                candidates = [item for item in list_entities(connection, definition) if item.id != survivor_id]
                self.respond_page("Merge duplicate", views.merge_select_page(survivor, candidates), active_slug=definition.slug)
                return
            try:
                preview = preview_entity_merge(connection, survivor_id, duplicate_id)
                if self.command == "POST":
                    create_recovery_backup(self.database_path, self.document_storage_dir, self.backup_dir, "before-merge")
                    merge_entities(connection, survivor_id, duplicate_id)
                    self.redirect(f"/{definition.slug}/{survivor_id}")
                    return
            except ValueError as error:
                candidates = [item for item in list_entities(connection, definition) if item.id != survivor_id]
                self.respond_page("Merge duplicate", views.merge_select_page(survivor, candidates, str(error)), active_slug=definition.slug)
                return
        self.respond_page("Merge preview", views.merge_preview_page(preview), active_slug=definition.slug)

    def handle_document_download(self, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        definition = DEFINITIONS_BY_SLUG["documents"]
        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
        if record is None:
            self.respond_not_found()
            return
        file_path = self.stored_document_path(record.metadata.get("file_path", ""))
        if file_path is None or not file_path.exists():
            self.respond_not_found()
            return
        content = file_path.read_bytes()
        file_name = record.metadata.get("file_name", file_path.name)
        content_type = record.metadata.get("mime_type", "") or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        disposition = "inline" if parse_qs(urlparse(self.path).query).get("open") == ["1"] and (content_type.startswith("text/") or content_type.startswith("image/")) else "attachment"
        self.send_header("Content-Disposition", f'{disposition}; filename="{file_name.replace(chr(34), "")}"')
        self.end_headers()
        self.wfile.write(content)

    def handle_favourite(self, definition: EntityDefinition, raw_id: str) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        is_favourite = self.read_form().get("is_favourite") == "1"
        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            if record is None:
                self.respond_not_found()
                return
            set_entity_favourite(connection, entity_id, is_favourite)
        self.redirect(f"/{definition.slug}/{entity_id}")

    def handle_delete(self, definition: EntityDefinition, raw_id: str) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            if record is None:
                self.respond_not_found()
                return
            delete_entity(connection, definition, entity_id)
        self.redirect(f"/{definition.slug}")

    def handle_journal_create(self, raw_person_id: str) -> None:
        person_id = self.parse_entity_id(raw_person_id)
        if self.command != "POST" or person_id is None:
            self.respond_not_found()
            return
        body = self.read_form().get("body", "")
        with connect(self.database_path) as connection:
            person = get_entity(connection, DEFINITIONS_BY_SLUG["people"], person_id)
            if person is None:
                self.respond_not_found()
                return
            try:
                create_journal_entry(connection, "person", person_id, body)
            except ValueError:
                self.redirect(f"/people/{person_id}")
                return
        self.redirect(f"/people/{person_id}")

    def handle_journal_action(
        self, raw_person_id: str, raw_entry_id: str, action: str
    ) -> None:
        person_id = self.parse_entity_id(raw_person_id)
        entry_id = self.parse_entity_id(raw_entry_id)
        if person_id is None or entry_id is None or action not in {"edit", "archive", "delete"}:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            person = get_entity(connection, DEFINITIONS_BY_SLUG["people"], person_id)
            entry = get_journal_entry(connection, entry_id)
            if person is None or entry is None or entry.entity_type != "person" or entry.entity_id != person_id:
                self.respond_not_found()
                return
            if action == "edit":
                if self.command == "GET":
                    self.respond_page(
                        "Edit journal entry",
                        views.journal_edit_page(person, entry),
                        active_slug="people",
                    )
                    return
                if self.command == "POST":
                    body = self.read_form().get("body", "")
                    try:
                        update_journal_entry(connection, entry_id, body)
                    except ValueError as error:
                        self.respond_page(
                            "Edit journal entry",
                            views.journal_edit_page(person, entry, str(error)),
                            active_slug="people",
                        )
                        return
                    self.redirect(f"/people/{person_id}")
                    return
            elif self.command == "POST" and action == "archive":
                archive_journal_entry(connection, entry_id)
                self.redirect(f"/people/{person_id}")
                return
            elif self.command == "POST" and action == "delete":
                delete_journal_entry(connection, entry_id)
                self.redirect(f"/people/{person_id}")
                return
        self.respond_not_found()

    def handle_inference_queue(self) -> None:
        with connect(self.database_path) as connection:
            # Reconcile on read as a safety net for imported, migrated, or previously
            # missed relationship changes. This remains deterministic and creates
            # review suggestions only; it never activates inferred relationships.
            recompute_inferences(connection, "queue_reconciliation")
            batches = list_review_batches(connection)
            history = [(batch, items) for batch, items in list_review_batches(connection, include_closed=True) if batch["status"] != "open"]
            relationships_by_id = {item.id: item for item in list_relationships(connection)}
        self.respond_page("Inference Review Queue", views.inference_review_page(batches, relationships_by_id, history), active_slug="relationships")

    def handle_inference_review(self, raw_id: str) -> None:
        suggestion_id = self.parse_entity_id(raw_id)
        if self.command != "POST" or suggestion_id is None:
            self.respond_not_found()
            return
        decision = self.read_form().get("decision", "")
        try:
            with connect(self.database_path) as connection:
                review_suggestion(connection, suggestion_id, decision)
        except ValueError:
            self.respond_not_found()
            return
        self.redirect("/relationships/inferences")

    def handle_inference_undo(self, raw_id: str) -> None:
        suggestion_id = self.parse_entity_id(raw_id)
        if self.command != "POST" or suggestion_id is None:
            self.respond_not_found()
            return
        try:
            with connect(self.database_path) as connection:
                undo_suggestion_review(connection, suggestion_id)
        except ValueError:
            self.respond_not_found()
            return
        self.redirect("/relationships/inferences")

    def handle_relationship_list(self) -> None:
        with connect(self.database_path) as connection:
            integrity_warnings = audit_relationships(connection)
            relationships = list_relationships(connection)
        self.respond_page(
            "Relationships",
            views.relationship_list_page(relationships, integrity_warnings),
            active_slug="relationships",
        )

    def handle_relationship_detail(self, raw_id: str, query: dict[str, str]) -> None:
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            relationship = get_relationship(connection, relationship_id)
        if relationship is None:
            self.respond_not_found()
            return
        self.respond_page(
            "Relationship",
            views.relationship_detail_page(relationship),
            active_slug="relationships",
            show_save_toast=query.get("saved") == "1",
        )

    def handle_relationship_new(self, query: dict[str, str]) -> None:
        if self.command == "POST":
            raw_form = self.read_form()
            values = normalise_relationship_values(raw_form)
            with connect(self.database_path) as connection:
                inline_errors = self.create_inline_relationship_target(connection, values, raw_form, query)
                normalise_relationship_direction(connection, values)
                errors = validate_relationship_values(connection, values)
                errors = inline_errors + errors
                entities = list_all_entities(connection)
                if not errors:
                    relationship_id = create_relationship(connection, values)
                    self.redirect(self.relationship_redirect(values, relationship_id, query))
                    return
                connection.rollback()
                context_entity = self.relationship_context_entity(connection, query, values)
            self.respond_relationship_form(values, errors, entities, "Create", context_entity=context_entity, target_type=query.get("target_type"))
            return

        values = {
            "source_entity_id": query.get("source_entity_id", ""),
            "target_entity_id": query.get("target_entity_id", ""),
            "type": "",
            "status": "active",
            "started_at": "",
            "started_at_precision": "exact",
            "ended_at": "",
            "ended_at_precision": "exact",
            "notes": "",
        }
        with connect(self.database_path) as connection:
            entities = list_all_entities(connection)
            context_entity = self.relationship_context_entity(connection, query, values)
        self.respond_relationship_form(values, [], entities, "Create", context_entity=context_entity, target_type=query.get("target_type"))

    def handle_relationship_edit(self, raw_id: str, query: dict[str, str]) -> None:
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            relationship = get_relationship(connection, relationship_id)
            entities = list_all_entities(connection)
        if relationship is None:
            self.respond_not_found()
            return

        if self.command == "POST":
            values = normalise_relationship_values(self.read_form())
            with connect(self.database_path) as connection:
                errors = validate_relationship_values(connection, values, relationship_id)
                entities = list_all_entities(connection)
                if not errors:
                    update_relationship(connection, relationship_id, values)
                    self.redirect(self.relationship_redirect(values, relationship_id, query))
                    return
                context_entity = self.relationship_context_entity(connection, query, values)
            self.respond_relationship_form(values, errors, entities, "Edit", relationship_id, context_entity=context_entity, target_type=query.get("target_type"))
            return

        values = relationship.to_form_values()
        context_entity = self.relationship_context_entity(connection, query, values)
        self.respond_relationship_form(
            values, [], entities, "Edit", relationship_id, context_entity=context_entity, target_type=query.get("target_type")
        )

    def handle_relationship_delete(self, raw_id: str, query: dict[str, str]) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        redirect_to = "/relationships"
        with connect(self.database_path) as connection:
            context_entity = self.relationship_context_entity(connection, query, {})
            if context_entity is not None:
                redirect_to = f"/{context_entity.slug}/{context_entity.id}"
            delete_relationship(connection, relationship_id)
        self.redirect(redirect_to)

    def respond_form(
        self,
        definition: EntityDefinition,
        values: dict[str, str],
        errors: list[str],
        action: str,
        entity_id: int | None = None,
        duplicate_matches: list | None = None,
    ) -> None:
        field_options: dict[str, list[tuple[str, str]]] = {}
        with connect(self.database_path) as connection:
            for field in definition.fields:
                if field.storage_kind == "reference":
                    field_options[field.name] = [
                        (str(item.id), item.name)
                        for item in list_reference_items(connection, field.reference_type)
                    ]
                elif field.storage_kind == "measurement":
                    field_options[field.name] = [
                        (str(unit.id), f"{unit.name} ({unit.symbol})")
                        for unit in list_units(connection, field.measurement_category)
                    ]
                elif field.storage_kind == "taxonomy":
                    from app.taxonomy import organisation_choices
                    current = values.get(f"{field.name}__taxonomy_entry_id", values.get(field.name, ""))
                    field_options[field.name] = organisation_choices(
                        connection, int(current) if current.isdecimal() else None
                    )
        self.respond_page(
            f"{action} {definition.singular}",
            views.entity_form_page(
                definition, values, errors, action, entity_id, duplicate_matches,
                field_options,
            ),
            active_slug=definition.slug,
        )

    def respond_relationship_form(
        self,
        values: dict[str, str],
        errors: list[str],
        entities: list,
        action: str,
        relationship_id: int | None = None,
        context_entity=None,
        target_type: str | None = None,
    ) -> None:
        from app.taxonomy import organisation_choices
        with connect(self.database_path) as connection:
            inline_field_options = {"organisation_type": organisation_choices(connection)}
        self.respond_page(
            f"{action} Relationship",
            views.relationship_form_page(
                values,
                errors,
                entities,
                action,
                relationship_id,
                context_entity=context_entity,
                target_type=target_type,
                inline_field_options=inline_field_options,
            ),
            active_slug=context_entity.slug if context_entity else "relationships",
        )

    def relationship_context_entity(self, connection, query: dict[str, str], values: dict[str, str]):
        raw_id = query.get("context_entity_id")
        entity_id = self.parse_entity_id(raw_id) if raw_id else None
        if entity_id is None:
            return None
        return get_entity_by_id(connection, entity_id)

    def create_inline_relationship_target(
        self,
        connection,
        values: dict[str, str],
        raw_form: dict[str, str],
        query: dict[str, str],
    ) -> list[str]:
        return create_inline_target(connection, values, raw_form, query)

    @staticmethod
    def inline_entity_values(definition: EntityDefinition, raw_form: dict[str, str]) -> dict[str, str]:
        return build_inline_entity_values(definition, raw_form)

    def relationship_redirect(
        self,
        values: dict[str, str],
        relationship_id: int,
        query: dict[str, str] | None = None,
    ) -> str:
        query = query or {}
        context_id = query.get("context_entity_id")
        if context_id:
            destination = self.entity_url_from_id(context_id) or f"/relationships/{relationship_id}"
            return f"{destination}?saved=1"
        return f"/relationships/{relationship_id}?saved=1"

    def entity_url_from_id(self, raw_id: str) -> str | None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            return None
        with connect(self.database_path) as connection:
            entity = get_entity_by_id(connection, entity_id)
        if entity is None:
            return None
        return f"/{entity.slug}/{entity.id}"

    def serve_static(self, relative_path: str) -> None:
        content_types = {
            "confirmation.js": "text/javascript; charset=utf-8",
            "dirty-form.js": "text/javascript; charset=utf-8",
            "foundation.css": "text/css; charset=utf-8",
            "shell.js": "text/javascript; charset=utf-8",
            "super-key.js": "text/javascript; charset=utf-8",
            "styles.css": "text/css; charset=utf-8",
            "taxonomy.js": "text/javascript; charset=utf-8",
        }
        if relative_path.startswith("icons/") and relative_path.endswith(".svg"):
            icon_name = relative_path.removeprefix("icons/").removesuffix(".svg")
            if not icon_name or not icon_name.replace("-", "").isalnum():
                self.respond_not_found()
                return
            path = STATIC_DIR / "icons" / f"{icon_name}.svg"
            if not path.is_file():
                self.respond_not_found()
                return
            content_type = "image/svg+xml"
        elif relative_path in content_types:
            path = STATIC_DIR / relative_path
            content_type = content_types[relative_path]
        else:
            self.respond_not_found()
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(body, keep_blank_values=True)
        return {key: ",".join(values) for key, values in parsed.items()}

    def read_entity_form(self, definition: EntityDefinition) -> tuple[dict[str, str], UploadedFile | None]:
        if definition.type != "document" or not self.headers.get("Content-Type", "").startswith("multipart/form-data"):
            raw_values = self.read_form()
            values = normalise_form_values(definition, raw_values)
            values["confirm_duplicate"] = raw_values.get("confirm_duplicate", "")
            return values, None
        raw_values, upload = self.read_multipart_form()
        values = normalise_form_values(definition, raw_values)
        values["confirm_duplicate"] = raw_values.get("confirm_duplicate", "")
        if upload is not None:
            values["file_name"] = upload.file_name
            values["mime_type"] = upload.content_type
            values["file_size"] = format_file_size(len(upload.data))
            if not values.get("display_name"):
                values["display_name"] = Path(upload.file_name).stem or upload.file_name
        return values, upload

    def read_multipart_form(self) -> tuple[dict[str, str], UploadedFile | None]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        values: dict[str, str] = {}
        upload = None
        for item in message.iter_parts():
            key = item.get_param("name", header="content-disposition")
            if not key:
                continue
            file_name = item.get_filename()
            data = item.get_payload(decode=True) or b""
            if key == "upload" and file_name:
                upload = UploadedFile(
                    file_name=Path(file_name).name,
                    content_type=item.get_content_type() or "application/octet-stream",
                    data=data,
                )
            elif not file_name:
                charset = item.get_content_charset() or "utf-8"
                values[key] = data.decode(charset, errors="replace")
        return values, upload

    @staticmethod
    def clear_document_file_values(values: dict[str, str]) -> None:
        for field_name in ("file_name", "file_path", "mime_type", "file_size"):
            values[field_name] = ""

    @staticmethod
    def restore_document_file_values(
        values: dict[str, str], metadata: dict[str, str]
    ) -> None:
        for field_name in ("file_name", "file_path", "mime_type", "file_size"):
            values[field_name] = metadata.get(field_name, "")

    def store_document_upload(self, upload: UploadedFile) -> dict[str, str]:
        return persist_document_upload(upload, self.document_storage_dir)

    def stored_document_path(self, value: str) -> Path | None:
        return resolve_document_path(value, self.document_storage_dir)

    def delete_document_file(self, value: str) -> bool:
        return delete_stored_document(value, self.document_storage_dir)

    def respond_page(
        self,
        title: str,
        content: str,
        status: HTTPStatus = HTTPStatus.OK,
        active_slug: str | None = None,
        show_save_toast: bool = False,
    ) -> None:
        body = views.layout(title, content, active_slug, show_save_toast)
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def respond_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def respond_not_found(self) -> None:
        self.respond_page("Not found", views.not_found_page(), HTTPStatus.NOT_FOUND)

    @staticmethod
    def parse_entity_id(raw_id: str) -> int | None:
        try:
            return int(raw_id)
        except ValueError:
            return None



def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    initialise_local_storage()
    initialise_database(EddyRequestHandler.database_path)
    server = ThreadingHTTPServer((host, port), EddyRequestHandler)
    print(f"Project E running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Project E stopped.")
    finally:
        server.server_close()
