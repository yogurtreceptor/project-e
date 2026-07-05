"""Stable public facade for server-rendered page functions.

Implementations live in :mod:`app.view_pages` modules grouped by responsibility.
"""

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import (
    DATE_PRECISIONS,
    RELATIONSHIP_STATUSES,
    RELATIONSHIP_TYPES,
    RelationshipRecord,
    relationship_choices_for_context,
)
from app.view_pages.layout import (
    layout,
)
from app.view_pages.dashboard import (
    dashboard_page,
    dashboard_discovery_sections,
    entity_link_list,
    favourite_form,
)
from app.view_pages.common import (
    format_relationship_dates,
    format_date_with_precision,
    not_found_page,
)
from app.view_pages.forms import (
    error_block,
    input_field,
    entity_field_control,
    entity_form_fields,
    custom_value_field,
    hidden_field,
    file_upload_field,
    select_field,
    existing_location_action,
    address_lookup_field,
    address_lookup_script,
)
from app.view_pages.entities import (
    entity_list_page,
    entity_detail_page,
    entity_profile_header,
    entity_overview_section,
    entity_geography_section,
    entity_relationships_panel,
    related_entities_section,
    entity_notes_section,
    person_journal_section,
    journal_edit_page,
    document_file_section,
    linked_documents_section,
    timeline_section,
    audit_history_section,
    metadata_section,
    entity_form_page,
)
from app.view_pages.relationships import (
    family_tree_page,
    relationship_list_page,
    inference_review_page,
    relationship_detail_page,
    relationship_form_page,
    relationship_workflow_selector,
    existing_entity_workflow,
    new_entity_workflow,
    relationship_metadata_fields,
    entity_options,
    relationship_type_options,
    relationship_option_text,
    relationship_form_script,
    date_precision_options,
)
from app.view_pages.search import (
    search_page,
    search_result_card,
)
from app.view_pages.data_quality import data_quality_page
from app.view_pages.map import (
    map_page,
)
from app.view_pages.merge import merge_select_page, merge_preview_page
from app.view_pages.recycle_bin import recycle_bin_page, permanent_delete_confirmation_page
from app.view_pages.timeline import universal_timeline_page
from app.view_pages.taxonomies import taxonomies_page
from app.view_pages.system_tools import system_tools_page
from app.view_pages.audit import system_audit_page
from app.view_pages.portability import portability_page, import_preview_page

INLINE_RELATIONSHIP_ENTITY_TYPES = {"person", "organisation", "location"}

__all__ = [
    "layout",
    "dashboard_page",
    "dashboard_discovery_sections",
    "entity_link_list",
    "favourite_form",
    "entity_list_page",
    "entity_detail_page",
    "entity_profile_header",
    "entity_overview_section",
    "entity_geography_section",
    "entity_relationships_panel",
    "related_entities_section",
    "entity_notes_section",
    "person_journal_section",
    "journal_edit_page",
    "document_file_section",
    "linked_documents_section",
    "timeline_section",
    "audit_history_section",
    "metadata_section",
    "format_relationship_dates",
    "format_date_with_precision",
    "entity_form_page",
    "relationship_list_page",
    "family_tree_page",
    "relationship_detail_page",
    "relationship_form_page",
    "relationship_workflow_selector",
    "existing_entity_workflow",
    "new_entity_workflow",
    "relationship_metadata_fields",
    "inline_fields_for_definition",
    "entity_options",
    "relationship_type_options",
    "relationship_option_text",
    "entity_field_control_for_name",
    "relationship_form_script",
    "date_precision_options",
    "search_page",
    "search_result_card",
    "not_found_page",
    "recycle_bin_page",
    "permanent_delete_confirmation_page",
    "universal_timeline_page",
    "error_block",
    "input_field",
    "entity_field_control",
    "custom_value_field",
    "hidden_field",
    "file_upload_field",
    "select_field",
    "taxonomies_page",
    "system_tools_page",
    "system_audit_page",
    "portability_page",
    "import_preview_page",
    "existing_location_action",
    "address_lookup_field",
    "address_lookup_script",
    "map_page",
    "merge_select_page",
    "merge_preview_page",
]
