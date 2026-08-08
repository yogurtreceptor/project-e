import json
import sqlite3
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from app import views
from app.config import initialise_local_storage
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
    location_place_context,
)
from app.document_lifecycle import delete_unreferenced_document_file
from app.defaults import (
    DEFAULT_CALENDAR_COLOUR,
    DEFAULT_EVENT_DURATION_MINUTES,
    DEFAULT_EXTERNAL_CALENDAR_COLOUR,
    PLATFORM_TIMEZONE,
)
from app.duplicate_detection import find_duplicate_entities
from app.entity_merge import list_entity_history, merge_entities, preview_entity_merge
from app.audit import AuditFilters, list_audit_events, record_audit_event
from app.integrity import audit_relationships, warnings_for_entity
from app.entities import DEFINITIONS_BY_SLUG, DEFINITIONS_BY_TYPE, EVENT_DEFINITION, EntityDefinition
from app.calendar_service import (
    CalendarInput, archive_calendar, create_calendar, delete_calendar, get_calendar,
    list_calendars, next_calendar_sort_order, reorder_calendars,
    set_default_calendar, unarchive_calendar, update_calendar,
)
from app.calendar_subscription_service import (
    SubscriptionSettingsInput, create_subscription, fetch_subscription,
    get_external_projection_event,
    get_subscription,
    list_subscriptions, read_staged_subscription, refresh_subscription,
    remove_subscription, reorder_subscriptions, set_subscription_enabled,
    stage_subscription_fetch, update_subscription_settings,
)
from app.event_service import EventSchedule, EventUpdate, create_event, get_event, list_events, reschedule_event, update_event
from app.event_recurrence import cancel_occurrence, get_recurrence, is_series_anchor, occurrence_exceptions, occurrences_between, override_occurrence, remove_recurrence, set_recurrence, split_series, truncate_series
from app.event_forms import (
    calendar_anchor_date,
    event_input_from_form,
    recurrence_rule_from_form,
)
from app.reminder_service import (DEFAULT_TIMINGS, act_on_inbox_item, archived_inbox_count,
    clear_policy, get_override, get_policy, inbox_count, list_deep_archive_items,
    list_inbox_actions_for_items, list_inbox_items, open_inbox_item,
    reactivate_next_open_snoozes, set_override, set_policy)
from app.scheduler_service import (SchedulerRuntime, ensure_registered_jobs, list_job_runs,
    list_scheduled_jobs, run_job_now, set_job_enabled)
from app.automation_service import ensure_registered_rules, list_rules, list_runs, set_rule_enabled
from app.geo import (
    build_map_payload,
    build_map_viewport_payload,
    geocoder,
    installed_provider_selection_key,
)
from app.map_feature_service import (
    add_map_feature_membership,
    clear_map_feature_list,
    create_map_feature_list,
    find_provider_promotion_matches,
    get_map_feature_list,
    list_map_feature_lists,
    list_map_feature_memberships,
    map_feature_membership_export,
    promote_provider_feature,
    provider_feature_from_form,
    remove_map_feature_membership,
)
from app.map_coverage_service import assess_map_coverage
from app.journey_cache import JourneyCache
from app.journey_repository import list_mobility_profiles, list_routing_policies
from app.journey_service import plan_journey
from app.routing_resources import (
    load_active_valhalla_capability,
    routing_capability_status,
)
from app.valhalla_adapter import ValhallaWalkingAdapter
from app.walking_journeys import (
    AVOID_STEPS_POLICY_KEY,
    configure_avoid_steps_policy,
    default_walking_form_values,
    ensure_default_walk_profile,
    list_journey_endpoint_options,
    walking_request_from_form,
)
from app.spatial_pack import (
    MAX_ARCHIVE_BYTES,
    activate_staged_spatial_pack,
    inspect_and_stage_spatial_pack,
    read_active_coverage,
    read_active_public_transport,
    read_active_search_feature,
    read_active_tile,
    read_staged_spatial_pack,
    remove_spatial_pack,
    rollback_spatial_pack,
    spatial_pack_status,
)
from app.relationship_graph import connected_family_components, extract_family_graph, full_family_component
from app.relationship_inference import list_review_batches, recompute_inferences, review_suggestion, undo_suggestion_review
from app.graph_layout import layered_layout
from app.relationship_workflow import (
    create_inline_relationship_target as create_inline_target,
    inline_entity_values as build_inline_entity_values,
)
from app.timeline import TimelineFilters, registry as timeline_registry
from app.portability import (apply_import_bundle, consume_staged_bundle, create_bundle, create_recovery_backup, inspect_bundle, stage_bundle)
from app.icalendar_service import (
    apply_icalendar_import, create_calendar_export, discard_staged_icalendar,
    inspect_icalendar_import, new_import_calendar_input, read_staged_icalendar,
    stage_icalendar,
)
from app.web_support import RequestSupportMixin
from app.http_server import DEFAULT_HTTP_CONFIG, create_http_server
from app.temporal_occurrences import calendar_temporal_projection
from app.web_router import route_request as dispatch_request


class EddyRequestHandler(RequestSupportMixin, BaseHTTPRequestHandler):
    database_path = DEFAULT_HTTP_CONFIG.database_path
    document_storage_dir = DEFAULT_HTTP_CONFIG.document_storage_dir
    backup_dir = DEFAULT_HTTP_CONFIG.backup_dir
    import_staging_dir = DEFAULT_HTTP_CONFIG.import_staging_dir
    spatial_pack_dir = DEFAULT_HTTP_CONFIG.spatial_pack_dir
    routing_dir = DEFAULT_HTTP_CONFIG.routing_dir
    journey_cache_path = DEFAULT_HTTP_CONFIG.journey_cache_path

    def do_GET(self) -> None:
        self.route_request()

    def do_POST(self) -> None:
        self.route_request()

    def log_message(self, format: str, *args: object) -> None:
        print("%s - - %s" % (self.address_string(), format % args))

    def route_request(self) -> None:
        dispatch_request(self)

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

    def route_inbox_request(self, parts: list[str], query: dict[str, str]) -> None:
        if parts[1:] == ["count"] and self.command == "GET":
            with connect(self.database_path) as connection:
                count = inbox_count(connection)
            self.respond_json({"count": count})
            return
        if parts[1:] == ["reminders"] and self.command == "GET":
            self.redirect("/calendar/settings")
            return
        source_kind = {"birthdays": "birthday", "document-expiries": "document_expiry"}.get(parts[2]) if len(parts) == 3 and parts[1] == "reminders" else None
        if source_kind is not None:
            if source_kind == "birthday":
                with connect(self.database_path) as connection:
                    calendar = connection.execute(
                        "SELECT id FROM calendars WHERE kind = 'birthday'"
                    ).fetchone()
                self.redirect(f"/calendar/settings/calendars/{calendar['id']}" if calendar else "/calendar/settings")
                return
            label = "Birthday" if source_kind == "birthday" else "Document-expiry"
            self.handle_reminder_policy("global", 0, source_kind, f"{label} reminder defaults", "/inbox/reminders", active_slug="inbox")
            return
        archived = query.get("archived") == "1"
        if len(parts) == 1 and self.command == "GET":
            page_size = int(query.get("page_size", "50")) if query.get("page_size", "50").isdigit() else 50
            page_size = page_size if page_size in {10, 50, 100} else 50
            page = max(1, int(query.get("page", "1"))) if query.get("page", "1").isdigit() else 1
            deep_archive = archived and query.get("deep") == "1"
            with connect(self.database_path) as connection:
                reactivate_next_open_snoozes(connection)
                archived_count = archived_inbox_count(connection) if archived else 0
                items = list_deep_archive_items(connection) if deep_archive else list_inbox_items(connection, archived=archived, limit=page_size, offset=(page - 1) * page_size)
                action_history = list_inbox_actions_for_items(connection, [item.id for item in items]) if archived else {}
            self.respond_page("Inbox", views.inbox_page(items, archived=archived, action_history=action_history, archived_count=archived_count, deep_archive=deep_archive, page_size=page_size, page=page), active_slug="inbox")
            return
        if len(parts) == 3 and self.command == "POST":
            item_id = self.parse_entity_id(parts[1])
            if item_id is not None:
                if parts[2] == "open":
                    with connect(self.database_path) as connection:
                        destination = open_inbox_item(connection, item_id)
                    if destination:
                        self.redirect(destination)
                        return
                else:
                    with connect(self.database_path) as connection: act_on_inbox_item(connection, item_id, parts[2])
            self.redirect("/inbox"); return
        self.respond_not_found()

    def route_calendar_request(self, parts: list[str], query: dict[str, str]) -> None:
        if len(parts) == 1 and self.command == "GET":
            anchor_date = calendar_anchor_date(query.get("date", ""))
            mini_month_date = calendar_anchor_date(query["mini_date"]) if query.get("mini_date") else anchor_date
            with connect(self.database_path) as connection:
                temporal = calendar_temporal_projection(connection)
                projection_calendars = list(temporal.calendars)
                calendars = [
                    calendar
                    for calendar in projection_calendars
                    if calendar.kind != "external"
                ]
                events = list(temporal.events)
                recurrences = dict(temporal.recurrences)
                recurrence_exceptions = dict(temporal.recurrence_exceptions)
                subscriptions = list_subscriptions(connection, include_disabled=False)
                created_id = self.parse_entity_id(query.get("created", ""))
                created_event = get_event(connection, created_id) if created_id else None
                preview_id = self.parse_entity_id(query.get("preview", ""))
                preview_event = get_event(connection, preview_id) if preview_id else None
                external_preview_id = self.parse_entity_id(query.get("external_preview", ""))
                external_preview = (
                    get_external_projection_event(connection, external_preview_id)
                    if external_preview_id is not None else None
                )
                if external_preview:
                    preview_event = external_preview[0]
                preview_occurrence = query.get("occurrence", "")
            view = query.get("view", "month") if query.get("view") in {"month", "week", "day"} else "month"
            selected_ids = {
                int(item) for item in query.get("calendars", "").split(",")
                if item.lstrip("-").isdigit() and int(item) != 0
            }
            selected_ids = selected_ids or {
                calendar.id for calendar in projection_calendars if not calendar.is_archived
            }
            projection = views.calendar_projection(events, projection_calendars, view=view, anchor_date=anchor_date, selected_calendar_ids=selected_ids, preview_event=preview_event, preview_occurrence=preview_occurrence, recurrences=recurrences, recurrence_exceptions=recurrence_exceptions)
            self.respond_page(
                "Calendar",
                views.calendar_page(calendars, events, return_to=self.path, created_event=created_event, projection=projection),
                active_slug="calendar",
                show_save_toast=created_event is not None or query.get("saved") == "1" or query.get("deleted") == "1",
                sidebar_variant="calendar",
                sidebar_content=views.calendar_sidebar(
                    calendars=calendars,
                    subscriptions=subscriptions,
                    anchor_date=anchor_date,
                    mini_month_date=mini_month_date,
                    view=view,
                    selected_calendar_ids=selected_ids,
                    return_to=self.path,
                ),
                header_content=views.calendar_header(
                    view=view,
                    anchor_date=anchor_date,
                    selected_calendar_ids=selected_ids,
                    return_to=self.calendar_return_to(self.path),
                ),
            )
            return
        if len(parts) == 3 and parts[1] == "order" and self.command == "POST":
            values = self.read_form()
            try:
                ids = [
                    int(item) for item in values.get("ids", "").split(",")
                    if item
                ]
                with connect(self.database_path) as connection:
                    if parts[2] == "local":
                        reorder_calendars(connection, ids)
                    elif parts[2] == "external":
                        reorder_subscriptions(connection, ids)
                    else:
                        self.respond_not_found()
                        return
            except (ValueError, sqlite3.Error) as error:
                self.respond_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if len(parts) >= 2 and parts[1] == "settings":
            self.route_calendar_settings_request(parts, query)
            return
        if len(parts) == 3 and parts[1:] == ["events", "new"]:
            if self.command == "GET":
                with connect(self.database_path) as connection:
                    calendars = list_calendars(connection, include_archived=True)
                values = {**views.default_event_values(calendars), **{key: value for key, value in query.items() if key in {"title", "calendar_id", "all_day", "start_date", "end_date", "start_local", "end_local", "timezone", "notes"}}}
                self.respond_page("Add Event", views.event_form_page(calendars, values, return_to=self.calendar_return_to(query.get("return_to", ""))), active_slug="calendar")
                return
            if self.command == "POST":
                self.handle_calendar_event_create()
                return
        editing_id = self.parse_entity_id(parts[2]) if len(parts) == 4 and parts[1] == "events" and parts[3] == "edit" else None
        reminder_id = self.parse_entity_id(parts[2]) if len(parts) == 4 and parts[1] == "events" and parts[3] == "reminders" else None
        delete_id = self.parse_entity_id(parts[2]) if len(parts) == 4 and parts[1] == "events" and parts[3] == "delete" else None
        if reminder_id is not None:
            if self.command == "GET":
                occurrence_date = query.get("occurrence", "")
                with connect(self.database_path) as connection:
                    event = get_event(connection, reminder_id, include_archived=True)
                    override = get_override(connection, "event", reminder_id, occurrence_date)
                if event is None: self.respond_not_found(); return
                self.respond_page("Event reminder settings", views.reminder_settings_page(event.title, f"/calendar/events/{reminder_id}/edit", override, occurrence_date=occurrence_date), active_slug="calendar")
                return
            if self.command == "POST":
                values = self.read_form()
                try:
                    with connect(self.database_path) as connection:
                        event = get_event(connection, reminder_id, include_archived=True)
                        if event is None:
                            raise ValueError("Event does not exist.")
                        occurrence_date = values.get("occurrence_date", "")
                        scope = values.get("recurrence_scope", "all")
                        custom_timings = self.reminder_timings(values, "custom_reminder")
                        suppressed_timings = self.reminder_timings(values, "suppressed_reminder")
                        settings = {"mode": "custom" if custom_timings or suppressed_timings else "default", "custom_timings": custom_timings, "suppressed_timings": suppressed_timings}
                        definition = get_recurrence(connection, reminder_id)
                        if occurrence_date and definition and scope == "this":
                            set_override(connection, "event", reminder_id, occurrence_key=occurrence_date, **settings)
                        elif occurrence_date and definition and scope == "following" and not is_series_anchor(event, occurrence_date):
                            successor_id = split_series(connection, event, definition, occurrence_date)
                            set_override(connection, "event", successor_id, **settings)
                            self.redirect(f"/calendar/events/{successor_id}/edit?saved=1"); return
                        else:
                            set_override(connection, "event", reminder_id, **settings)
                except ValueError:
                    self.redirect(f"/calendar/events/{reminder_id}/reminders"); return
                self.redirect(f"/calendar/events/{reminder_id}/edit?saved=1"); return
        if delete_id is not None and self.command == "POST":
            with connect(self.database_path) as connection:
                from app.birthday_calendar import person_for_birthday_event
                person_id = person_for_birthday_event(connection, delete_id)
            if person_id is not None:
                self.redirect(f"/people/{person_id}/edit")
                return
            self.handle_calendar_event_delete(delete_id)
            return
        if editing_id is not None and self.command == "GET":
            occurrence_date = query.get("occurrence", "")
            with connect(self.database_path) as connection:
                event = get_event(connection, editing_id, include_archived=True)
                calendars = list_calendars(connection, include_archived=True)
                events = list_events(connection)
                calendar = get_calendar(connection, event.calendar_id, include_archived=True) if event else None
                recurrence = get_recurrence(connection, event.id) if event else None
                exceptions = occurrence_exceptions(connection, recurrence) if recurrence else {}
                from app.birthday_calendar import person_for_birthday_event
                person_id = person_for_birthday_event(connection, editing_id)
            if event is None or calendar is None:
                self.respond_not_found(); return
            if person_id is not None:
                self.redirect(f"/people/{person_id}/edit")
                return
            form_event = event
            if occurrence_date and recurrence:
                try:
                    target = calendar_anchor_date(occurrence_date)
                    matches = occurrences_between(event, recurrence, target, target, exceptions)
                except ValueError:
                    matches = []
                if not matches:
                    self.respond_not_found(); return
                form_event = matches[0].event
            self.respond_page("Edit Event", views.event_form_page(calendars, views.event_form_values(form_event, calendar), editing_event=event, recurrence=recurrence, occurrence_date=occurrence_date if form_event is not event else "", return_to=self.calendar_return_to(query.get("return_to", ""))), active_slug="calendar", show_save_toast=query.get("saved") == "1")
            return
        if editing_id is not None and self.command == "POST":
            self.handle_calendar_event_edit(editing_id)
            return
        self.respond_not_found()

    def route_calendar_settings_request(self, parts: list[str], query: dict[str, str]) -> None:
        return_to = self.calendar_return_to(query.get("return_to", ""))
        if len(parts) == 2 and self.command == "GET":
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
            self.respond_calendar_settings(
                "General",
                views.calendar_settings_general_page(),
                calendars,
                active_section="general",
                return_to=return_to,
            )
            return
        if len(parts) == 3 and parts[2] == "add":
            if self.command == "GET":
                with connect(self.database_path) as connection:
                    calendars = list_calendars(connection, include_archived=True)
                self.respond_calendar_settings(
                    "Create New Calendar",
                    views.calendar_settings_create_page(return_to=return_to),
                    calendars,
                    active_section="add",
                    return_to=return_to,
                )
                return
            if self.command == "POST":
                self.handle_calendar_settings_create()
                return
        if len(parts) == 3 and parts[2] == "discover" and self.command == "GET":
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
            self.respond_calendar_settings(
                "Browse calendars of interest",
                views.calendar_settings_placeholder_page(
                    "Browse calendars of interest",
                    "Optional public calendars such as holidays and moon phases will be available here after their catalogue and update behaviour are designed.",
                ),
                calendars,
                active_section="discover",
                return_to=return_to,
            )
            return
        if len(parts) == 3 and parts[2] == "import":
            if self.command == "GET":
                with connect(self.database_path) as connection:
                    calendars = list_calendars(connection, include_archived=True)
                self.respond_calendar_settings(
                    "Import",
                    views.calendar_settings_import_page(calendars, return_to=return_to),
                    calendars,
                    active_section="import",
                    return_to=return_to,
                    show_save_toast=query.get("saved") == "1",
                )
                return
            if self.command == "POST":
                self.handle_calendar_icalendar_preview()
                return
        if len(parts) == 4 and parts[2:] == ["import", "confirm"] and self.command == "POST":
            self.handle_calendar_icalendar_confirm()
            return
        if len(parts) == 4 and parts[2:] == ["import", "cancel"] and self.command == "POST":
            values = self.read_form()
            try:
                discard_staged_icalendar(values.get("token", ""), self.import_staging_dir)
            except ValueError:
                pass
            self.redirect(self.calendar_settings_url("/import", self.calendar_return_to(values.get("return_to", ""))))
            return
        if len(parts) == 3 and parts[2] == "export":
            if self.command == "GET":
                with connect(self.database_path) as connection:
                    calendars = list_calendars(connection, include_archived=True)
                    subscriptions = list_subscriptions(connection)
                self.respond_calendar_settings(
                    "Export",
                    views.calendar_settings_export_page(
                        calendars, subscriptions, return_to=return_to
                    ),
                    calendars,
                    active_section="export",
                    return_to=return_to,
                )
                return
            if self.command == "POST":
                self.handle_calendar_export()
                return
        if len(parts) == 3 and parts[2] == "from-url":
            if self.command == "GET":
                with connect(self.database_path) as connection:
                    calendars = list_calendars(connection, include_archived=True)
                    subscriptions = list_subscriptions(connection)
                self.respond_calendar_settings(
                    "From URL",
                    views.calendar_settings_from_url_page(
                        subscriptions, return_to=return_to
                    ),
                    calendars,
                    active_section="from-url",
                    return_to=return_to,
                    show_save_toast=query.get("saved") == "1",
                )
                return
            if self.command == "POST":
                self.handle_calendar_subscription_preview()
                return
        if len(parts) == 4 and parts[2:] == ["from-url", "confirm"] and self.command == "POST":
            self.handle_calendar_subscription_confirm()
            return
        managed_subscription_id = (
            self.parse_entity_id(parts[3])
            if len(parts) == 4 and parts[2] == "other-calendars" else None
        )
        if managed_subscription_id is not None and self.command == "GET":
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                source = get_subscription(connection, managed_subscription_id)
                configured = get_policy(
                    connection,
                    "calendar_subscription",
                    managed_subscription_id,
                    "event",
                )
            if source is None:
                self.respond_not_found()
                return
            self.respond_calendar_settings(
                source.name,
                views.calendar_settings_subscription_page(
                    source, configured, return_to=return_to
                ),
                calendars,
                active_section=f"subscription:{source.id}",
                return_to=return_to,
                show_save_toast=query.get("saved") == "1",
            )
            return
        if managed_subscription_id is not None and self.command == "POST":
            self.handle_calendar_subscription_settings_edit(
                managed_subscription_id
            )
            return
        subscription_id = (
            self.parse_entity_id(parts[3])
            if len(parts) == 5 and parts[2] == "other-calendars" else None
        )
        if subscription_id is not None and self.command == "POST":
            self.handle_calendar_subscription_action(subscription_id, parts[4])
            return
        managed_id = self.parse_entity_id(parts[3]) if len(parts) in {4, 5} and parts[2] == "calendars" else None
        if managed_id is None:
            self.respond_not_found()
            return
        if len(parts) == 4 and self.command == "GET":
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                calendar = get_calendar(connection, managed_id, include_archived=True)
                configured = get_policy(connection, "calendar", managed_id, "event")
            if calendar is None:
                self.respond_not_found()
                return
            self.respond_calendar_settings(
                calendar.name,
                views.calendar_settings_edit_page(calendar, configured, return_to=return_to),
                calendars,
                active_section=f"calendar:{managed_id}",
                return_to=return_to,
                show_save_toast=query.get("saved") == "1",
            )
            return
        if len(parts) == 4 and self.command == "POST":
            self.handle_calendar_settings_edit(managed_id)
            return
        if len(parts) == 5 and self.command == "POST" and parts[4] in {"default", "archive", "unarchive", "delete"}:
            self.handle_calendar_settings_action(managed_id, parts[4])
            return
        self.respond_not_found()

    def handle_calendar_event_create(self) -> None:
        values = self.read_form()
        try:
            with connect(self.database_path) as connection:
                event_id = create_event(connection, event_input_from_form(values))
                event = get_event(connection, event_id, include_archived=True)
                rule = recurrence_rule_from_form(values, event)
                if rule is not None:
                    set_recurrence(connection, event, rule)
        except (ValueError, sqlite3.Error) as error:
            self.respond_calendar_event_form(values, [str(error)])
            return
        self.redirect(self.calendar_return_url(values.get("return_to", ""), f"created={event_id}"))

    @staticmethod
    def calendar_return_to(value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc or parsed.path != "/calendar":
            return "/calendar"
        return f"/calendar?{parsed.query}" if parsed.query else "/calendar"

    def calendar_return_url(self, value: str, marker: str) -> str:
        destination = self.calendar_return_to(value)
        return f"{destination}{'&' if '?' in destination else '?'}{marker}"

    @staticmethod
    def calendar_settings_url(path: str, return_to: str, *, saved: bool = False) -> str:
        parameters = [("return_to", return_to)]
        if saved:
            parameters.append(("saved", "1"))
        return f"/calendar/settings{path}?{urlencode(parameters)}"

    def handle_calendar_settings_create(self) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            with connect(self.database_path) as connection:
                calendar_id = create_calendar(
                    connection,
                    CalendarInput(
                        name=values.get("name", ""),
                        colour=values.get("colour", DEFAULT_CALENDAR_COLOUR),
                        timezone=PLATFORM_TIMEZONE,
                        default_event_duration_minutes=DEFAULT_EVENT_DURATION_MINUTES,
                        sort_order=next_calendar_sort_order(connection),
                    ),
                )
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
            self.respond_calendar_settings(
                "Create New Calendar",
                views.calendar_settings_create_page([str(error)], return_to=return_to),
                calendars,
                active_section="add",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.redirect(self.calendar_settings_url(f"/calendars/{calendar_id}", return_to, saved=True))

    def handle_calendar_icalendar_preview(self) -> None:
        values: dict[str, str] = {}
        return_to = "/calendar"
        try:
            if int(self.headers.get("Content-Length", "0")) > 2_200_000:
                raise ValueError("Calendar import upload exceeds the supported request size.")
            values, upload = self.read_multipart_form()
            return_to = self.calendar_return_to(values.get("return_to", ""))
            if upload is None:
                raise ValueError("Choose an iCalendar file to import.")
            suffix = Path(upload.file_name).suffix.lower()
            if suffix not in {".ics", ".ical"} and upload.content_type != "text/calendar":
                raise ValueError("Choose an .ics or .ical iCalendar file.")
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                preview = inspect_icalendar_import(
                    connection, upload.data, filename=upload.file_name
                )
            token = stage_icalendar(upload.data, self.import_staging_dir)
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
            self.respond_calendar_settings(
                "Import",
                views.calendar_settings_import_page(
                    calendars, errors=[str(error)], return_to=return_to
                ),
                calendars,
                active_section="import",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.respond_calendar_settings(
            "Import preview",
            views.calendar_settings_import_page(
                calendars,
                preview=preview,
                token=token,
                return_to=return_to,
            ),
            calendars,
            active_section="import",
            return_to=return_to,
        )

    def handle_calendar_icalendar_confirm(self) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            content = read_staged_icalendar(
                values.get("token", ""), self.import_staging_dir, consume=True
            )
            with connect(self.database_path) as connection:
                if values.get("destination_mode", "existing") == "new":
                    new_calendar = new_import_calendar_input(
                        connection,
                        values.get("new_name", ""),
                        values.get("new_colour", DEFAULT_EXTERNAL_CALENDAR_COLOUR),
                        values.get("new_timezone", PLATFORM_TIMEZONE),
                    )
                    result = apply_icalendar_import(
                        connection, content, new_calendar=new_calendar
                    )
                    destination_path = (
                        f"/calendars/{result.calendar_id}"
                        if result.calendar_id else "/import"
                    )
                else:
                    calendar_id = self.parse_entity_id(values.get("calendar_id", ""))
                    if calendar_id is None:
                        raise ValueError("Choose an existing destination Calendar.")
                    result = apply_icalendar_import(
                        connection,
                        content,
                        destination_calendar_id=calendar_id,
                    )
                    destination_path = "/import"
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
            self.respond_calendar_settings(
                "Import",
                views.calendar_settings_import_page(
                    calendars, errors=[str(error)], return_to=return_to
                ),
                calendars,
                active_section="import",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.redirect(self.calendar_settings_url(destination_path, return_to, saved=True))

    def handle_calendar_export(self) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        selections = [item for item in values.get("sources", "").split(",") if item]
        try:
            with connect(self.database_path) as connection:
                content = create_calendar_export(connection, selections)
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                subscriptions = list_subscriptions(connection)
            self.respond_calendar_settings(
                "Export",
                views.calendar_settings_export_page(
                    calendars,
                    subscriptions,
                    errors=[str(error)],
                    return_to=return_to,
                ),
                calendars,
                active_section="export",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header(
            "Content-Disposition",
            'attachment; filename="project-e-calendars.zip"',
        )
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_calendar_subscription_preview(self) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            fetched = fetch_subscription(values.get("url", ""))
            token = stage_subscription_fetch(fetched, self.import_staging_dir)
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                subscriptions = list_subscriptions(connection)
            self.respond_calendar_settings(
                "From URL",
                views.calendar_settings_from_url_page(
                    subscriptions, errors=[str(error)], return_to=return_to
                ),
                calendars,
                active_section="from-url",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        with connect(self.database_path) as connection:
            calendars = list_calendars(connection, include_archived=True)
            subscriptions = list_subscriptions(connection)
        self.respond_calendar_settings(
            "From URL preview",
            views.calendar_settings_from_url_page(
                subscriptions,
                preview=fetched,
                token=token,
                return_to=return_to,
            ),
            calendars,
            active_section="from-url",
            return_to=return_to,
        )

    def handle_calendar_subscription_confirm(self) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            fetched = read_staged_subscription(
                values.get("token", ""), self.import_staging_dir, consume=True
            )
            with connect(self.database_path) as connection:
                subscription_id = create_subscription(
                    connection,
                    fetched,
                    colour=values.get("colour", DEFAULT_EXTERNAL_CALENDAR_COLOUR),
                    display_name=values.get("display_name", ""),
                )
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                subscriptions = list_subscriptions(connection)
            self.respond_calendar_settings(
                "From URL",
                views.calendar_settings_from_url_page(
                    subscriptions, errors=[str(error)], return_to=return_to
                ),
                calendars,
                active_section="from-url",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.redirect(self.calendar_settings_url(
            f"/other-calendars/{subscription_id}", return_to, saved=True
        ))

    def handle_calendar_subscription_settings_edit(
        self,
        subscription_id: int,
    ) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            reminder_timings = self.reminder_timings(
                values, "calendar_reminder"
            )
            with connect(self.database_path) as connection:
                update_subscription_settings(
                    connection,
                    subscription_id,
                    SubscriptionSettingsInput(
                        values.get("name", ""),
                        values.get("colour", DEFAULT_EXTERNAL_CALENDAR_COLOUR),
                        values.get("timezone", PLATFORM_TIMEZONE),
                    ),
                )
                if reminder_timings:
                    set_policy(
                        connection,
                        "calendar_subscription",
                        subscription_id,
                        "event",
                        reminder_timings,
                    )
                else:
                    clear_policy(
                        connection,
                        "calendar_subscription",
                        subscription_id,
                        "event",
                    )
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                source = get_subscription(connection, subscription_id)
                configured = get_policy(
                    connection,
                    "calendar_subscription",
                    subscription_id,
                    "event",
                )
            if source is None:
                self.respond_not_found()
                return
            self.respond_calendar_settings(
                source.name,
                views.calendar_settings_subscription_page(
                    source,
                    configured,
                    errors=[str(error)],
                    return_to=return_to,
                ),
                calendars,
                active_section=f"subscription:{source.id}",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.redirect(self.calendar_settings_url(
            f"/other-calendars/{subscription_id}", return_to, saved=True
        ))

    def handle_calendar_subscription_action(self, subscription_id: int, action: str) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            with connect(self.database_path) as connection:
                if action == "refresh":
                    refresh_subscription(connection, subscription_id)
                elif action == "enable":
                    set_subscription_enabled(connection, subscription_id, True)
                elif action == "disable":
                    set_subscription_enabled(connection, subscription_id, False)
                elif action == "remove":
                    remove_subscription(connection, subscription_id)
                else:
                    self.respond_not_found()
                    return
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                subscriptions = list_subscriptions(connection)
            self.respond_calendar_settings(
                "From URL",
                views.calendar_settings_from_url_page(
                    subscriptions, errors=[str(error)], return_to=return_to
                ),
                calendars,
                active_section="from-url",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        destination = (
            "/from-url" if action == "remove"
            else f"/other-calendars/{subscription_id}"
        )
        self.redirect(self.calendar_settings_url(
            destination, return_to, saved=True
        ))

    def handle_calendar_settings_edit(self, calendar_id: int) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            reminder_timings = self.reminder_timings(values, "calendar_reminder")
            with connect(self.database_path) as connection:
                current = get_calendar(connection, calendar_id, include_archived=True)
                if current is None:
                    raise ValueError("Calendar does not exist.")
                update_calendar(
                    connection,
                    calendar_id,
                    CalendarInput(
                        values.get("name", ""),
                        values.get("colour", DEFAULT_CALENDAR_COLOUR),
                        values.get("timezone", PLATFORM_TIMEZONE),
                        int(values.get("default_event_duration_minutes", str(DEFAULT_EVENT_DURATION_MINUTES))),
                        current.sort_order,
                        current.kind,
                    ),
                )
                if not reminder_timings:
                    clear_policy(connection, "calendar", calendar_id, "event")
                else:
                    set_policy(connection, "calendar", calendar_id, "event", reminder_timings)
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                calendar = get_calendar(connection, calendar_id, include_archived=True)
                configured = get_policy(connection, "calendar", calendar_id, "event")
            if calendar is None:
                self.respond_not_found(); return
            self.respond_calendar_settings(
                calendar.name,
                views.calendar_settings_edit_page(calendar, configured, [str(error)], return_to=return_to),
                calendars,
                active_section=f"calendar:{calendar_id}",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        self.redirect(self.calendar_settings_url(f"/calendars/{calendar_id}", return_to, saved=True))

    def handle_calendar_settings_action(self, calendar_id: int, action: str) -> None:
        values = self.read_form()
        return_to = self.calendar_return_to(values.get("return_to", ""))
        try:
            with connect(self.database_path) as connection:
                if action == "default":
                    set_default_calendar(connection, calendar_id)
                elif action == "archive":
                    archive_calendar(connection, calendar_id)
                elif action == "unarchive":
                    unarchive_calendar(connection, calendar_id)
                else:
                    delete_calendar(connection, calendar_id)
        except (ValueError, sqlite3.Error) as error:
            with connect(self.database_path) as connection:
                calendars = list_calendars(connection, include_archived=True)
                calendar = get_calendar(connection, calendar_id, include_archived=True)
                configured = get_policy(connection, "calendar", calendar_id, "event")
            if calendar is None:
                self.respond_not_found()
                return
            self.respond_calendar_settings(
                calendar.name,
                views.calendar_settings_edit_page(calendar, configured, [str(error)], return_to=return_to),
                calendars,
                active_section=f"calendar:{calendar_id}",
                return_to=return_to,
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        destination = "" if action == "delete" else f"/calendars/{calendar_id}"
        self.redirect(self.calendar_settings_url(destination, return_to, saved=True))

    def handle_reminder_policy(self, context_kind: str, context_id: int, source_kind: str, title: str, back_url: str, *, active_slug: str) -> None:
        if self.command == "GET":
            with connect(self.database_path) as connection:
                configured = get_policy(connection, context_kind, context_id, source_kind)
            self.respond_page(title, views.reminder_policy_page(title, back_url, configured_timings=configured, inherited_timings=DEFAULT_TIMINGS[source_kind]), active_slug=active_slug)
            return
        if self.command == "POST":
            values = self.read_form()
            try:
                with connect(self.database_path) as connection:
                    if values.get("mode") == "inherit":
                        clear_policy(connection, context_kind, context_id, source_kind)
                    else:
                        timings = self.reminder_timings(values, "policy_reminder")
                        if not timings:
                            raise ValueError("Add at least one notification time or restore inheritance.")
                        set_policy(connection, context_kind, context_id, source_kind, timings)
            except ValueError:
                if context_kind == "calendar":
                    retry_url = f"/calendar/settings/calendars/{context_id}"
                else:
                    retry_url = f"/inbox/reminders/{'birthdays' if source_kind == 'birthday' else 'document-expiries'}"
                self.redirect(retry_url)
                return
            self.redirect(back_url)
            return
        self.respond_not_found()

    def handle_calendar_event_edit(self, event_id: int) -> None:
        values = self.read_form()
        try:
            with connect(self.database_path) as connection:
                from app.birthday_calendar import person_for_birthday_event
                person_id = person_for_birthday_event(connection, event_id)
                if person_id is not None:
                    self.redirect(f"/people/{person_id}/edit")
                    return
                event = get_event(connection, event_id, include_archived=True)
                if event is None:
                    self.respond_not_found(); return
                event_input = event_input_from_form(values)
                definition = get_recurrence(connection, event_id)
                occurrence_date = values.get("occurrence_date", "")
                scope = values.get("recurrence_scope", "all")
                if occurrence_date and definition and scope == "this":
                    override_occurrence(connection, event, definition, occurrence_date, event_input)
                elif occurrence_date and definition and scope == "following" and not is_series_anchor(event, occurrence_date):
                    rule = recurrence_rule_from_form(values, event, definition.rule)
                    successor_id = split_series(connection, event, definition, occurrence_date, rule, event_input)
                    self.redirect(f"/calendar/events/{successor_id}/edit?saved=1")
                    return
                else:
                    update_event(connection, event_id, EventUpdate(event_input.title, event_input.calendar_id, event_input.notes))
                    reschedule_event(connection, event_id, EventSchedule(event_input.all_day, event_input.timezone, event_input.start_local, event_input.end_local, start_date=event_input.start_date, end_date=event_input.end_date))
                    updated = get_event(connection, event_id, include_archived=True)
                    rule = recurrence_rule_from_form(values, updated, definition.rule if definition else None)
                    if rule is None:
                        remove_recurrence(connection, event_id)
                    else:
                        set_recurrence(connection, updated, rule)
        except (ValueError, sqlite3.Error) as error:
            self.respond_calendar_event_form(values, [str(error)], event_id)
            return
        self.redirect(self.calendar_return_url(values.get("return_to", ""), "saved=1"))

    def handle_calendar_event_delete(self, event_id: int) -> None:
        values = self.read_form()
        with connect(self.database_path) as connection:
            event = get_event(connection, event_id, include_archived=True)
            if event is None:
                self.respond_not_found()
                return
            definition = get_recurrence(connection, event_id)
            occurrence_date = values.get("occurrence_date", "")
            scope = values.get("recurrence_scope", "all")
            if occurrence_date and definition and scope == "this":
                cancel_occurrence(connection, definition, occurrence_date)
            elif occurrence_date and definition and scope == "following":
                if is_series_anchor(event, occurrence_date):
                    delete_entity(connection, EVENT_DEFINITION, event_id)
                else:
                    truncate_series(connection, event, definition, occurrence_date)
            else:
                delete_entity(connection, EVENT_DEFINITION, event_id)
        self.redirect(self.calendar_return_url(values.get("return_to", ""), "deleted=1"))

    def respond_calendar_event_form(self, values: dict[str, str], errors: list[str], event_id: int | None = None) -> None:
        with connect(self.database_path) as connection:
            calendars = list_calendars(connection, include_archived=True)
            events = list_events(connection)
            event = get_event(connection, event_id, include_archived=True) if event_id else None
        self.respond_page("Edit Event" if event else "Add Event", views.event_form_page(calendars, values, editing_event=event, errors=errors, return_to=self.calendar_return_to(values.get("return_to", ""))), HTTPStatus.BAD_REQUEST, active_slug="calendar")

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

    def route_scheduled_jobs(self, parts: list[str]) -> None:
        if len(parts) == 2 and self.command == "GET":
            with connect(self.database_path) as connection:
                ensure_registered_jobs(connection)
                jobs = list_scheduled_jobs(connection)
                runs = {job.id: list_job_runs(connection, job.id) for job in jobs}
            self.respond_page("Scheduled Jobs", views.scheduled_jobs_page(jobs, runs), active_slug="system-tools")
            return
        job_id = self.parse_entity_id(parts[2]) if len(parts) == 4 else None
        if job_id is not None and self.command == "POST":
            with connect(self.database_path) as connection:
                if parts[3] == "run":
                    run_job_now(connection, job_id)
                elif parts[3] == "rerun":
                    run_job_now(connection, job_id, rerun=True)
                elif parts[3] in {"enable", "disable"}:
                    set_job_enabled(connection, job_id, parts[3] == "enable")
                else:
                    self.respond_not_found()
                    return
            self.redirect("/system-tools/jobs")
            return
        self.respond_not_found()

    def route_automation(self, parts: list[str]) -> None:
        if len(parts) == 4 and self.command == "POST" and parts[3] in {"enable", "disable"}:
            rule_id = self.parse_entity_id(parts[2])
            if rule_id is None:
                self.respond_not_found(); return
            with connect(self.database_path) as connection:
                set_rule_enabled(connection, rule_id, parts[3] == "enable")
            self.redirect("/system-tools/automation")
            return
        if len(parts) == 2 and self.command == "GET":
            with connect(self.database_path) as connection:
                ensure_registered_rules(connection)
                rules = list_rules(connection)
                runs = {rule.id: list_runs(connection, rule.id) for rule in rules}
            self.respond_page("Deterministic automation", views.automation_page(rules, runs), active_slug="system-tools")
            return
        self.respond_not_found()

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
        search_query = query.get("q", "").strip()
        provider_requested = query.get("online") == "1" and bool(search_query)
        provider_results = []
        provider_error = ""
        if provider_requested:
            try:
                provider_results = geocoder().search(search_query, limit=5)
            except Exception:
                provider_error = "unavailable"
        with connect(self.database_path) as connection:
            payload = build_map_payload(
                connection,
                search_query,
                provider_results=provider_results,
                provider_requested=provider_requested,
                provider_error=provider_error,
                spatial_pack_root=self.spatial_pack_dir,
            )
        self.respond_page(
            "Map",
            views.map_page(
                payload,
                query.get("entity_id", ""),
                selected_key=query.get("selected", ""),
            ),
            active_slug="map",
            show_save_toast=bool(query.get("saved")),
        )

    def handle_walking_journey(self, query: dict[str, str]) -> None:
        values = default_walking_form_values()
        values.update(
            {
                key: query[key]
                for key in ("origin", "destination")
                if query.get(key)
            }
        )
        self._respond_walking_journey(values)

    def handle_walking_journey_plan(self) -> None:
        values = self.read_form()
        execution = None
        errors: list[str] = []
        try:
            request = walking_request_from_form(values)
            capability = load_active_valhalla_capability(
                self.routing_dir, self.spatial_pack_dir
            )
            adapter = ValhallaWalkingAdapter(capability)
            cache = JourneyCache(
                self.journey_cache_path,
                maximum_entries=capability.maximum_cache_entries,
            )
            with connect(self.database_path) as connection:
                ensure_default_walk_profile(connection)
                execution = plan_journey(
                    connection, request, adapter, cache=cache
                )
        except (OSError, sqlite3.Error, ValueError) as error:
            errors.append(str(error))
        self._respond_walking_journey(
            values,
            execution=execution,
            errors=errors,
            status=HTTPStatus.BAD_REQUEST if errors else HTTPStatus.OK,
        )

    def _respond_walking_journey(
        self,
        values: dict[str, str],
        *,
        execution=None,
        errors: list[str] | None = None,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        routing_status = routing_capability_status(
            self.routing_dir, self.spatial_pack_dir
        )
        with connect(self.database_path) as connection:
            ensure_default_walk_profile(connection)
            endpoints = list_journey_endpoint_options(connection)
            profiles = list_mobility_profiles(connection)
            policies = list_routing_policies(connection)
            payload = build_map_payload(
                connection,
                spatial_pack_root=self.spatial_pack_dir,
            )
        overlay = views.journey_overlay_payload(
            execution.result if execution is not None else None
        )
        if overlay is not None:
            payload["journeyOverlay"] = overlay
            for layer in payload["contextLayers"]:
                if layer["id"] == "journey-routes":
                    layer.update(
                        available=True,
                        enabled=True,
                        explanation="The current calculated route is shown as a temporary Map overlay.",
                    )
        sidebar = views.walking_journey_panel(
            endpoints,
            profiles,
            policies,
            routing_status,
            values,
            execution=execution,
            errors=errors,
        )
        self.respond_page(
            "Walking journey",
            views.map_page(
                payload,
                sidebar_html=sidebar,
                workspace_title="Walking journey",
                workspace_eyebrow="N6 · local walking",
                workspace_description=(
                    "Calculate between deliberate canonical access points without "
                    "creating an Event or sending private records online."
                ),
            ),
            status,
            active_slug="map",
        )

    def handle_walking_settings(self, query: dict[str, str]) -> None:
        self._respond_walking_settings(saved=query.get("saved", ""))

    def _respond_walking_settings(
        self,
        *,
        errors: list[str] | None = None,
        status: HTTPStatus = HTTPStatus.OK,
        saved: str = "",
    ) -> None:
        with connect(self.database_path) as connection:
            ensure_default_walk_profile(connection)
            profiles = list_mobility_profiles(connection)
            policies = list_routing_policies(connection)
        avoid_steps = next(
            (
                policy
                for policy in policies
                if policy.policy_key == AVOID_STEPS_POLICY_KEY
            ),
            None,
        )
        self.respond_page(
            "Walking settings",
            views.walking_settings_page(
                profiles, avoid_steps, errors=errors, saved=saved
            ),
            status,
            active_slug="map",
        )

    def handle_walking_avoid_steps(self) -> None:
        values = self.read_form()
        try:
            enabled = values.get("enabled") == "1"
            with connect(self.database_path) as connection:
                policy = configure_avoid_steps_policy(
                    connection, enabled=enabled
                )
        except (sqlite3.Error, ValueError) as error:
            self._respond_walking_settings(
                errors=[str(error)], status=HTTPStatus.BAD_REQUEST
            )
            return
        state = "enabled" if policy.is_enabled else "disabled"
        self.redirect(
            "/journeys/walk/settings?"
            + urlencode({"saved": f"Avoid-steps preference {state}."})
        )

    def handle_map_coverage_recommendation(self, query: dict[str, str]) -> None:
        return_to = self.map_return_to(query.get("return_to", ""))
        try:
            recommendation = assess_map_coverage(
                self.spatial_pack_dir,
                selection_title=query.get("title", ""),
                latitude=query.get("latitude", ""),
                longitude=query.get("longitude", ""),
            )
        except ValueError as error:
            self.respond_page(
                "Coverage context unavailable",
                views.map_coverage_error_page(str(error), return_to),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.respond_page(
            "Improve coverage",
            views.map_coverage_recommendation_page(recommendation, return_to),
            active_slug="map",
        )

    def handle_map_provider_location_review(self) -> None:
        values = self.read_form()
        return_to = self.map_return_to(values.get("return_to", ""))
        try:
            feature = provider_feature_from_form(values, self.spatial_pack_dir)
            with connect(self.database_path) as connection:
                matches = find_provider_promotion_matches(connection, feature)
        except (OSError, ValueError) as error:
            self.respond_page(
                "Provider feature unavailable",
                views.map_provider_feature_error_page(str(error), return_to),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.respond_page(
            "Review Save as Location",
            views.map_provider_review_page(feature, matches, return_to),
            active_slug="map",
        )

    def handle_map_provider_location_save(self) -> None:
        values = self.read_form()
        return_to = self.map_return_to(values.get("return_to", ""))
        try:
            feature = provider_feature_from_form(values, self.spatial_pack_dir)
        except (OSError, ValueError) as error:
            self.respond_page(
                "Provider feature unavailable",
                views.map_provider_feature_error_page(str(error), return_to),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        try:
            with connect(self.database_path) as connection:
                location_id, _created = promote_provider_feature(
                    connection,
                    feature,
                    choice=values.get("choice", ""),
                    display_name=values.get("display_name", ""),
                )
        except (sqlite3.Error, ValueError) as error:
            with connect(self.database_path) as connection:
                matches = find_provider_promotion_matches(connection, feature)
            self.respond_page(
                "Review Save as Location",
                views.map_provider_review_page(
                    feature, matches, return_to, errors=[str(error)]
                ),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.redirect(f"/locations/{location_id}?saved=1")

    def handle_map_feature_lists(self) -> None:
        with connect(self.database_path) as connection:
            feature_lists = list_map_feature_lists(connection)
        self.respond_page(
            "Map lists",
            views.map_feature_lists_page(feature_lists),
            active_slug="map",
        )

    def handle_map_feature_list_create(self) -> None:
        values = self.read_form()
        try:
            with connect(self.database_path) as connection:
                list_id = create_map_feature_list(connection, values.get("name", ""))
        except ValueError as error:
            with connect(self.database_path) as connection:
                feature_lists = list_map_feature_lists(connection)
            self.respond_page(
                "Map lists",
                views.map_feature_lists_page(feature_lists, errors=[str(error)]),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.redirect(f"/map/lists/{list_id}?saved=1")

    def handle_map_feature_list_add(self) -> None:
        values = self.read_form()
        return_to = self.map_return_to(values.get("return_to", ""))
        try:
            list_id = int(values.get("list_id", ""))
            feature = provider_feature_from_form(values, self.spatial_pack_dir)
            with connect(self.database_path) as connection:
                add_map_feature_membership(connection, list_id, feature)
        except (OSError, sqlite3.Error, TypeError, ValueError) as error:
            self.respond_page(
                "Map feature not saved",
                views.map_provider_feature_error_page(str(error), return_to),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        delimiter = "&" if "?" in return_to else "?"
        self.redirect(f"{return_to}{delimiter}saved=1")

    def handle_map_feature_list(self, raw_id: str) -> None:
        list_id = self.parse_entity_id(raw_id)
        if list_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            feature_list = get_map_feature_list(connection, list_id)
            memberships = (
                list_map_feature_memberships(connection, list_id)
                if feature_list is not None
                else []
            )
        if feature_list is None:
            self.respond_not_found()
            return
        membership_views = self.map_feature_membership_views(memberships)
        parsed = urlparse(self.path)
        saved = parse_qs(parsed.query).get("saved", [""])[0]
        self.respond_page(
            feature_list.name,
            views.map_feature_list_page(feature_list, membership_views),
            active_slug="map",
            show_save_toast=bool(saved),
        )

    def handle_map_feature_list_export(self, raw_id: str) -> None:
        list_id = self.parse_entity_id(raw_id)
        if list_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            feature_list = get_map_feature_list(connection, list_id)
            memberships = (
                list_map_feature_memberships(connection, list_id)
                if feature_list is not None
                else []
            )
        if feature_list is None:
            self.respond_not_found()
            return
        content = json.dumps(
            map_feature_membership_export(feature_list, memberships),
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header(
            "Content-Disposition", f'attachment; filename="map-list-{list_id}.json"'
        )
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_map_feature_list_clear(self, raw_id: str) -> None:
        list_id = self.parse_entity_id(raw_id)
        if list_id is None:
            self.respond_not_found()
            return
        values = self.read_form()
        if values.get("confirm") != "CLEAR":
            self.respond_map_feature_list_error(
                list_id, "Type CLEAR to confirm removing every membership."
            )
            return
        try:
            with connect(self.database_path) as connection:
                clear_map_feature_list(connection, list_id)
        except ValueError as error:
            self.respond_map_feature_list_error(list_id, str(error))
            return
        self.redirect(f"/map/lists/{list_id}?saved=1")

    def handle_map_feature_list_remove(self, raw_id: str) -> None:
        list_id = self.parse_entity_id(raw_id)
        if list_id is None:
            self.respond_not_found()
            return
        values = self.read_form()
        membership_id = self.parse_entity_id(values.get("membership_id", ""))
        if membership_id is None:
            self.respond_map_feature_list_error(list_id, "The Map-list membership is invalid.")
            return
        with connect(self.database_path) as connection:
            removed = remove_map_feature_membership(
                connection, list_id, membership_id
            )
        if not removed:
            self.respond_map_feature_list_error(
                list_id, "The Map-list membership no longer exists."
            )
            return
        self.redirect(f"/map/lists/{list_id}?saved=1")

    def respond_map_feature_list_error(self, list_id: int, message: str) -> None:
        with connect(self.database_path) as connection:
            feature_list = get_map_feature_list(connection, list_id)
            memberships = (
                list_map_feature_memberships(connection, list_id)
                if feature_list is not None
                else []
            )
        if feature_list is None:
            self.respond_not_found()
            return
        self.respond_page(
            feature_list.name,
            views.map_feature_list_page(
                feature_list,
                self.map_feature_membership_views(memberships),
                errors=[message],
            ),
            HTTPStatus.BAD_REQUEST,
            active_slug="map",
        )

    def map_feature_membership_views(self, memberships) -> list[dict[str, object]]:
        status = spatial_pack_status(self.spatial_pack_dir)
        result = []
        for membership in memberships:
            current = read_active_search_feature(
                self.spatial_pack_dir,
                membership.provider_key,
                membership.feature_id,
            )
            revisit_url = ""
            if current is not None:
                selected = installed_provider_selection_key(
                    str(current["pack_id"]), membership.feature_id
                )
                revisit_url = "/map?" + urlencode(
                    {"q": str(current["title"]), "selected": selected}
                )
                explanation = ""
            elif membership.provider_key == "nominatim-osm":
                revisit_url = "/map?" + urlencode(
                    {"q": membership.user_label, "online": "1"}
                )
                explanation = (
                    "Online provider data is never loaded from a saved list automatically."
                )
            elif membership.provider_key.startswith("spatial-pack:"):
                expected_pack = membership.provider_key.removeprefix("spatial-pack:")
                if status.active is None:
                    explanation = (
                        "The required spatial pack is not active; portable membership remains."
                    )
                elif status.active.manifest.pack_id != expected_pack:
                    explanation = (
                        "A different region pack is active; portable membership remains."
                    )
                else:
                    explanation = (
                        "The active provider version no longer exposes this feature identity; "
                        "the membership was not silently reassigned."
                    )
            else:
                explanation = "The saved provider is not currently available."
            result.append(
                {
                    "membership": membership,
                    "current": current,
                    "revisitUrl": revisit_url,
                    "explanation": explanation,
                }
            )
        return result

    @staticmethod
    def map_return_to(value: str) -> str:
        if not value or len(value) > 2000:
            return "/map"
        parsed = urlparse(value)
        if (
            parsed.scheme
            or parsed.netloc
            or not (parsed.path == "/map" or parsed.path.startswith("/map/"))
        ):
            return "/map"
        return parsed.path + (f"?{parsed.query}" if parsed.query else "")

    def handle_map_viewport(self, query: dict[str, str]) -> None:
        try:
            bounds = {
                name: float(query[name])
                for name in ("west", "south", "east", "north")
            }
            raw_layers = query.get("layers", "")
            layer_ids = (
                set()
                if raw_layers == "none"
                else {item for item in raw_layers.split(",") if item}
            )
            with connect(self.database_path) as connection:
                payload = build_map_viewport_payload(
                    connection,
                    **bounds,
                    layer_ids=layer_ids,
                    request_token=query.get("request", ""),
                )
            self.respond_json(payload)
        except (KeyError, TypeError, ValueError):
            self.respond_json(
                {"error": "Valid bounded viewport coordinates are required."},
                status=HTTPStatus.BAD_REQUEST,
            )

    def handle_spatial_pack_manager(self, query: dict[str, str]) -> None:
        status = spatial_pack_status(self.spatial_pack_dir)
        saved = query.get("saved", "")
        self.respond_page(
            "Spatial Packs",
            views.spatial_pack_page(status, saved=saved),
            active_slug="map",
            show_save_toast=bool(saved),
        )

    def handle_spatial_pack_preview(self) -> None:
        status = spatial_pack_status(self.spatial_pack_dir)
        try:
            _values, upload = self.read_multipart_form(
                max_bytes=MAX_ARCHIVE_BYTES + 1024 * 1024
            )
            if upload is None:
                raise ValueError("Choose a spatial-pack ZIP file to inspect.")
            preview = inspect_and_stage_spatial_pack(
                upload.data, self.spatial_pack_dir
            )
        except (OSError, ValueError) as error:
            self.respond_page(
                "Spatial Packs",
                views.spatial_pack_page(status, errors=[str(error)]),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.respond_page(
            "Inspect Spatial Pack",
            views.spatial_pack_page(status, preview=preview),
            active_slug="map",
        )

    def handle_spatial_pack_activate(self) -> None:
        values = self.read_form()
        try:
            preview = read_staged_spatial_pack(
                values.get("token", ""), self.spatial_pack_dir
            )
            before = spatial_pack_status(self.spatial_pack_dir).active
            active = activate_staged_spatial_pack(
                values.get("token", ""), self.spatial_pack_dir
            )
            with connect(self.database_path) as connection:
                record_audit_event(
                    connection,
                    "import",
                    [("spatial_pack", 0)],
                    before=(
                        {
                            "pack_id": before.manifest.pack_id,
                            "version": before.manifest.pack_version,
                        }
                        if before
                        else None
                    ),
                    after={
                        "pack_id": active.manifest.pack_id,
                        "version": active.manifest.pack_version,
                        "coverage": active.manifest.coverage_label,
                    },
                    notes="Verified local spatial pack activated",
                    provenance="imported",
                )
                connection.commit()
        except (OSError, ValueError) as error:
            self.respond_page(
                "Spatial Packs",
                views.spatial_pack_page(
                    spatial_pack_status(self.spatial_pack_dir),
                    preview=preview if "preview" in locals() else None,
                    errors=[str(error)],
                ),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.redirect("/map/packs?saved=installed")

    def handle_spatial_pack_rollback(self) -> None:
        before = spatial_pack_status(self.spatial_pack_dir).active
        try:
            active = rollback_spatial_pack(self.spatial_pack_dir)
            with connect(self.database_path) as connection:
                record_audit_event(
                    connection,
                    "edit",
                    [("spatial_pack", 0)],
                    before={"version": before.manifest.pack_version} if before else None,
                    after={"version": active.manifest.pack_version},
                    notes="Local spatial pack rolled back to a validated version",
                )
                connection.commit()
        except (OSError, ValueError) as error:
            self.respond_page(
                "Spatial Packs",
                views.spatial_pack_page(
                    spatial_pack_status(self.spatial_pack_dir), errors=[str(error)]
                ),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.redirect("/map/packs?saved=rolled-back")

    def handle_spatial_pack_remove(self) -> None:
        values = self.read_form()
        if values.get("confirm") != "REMOVE":
            self.respond_page(
                "Spatial Packs",
                views.spatial_pack_page(
                    spatial_pack_status(self.spatial_pack_dir),
                    errors=["Type REMOVE to confirm spatial-pack removal."],
                ),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        try:
            removed = remove_spatial_pack(self.spatial_pack_dir)
            with connect(self.database_path) as connection:
                record_audit_event(
                    connection,
                    "delete",
                    [("spatial_pack", 0)],
                    before=removed,
                    notes="Replaceable local spatial pack removed; canonical data retained",
                )
                connection.commit()
        except (OSError, ValueError) as error:
            self.respond_page(
                "Spatial Packs",
                views.spatial_pack_page(
                    spatial_pack_status(self.spatial_pack_dir), errors=[str(error)]
                ),
                HTTPStatus.BAD_REQUEST,
                active_slug="map",
            )
            return
        self.redirect("/map/packs?saved=removed")

    def handle_spatial_pack_tile(
        self, activation_id: str, raw_zoom: str, raw_x: str, raw_y: str
    ) -> None:
        if not (raw_zoom.isdigit() and raw_x.isdigit() and raw_y.isdigit()):
            self.respond_not_found()
            return
        tile = read_active_tile(
            self.spatial_pack_dir,
            activation_id,
            int(raw_zoom),
            int(raw_x),
            int(raw_y),
        )
        if tile is None:
            self.respond_not_found()
            return
        content, gzipped = tile
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.mapbox-vector-tile")
        if gzipped:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_spatial_pack_coverage(self, activation_id: str) -> None:
        content = read_active_coverage(self.spatial_pack_dir, activation_id)
        if content is None:
            self.respond_not_found()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/geo+json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_spatial_pack_public_transport(self, activation_id: str) -> None:
        content = read_active_public_transport(self.spatial_pack_dir, activation_id)
        if content is None:
            self.respond_not_found()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/geo+json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

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
            project_events = []
            place_context = (
                location_place_context(connection, entity_id)
                if record and definition.type == "location"
                else None
            )
            if record and definition.type == "project":
                from datetime import date
                for relationship in relationships:
                    other = relationship.other_entity(entity_id)
                    if other.type == "event":
                        event = get_event(connection, other.id)
                        if event and (event.start_date >= date.today().isoformat() if event.is_all_day else event.start_utc[:10] >= date.today().isoformat()):
                            project_events.append(event)
        if record is None:
            self.respond_not_found()
            return

        self.respond_page(
            record.title,
            views.entity_detail_page(
                record,
                relationships,
                integrity_warnings,
                history,
                audit_events,
                journal_entries,
                project_events,
                place_context,
            ),
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
            relationship = get_relationship(connection, relationship_id)
            if relationship is None:
                self.respond_not_found()
                return
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

def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    initialise_local_storage()
    initialise_database(DEFAULT_HTTP_CONFIG.database_path)
    scheduler = SchedulerRuntime(DEFAULT_HTTP_CONFIG.database_path)
    scheduler.start()
    server = create_http_server((host, port), EddyRequestHandler)
    print(f"Project E running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Project E stopped.")
    finally:
        server.server_close()
        scheduler.stop()
