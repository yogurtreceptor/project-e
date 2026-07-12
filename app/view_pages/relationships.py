import json
from itertools import permutations
from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import (
    DATE_PRECISIONS,
    RELATIONSHIP_STATUSES,
    RELATIONSHIP_TYPES,
    RELATIONSHIP_TYPES_BY_KEY,
    RelationshipRecord,
    relationship_choice_value,
    relationship_choices_for_context,
    role_label,
    split_relationship_choice,
)
from app.taxonomy import TaxonomyChoice
from app.view_pages.common import format_date_with_precision
from app.view_pages.forms import associate_field_errors, entity_form_fields, error_block, input_field, select_field, taxonomy_field
from app.graph_layout import GraphLayout


INLINE_RELATIONSHIP_ENTITY_TYPES = {"person", "organisation", "location"}


def family_tree_page(tree: GraphLayout) -> str:
    if not tree.nodes:
        visual = '<p class="empty">No supported family relationships yet. Add parent/child, spouse or partner relationships between People first.</p>'
    else:
        positions = {node.id: node for node in tree.nodes}
        lines = _hierarchy_connector_paths(tree, positions)
        for edge in tree.edges:
            if edge.rank_delta > 0 and not edge.cyclic:
                continue
            source = positions.get(edge.source_id)
            target = positions.get(edge.target_id)
            if source is None or target is None:
                continue
            css_class = f"family-edge family-edge-{edge.connector_style}"
            if edge.cyclic:
                css_class += " family-edge-cyclic"
            if source.y == target.y:
                direction = 1 if target.x > source.x else -1
                start_x, end_x = source.x + direction * 72, target.x - direction * 72
                path = f"M {start_x} {source.y} H {end_x}"
            else:
                direction = 1 if target.y > source.y else -1
                start_y, end_y = source.y + direction * 26, target.y - direction * 26
                midpoint_y = (start_y + end_y) // 2
                path = f"M {source.x} {start_y} V {midpoint_y} H {target.x} V {end_y}"
            lines.append(f'<path class="{css_class}" d="{path}" />')
        nodes = "".join(f'<a href="{escape(node.href)}" class="{"family-node-selected" if node.selected else "family-node"}"><rect x="{node.x - 72}" y="{node.y - 26}" width="144" height="52" rx="8"/><text x="{node.x}" y="{node.y + 5}">{escape(node.label)}</text></a>' for node in tree.nodes)
        visual = f'<div class="family-tree-scroll" tabindex="0" role="region" aria-label="Scrollable family relationship tree"><svg class="family-tree" viewBox="0 0 {tree.width} {tree.height}" width="{tree.width}" height="{tree.height}" role="img" aria-label="Family relationship tree">{"".join(lines)}{nodes}</svg></div>'
    node_names = {node.id: node.label for node in tree.nodes}
    relationship_items = "".join(
        f'<li><a href="{escape(next(node.href for node in tree.nodes if node.id == edge.source_id))}">{escape(node_names.get(edge.source_id, "Unknown person"))}</a> <span>{escape(edge.label)}</span> <a href="{escape(next(node.href for node in tree.nodes if node.id == edge.target_id))}">{escape(node_names.get(edge.target_id, "Unknown person"))}</a>{" <strong>Contradictory/cyclic</strong>" if edge.cyclic else ""}</li>'
        for edge in tree.edges if edge.source_id in node_names and edge.target_id in node_names
    )
    text_alternative = f'<ul class="family-relationship-list">{relationship_items}</ul>' if relationship_items else '<p class="empty">No included relationships.</p>'
    cycle_warning = '<div class="status-row warning"><span>Contradictory or cyclic family relationships are present.</span> Inspect the relationships below.</div>' if any(edge.cyclic for edge in tree.edges) else ""
    return f"""
    <section class="page-heading split">
        <div><p class="eyebrow">Relationship visualisation</p><h1>Family tree</h1><p>A derived view of existing family relationships. No separate family data is stored.</p></div>
        <a class="button secondary" href="/relationships">Back to relationships</a>
    </section>
    {cycle_warning}<section class="panel family-tree-panel">{visual}</section>
    <section class="family-tree-legend" aria-label="Family tree connector key"><strong>Connector key</strong><span><i class="legend-line legend-partner"></i>Partner / spouse</span><span><i class="legend-line legend-parent"></i>Parent / child</span></section>
    <section class="panel"><h2>Included relationships</h2>{text_alternative}<p>Parent/child links connect adjacent generations, with children grouped only when their complete recorded parent sets match; each group uses an independent connector. Sibling connections are inferred only from shared parent-set connectors; no separate sibling lines are drawn. Spouse and partner links are shown directly on the same generation. Relationships spanning multiple generations remain stored but are shown through the parent/child chain instead of redundant direct lines.</p></section>
    """


def _hierarchy_connector_paths(tree: GraphLayout, positions: dict) -> list[str]:
    """Route exact incoming-source sets independently, avoiding crossings first."""
    incoming_sources: dict[int, set[int]] = {}
    hierarchy_edges = [edge for edge in tree.edges if edge.rank_delta > 0 and not edge.cyclic]
    for edge in hierarchy_edges:
        incoming_sources.setdefault(edge.target_id, set()).add(edge.source_id)

    targets_by_sources: dict[tuple[int, ...], list[int]] = {}
    for target_id, source_ids in incoming_sources.items():
        targets_by_sources.setdefault(tuple(sorted(source_ids)), []).append(target_id)

    bundles = []
    for source_ids, target_ids in targets_by_sources.items():
        sources = [positions[source_id] for source_id in source_ids if source_id in positions]
        targets = [positions[target_id] for target_id in sorted(target_ids) if target_id in positions]
        if sources and targets:
            bundles.append((source_ids, tuple(sorted(target_ids)), sources, targets))
    bundles.sort(key=lambda bundle: (sum(target.x for target in bundle[3]) / len(bundle[3]), bundle[0], bundle[1]))

    bundles_by_gap: dict[tuple[int, int], list[tuple]] = {}
    for bundle in bundles:
        source_y = max(source.y for source in bundle[2]) + 26
        target_y = min(target.y for target in bundle[3]) - 26
        bundles_by_gap.setdefault((source_y, target_y), []).append(bundle)

    paths: list[str] = []
    accepted_segments: list[tuple[int, int, int, int]] = []
    for (source_y, target_y), gap_bundles in sorted(bundles_by_gap.items()):
        available_height = target_y - source_y
        lane_step = max(8, min(18, available_height // max(4, len(gap_bundles) * 2 + 2)))
        candidate_orders = permutations(gap_bundles) if len(gap_bundles) <= 6 else (tuple(gap_bundles),)
        route_sets = [
            _route_bundle_order(
                order, positions, source_y, target_y, lane_step, tree.width, accepted_segments
            )
            for order in candidate_orders
        ]
        chosen_routes = min(
            route_sets,
            key=lambda routes: (sum(route[6] for route in routes), tuple(route[0] for route in routes)),
        )
        for source_ids, target_ids, source_port_pairs, parent_bar_y, child_bar_y, trunk_x, crossing_count, commands, segments in chosen_routes:
            source_set = ",".join(str(source_id) for source_id in source_ids)
            target_set = ",".join(str(target_id) for target_id in target_ids)
            source_port_set = ",".join(f"{source_id}:{x}" for source_id, x in source_port_pairs)
            path_data = " ".join(commands)
            if crossing_count:
                paths.append(f'<path class="family-edge-casing" d="{path_data}" aria-hidden="true" />')
            paths.append(
                f'<path class="family-edge family-edge-hierarchy family-edge-bundle" '
                f'data-source-set="{source_set}" data-target-set="{target_set}" '
                f'data-source-ports="{source_port_set}" data-lane="{parent_bar_y},{child_bar_y}" '
                f'data-trunk="{trunk_x}" data-crossings="{crossing_count}" d="{path_data}" />'
            )
            accepted_segments.extend(segments)
    return paths


def _route_bundle_order(order: tuple, positions: dict, source_y: int, target_y: int, lane_step: int, width: int, existing_segments: list[tuple[int, int, int, int]]) -> list[tuple]:
    source_bundles: dict[int, list[tuple[int, ...]]] = {}
    for source_ids, _, _, _ in order:
        for source_id in source_ids:
            source_bundles.setdefault(source_id, []).append(source_ids)
    source_ports: dict[tuple[int, tuple[int, ...]], int] = {}
    for source_id, source_sets in source_bundles.items():
        step = min(24, 96 // max(1, len(source_sets) - 1))
        start_offset = (step * (len(source_sets) - 1)) // 2
        for index, source_ids in enumerate(source_sets):
            source_ports[(source_id, source_ids)] = positions[source_id].x + start_offset - index * step

    routes = []
    routed_segments = list(existing_segments)
    for lane_index, (source_ids, target_ids, sources, targets) in enumerate(order):
        parent_bar_y = source_y + lane_step * (lane_index + 1)
        child_bar_y = target_y - lane_step * (len(order) - lane_index)
        source_port_pairs = sorted((source.id, source_ports[(source.id, source_ids)]) for source in sources)
        source_xs = sorted(x for _, x in source_port_pairs)
        target_xs = sorted(target.x for target in targets)
        parent_centre_x = (source_xs[0] + source_xs[-1]) // 2
        target_centre_x = sum(target_xs) // len(target_xs)
        candidates = _trunk_candidates(parent_centre_x, target_centre_x, source_xs, target_xs, width)
        scored_options = []
        for trunk_x in candidates:
            commands, segments = _bundle_route(source_xs, target_xs, source_y, target_y, parent_bar_y, child_bar_y, trunk_x)
            scored_options.append((commands, segments, _crossing_count(segments, routed_segments), trunk_x))
        commands, segments, crossing_count, trunk_x = min(
            scored_options,
            key=lambda option: (option[2], abs(option[3] - target_centre_x), option[3]),
        )
        routes.append((source_ids, target_ids, source_port_pairs, parent_bar_y, child_bar_y, trunk_x, crossing_count, commands, segments))
        routed_segments.extend(segments)
    return routes


def _trunk_candidates(parent_x: int, target_x: int, source_xs: list[int], target_xs: list[int], width: int) -> list[int]:
    candidates = [target_x, parent_x, *target_xs, *source_xs]
    for x in (min(source_xs + target_xs), max(source_xs + target_xs)):
        candidates.extend((x - 48, x + 48))
    return list(dict.fromkeys(max(12, min(width - 12, x)) for x in candidates))


def _bundle_route(source_xs: list[int], target_xs: list[int], source_y: int, target_y: int, parent_bar_y: int, child_bar_y: int, trunk_x: int) -> tuple[list[str], list[tuple[int, int, int, int]]]:
    parent_x = (source_xs[0] + source_xs[-1]) // 2
    commands = [f"M {x} {source_y} V {parent_bar_y}" for x in source_xs]
    segments = [(x, source_y, x, parent_bar_y) for x in source_xs]
    if len(source_xs) > 1:
        commands.append(f"M {source_xs[0]} {parent_bar_y} H {source_xs[-1]}")
        segments.append((source_xs[0], parent_bar_y, source_xs[-1], parent_bar_y))
    commands.append(f"M {parent_x} {parent_bar_y} H {trunk_x} V {child_bar_y}")
    segments.extend(((parent_x, parent_bar_y, trunk_x, parent_bar_y), (trunk_x, parent_bar_y, trunk_x, child_bar_y)))
    child_bar_start = min(trunk_x, target_xs[0])
    child_bar_end = max(trunk_x, target_xs[-1])
    if child_bar_start != child_bar_end:
        commands.append(f"M {child_bar_start} {child_bar_y} H {child_bar_end}")
        segments.append((child_bar_start, child_bar_y, child_bar_end, child_bar_y))
    commands.extend(f"M {x} {child_bar_y} V {target_y}" for x in target_xs)
    segments.extend((x, child_bar_y, x, target_y) for x in target_xs)
    return commands, segments


def _crossing_count(route: list[tuple[int, int, int, int]], accepted: list[tuple[int, int, int, int]]) -> int:
    return sum(_segments_intersect(first, second) for first in route for second in accepted)


def _segments_intersect(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = first
    bx1, by1, bx2, by2 = second
    if ax1 == ax2 and bx1 == bx2:
        return ax1 == bx1 and max(min(ay1, ay2), min(by1, by2)) <= min(max(ay1, ay2), max(by1, by2))
    if ay1 == ay2 and by1 == by2:
        return ay1 == by1 and max(min(ax1, ax2), min(bx1, bx2)) <= min(max(ax1, ax2), max(bx1, bx2))
    if ax1 == ax2:
        return min(bx1, bx2) <= ax1 <= max(bx1, bx2) and min(ay1, ay2) <= by1 <= max(ay1, ay2)
    return min(ax1, ax2) <= bx1 <= max(ax1, ax2) and min(by1, by2) <= ay1 <= max(by1, by2)


def relationship_list_page(relationships: list[RelationshipRecord], integrity_warnings: list = None) -> str:
    integrity_warnings = integrity_warnings or []
    warning_html = ""
    if integrity_warnings:
        items = "".join(f"<li><strong>{escape(item.severity.title())}:</strong> {escape(item.message)}</li>" for item in integrity_warnings)
        warning_html = f'<section class="warnings"><h2>Data integrity warnings</h2><ul>{items}</ul></section>'
    if not relationships:
        content = '<p class="empty">No relationships yet.</p>'
    else:
        rows = []
        for relationship in relationships:
            rows.append(
                f"""
                <tr>
                    <td><a href="/relationships/{relationship.id}">{escape(relationship.label)}</a></td>
                    <td><a href="/{relationship.source.slug}/{relationship.source.id}">{escape(relationship.source.title)}</a></td>
                    <td><a href="/{relationship.target.slug}/{relationship.target.id}">{escape(relationship.target.title)}</a></td>
                    <td>{escape(relationship.status)} {('<span class="origin-badge origin-inferred">created from inference</span>' if relationship.created_from_inference else '')}</td>
                    <td class="row-actions"><a href="/relationships/{relationship.id}/edit">Edit</a></td>
                </tr>
                """
            )
        content = (
            """
            <div class="table-scroll" tabindex="0" role="region" aria-label="Relationship records"><table>
                <thead><tr><th>Type</th><th>Source</th><th>Target</th><th>Status</th><th><span class="visually-hidden">Actions</span></th></tr></thead>
                <tbody>"""
            + "".join(rows)
            + "</tbody></table></div>"
        )
    return f"""
    <section class="page-heading split">
        <div>
            <h1>Relationships</h1>
            <p>Browse first-class links between any entity types.</p>
        </div>
        <div class="actions"><a class="button secondary" href="/relationships/inferences">Inference review queue</a><a class="button secondary" href="/relationships/family-tree">View family tree</a></div>
    </section>
    {warning_html}
    <section class="panel">{content}</section>
    """


def relationship_detail_page(relationship: RelationshipRecord) -> str:
    ended_date = (
        f'<dt>Ended</dt><dd>{escape(format_date_with_precision(relationship.ended_at, relationship.ended_at_precision))}</dd>'
        if relationship.ended_at
        else ""
    )
    return f"""
    <section class="page-heading split">
        <div>
            <p class="eyebrow">Relationship</p>
            <h1>{escape(relationship.source.title)} {escape(relationship.label)} {escape(relationship.target.title)}</h1>
            <p>{escape(relationship.status)}</p>
        </div>
        <div class="actions">
            <a class="button secondary" href="/relationships">Back</a>
            <a class="button" href="/relationships/{relationship.id}/edit">Edit</a>
        </div>
    </section>
    <section class="panel">
        <h2>Connected entities</h2>
        <dl>
            <dt>Source</dt><dd><a href="/{relationship.source.slug}/{relationship.source.id}">{escape(relationship.source.title)}</a></dd>
            <dt>Target</dt><dd><a href="/{relationship.target.slug}/{relationship.target.id}">{escape(relationship.target.title)}</a></dd>
            <dt>Type</dt><dd>{escape(relationship.label)}</dd>
            <dt>Inverse</dt><dd>{escape(relationship.type.inverse_label)}</dd>
            <dt>Status</dt><dd>{escape(relationship.status)}</dd>
            <dt>Origin</dt><dd>{'Created from a confirmed inference' if getattr(relationship, 'created_from_inference', False) else 'Created manually'}</dd>
            <dt>Started</dt><dd>{escape(format_date_with_precision(relationship.started_at, relationship.started_at_precision))}</dd>
            {ended_date}
        </dl>
    </section>
    {inference_audit_panel(relationship)}
    <section class="panel">
        <h2>Notes</h2>
        <p class="notes">{escape(relationship.notes) if relationship.notes else 'No notes yet.'}</p>
    </section>
    <section class="panel metadata">
        <h2>Metadata</h2>
        <dl>
            <dt>Created</dt><dd>{escape(relationship.created_at)}</dd>
            <dt>Updated</dt><dd>{escape(relationship.updated_at)}</dd>
        </dl>
    </section>
    """


def relationship_form_page(
    values: dict[str, str],
    errors: list[str],
    entities: list[EntityRecord],
    action: str,
    relationship_id: int | None = None,
    context_entity: EntityRecord | None = None,
    target_type: str | None = None,
    inline_field_options: dict[str, list] | None = None,
) -> str:
    query = []
    if context_entity is not None:
        query.append(f"context_entity_id={context_entity.id}")
    if target_type:
        query.append(f"target_type={target_type}")
    query_string = "?" + "&".join(query) if query else ""
    form_action = f"/relationships/{relationship_id}/edit{query_string}" if relationship_id else f"/relationships/new{query_string}"
    target_entities = [entity for entity in entities if entity.id != (context_entity.id if context_entity else None) and (not target_type or entity.type == target_type)]
    source_entity = context_entity
    if source_entity is None and values.get("source_entity_id"):
        source_entity = next((entity for entity in entities if str(entity.id) == str(values.get("source_entity_id"))), None)
    selected_target = next((entity for entity in entities if str(entity.id) == str(values.get("target_entity_id"))), None)
    connected_type = selected_target.type if selected_target else (target_type or "")
    connected_sex = selected_target.metadata.get("sex", "Unknown") if selected_target else "Unknown"
    workflow_mode = values.get("workflow_mode") or values.get("target_mode") or "existing"

    error_fields = relationship_error_fields(errors)
    fields = []
    if context_entity is not None:
        fields.append(f'<div class="readonly-field"><span>Current entity</span><strong>{escape(context_entity.title)}</strong></div>')
        source_value = escape(str(values.get("source_entity_id", context_entity.id)))
        fields.append(f'<input type="hidden" name="source_entity_id" value="{source_value}">')
    else:
        fields.append(select_field("source_entity_id", "Current entity", entity_options(entities), values))

    fields.extend([
        relationship_workflow_selector(workflow_mode),
        existing_entity_workflow(target_entities, values, workflow_mode),
        new_entity_workflow(target_type, workflow_mode, values, inline_field_options),
        relationship_metadata_fields(source_entity, connected_type, connected_sex, selected_target, values),
    ])
    return f"""
    <section class="page-heading">
        <p class="eyebrow">Relationship</p>
        <h1>{escape(action)} Relationship</h1>
    </section>
    <section class="panel">
        {error_block(errors, error_fields)}
        <form class="record-form relationship-form" method="post" action="{form_action}">
            {associate_field_errors(''.join(fields), errors, error_fields)}
            <div class="actions">
                <a class="button secondary" href="{'/' + context_entity.slug + '/' + str(context_entity.id) if context_entity else '/relationships'}">Cancel</a>
                <button class="button" type="submit">Save</button>
            </div>
        </form>
    </section>
    {relationship_form_script(entities, target_type, source_entity)}
    """


def relationship_error_fields(errors: list[str]) -> list[str | None]:
    prefixes = (
        ("Source entity", "source_entity_id"),
        ("Target entity", "target_entity_id"),
        ("Connected entity type", "new_entity_type"),
        ("Choose Person", "new_entity_type"),
        ("Relationship type", "type"),
        ("Relationship status", "status"),
        ("Start date certainty", "started_at_precision"),
        ("End date certainty", "ended_at_precision"),
        ("Started", "started_at"),
        ("Ended", "ended_at"),
    )
    fields = []
    for error in errors:
        field = next((name for prefix, name in prefixes if error.startswith(prefix)), None)
        if error.startswith("New ") and ": " in error:
            nested = error.split(": ", 1)[1]
            if nested.startswith("Given name"):
                field = "new_given_name"
            elif " name " in nested:
                field = "new_display_name"
        fields.append(field)
    return fields


def relationship_workflow_selector(workflow_mode: str) -> str:
    existing_checked = " checked" if workflow_mode != "create_new" else ""
    new_checked = " checked" if workflow_mode == "create_new" else ""
    return f"""
    <fieldset class="relationship-step workflow-toggle">
        <legend>Relationship workflow</legend>
        <label class="inline-check"><input type="radio" name="workflow_mode" value="existing"{existing_checked}> Existing entity</label>
        <label class="inline-check"><input type="radio" name="workflow_mode" value="create_new"{new_checked}> New entity</label>
    </fieldset>
    """


def existing_entity_workflow(entities: list[EntityRecord], values: dict[str, str], workflow_mode: str) -> str:
    hidden = " hidden" if workflow_mode == "create_new" else ""
    select = select_field("target_entity_id", "Existing entity", entity_options(entities), values)
    return f"""
    <fieldset class="relationship-step relationship-workflow-panel" data-workflow-panel="existing"{hidden}>
        <legend>Existing entity</legend>
        {select}
    </fieldset>
    """


def new_entity_workflow(
    target_type: str | None, workflow_mode: str, values: dict[str, str] | None = None,
    field_options: dict[str, list] | None = None,
) -> str:
    values = values or {}
    hidden = " hidden" if workflow_mode != "create_new" else ""
    definitions = [
        definition
        for definition in ENTITY_DEFINITIONS
        if definition.type in INLINE_RELATIONSHIP_ENTITY_TYPES and (not target_type or definition.type == target_type)
    ]
    if not definitions:
        return ""
    selected_type = values.get("new_entity_type") or target_type or definitions[0].type
    select_values = {**values, "new_entity_type": selected_type}
    fieldsets = []
    for definition in definitions:
        fieldsets.append(
            f"""
            <div class="inline-entity-fields" data-inline-entity-type="{escape(definition.type)}">
                {entity_form_fields(definition, values, name_prefix="new_", field_options=field_options)}
            </div>
            """
        )
    return f"""
    <fieldset class="relationship-step relationship-workflow-panel" data-workflow-panel="create_new"{hidden}>
        <legend>New entity</legend>
        {select_field("new_entity_type", "Entity type", [(definition.type, definition.singular) for definition in definitions], select_values)}
        {''.join(fieldsets)}
    </fieldset>
    """


def relationship_metadata_fields(
    source_entity: EntityRecord | None,
    connected_type: str,
    connected_sex: str,
    selected_target: EntityRecord | None,
    values: dict[str, str],
) -> str:
    options = relationship_taxonomy_choices(source_entity, connected_type, connected_sex, values.get("type", ""))
    selector_values = values
    current_type = values.get("type", "")
    if current_type and "::" not in current_type:
        matches = [item.value for item in options if item.value.startswith(current_type + "::")]
        if matches:
            selected_value = next((value for value in matches if value.endswith("::target")), matches[0])
            selector_values = {**values, "type": selected_value}
    current_name = source_entity.title if source_entity else "the current entity"
    connected_name = selected_target.title if selected_target else inline_connected_name(connected_type, values)
    connected_label = connected_name or "the connected entity"
    prompt = f"What is {connected_label} in relation to {current_name}?"
    return f"""
    <fieldset class="relationship-step relationship-metadata">
        <legend>Relationship details</legend>
        <p class="relationship-question" id="relationship_question" data-current-name="{escape(current_name)}">{escape(prompt)}</p>
        {taxonomy_field("type", "Relationship", options, selector_values, "Browse relevant relationship paths or type to search the full taxonomy.")}
        {select_field("status", "Status", [(status, status.title()) for status in RELATIONSHIP_STATUSES], values)}
        {input_field("started_at", "Started", values, input_type="date")}
        {select_field("started_at_precision", "Start date certainty", date_precision_options(), values)}
        {input_field("ended_at", "Ended", values, input_type="date")}
        {select_field("ended_at_precision", "End date certainty", date_precision_options(), values)}
        {input_field("notes", "Notes", values, multiline=True)}
    </fieldset>
    """


def inline_connected_name(entity_type: str, values: dict[str, str]) -> str:
    if entity_type == "person":
        return " ".join(
            part
            for part in (
                values.get("new_given_name", "").strip(),
                values.get("new_family_name", "").strip(),
            )
            if part
        )
    return values.get("new_display_name", "").strip()


def entity_options(entities: list[EntityRecord]) -> list[tuple[str, str]]:
    return [(str(entity.id), f"{entity.title} ({entity.definition.singular})") for entity in entities]


def relationship_type_options(
    source_entity: EntityRecord | None = None,
    target_type: str | None = None,
    target_sex: str = "Unknown",
) -> list[tuple[str, str]]:
    if source_entity is not None and target_type:
        return relationship_choices_for_context(source_entity.type, target_type, target_sex)
    return [(relationship_type.key, relationship_option_text(relationship_type)) for relationship_type in RELATIONSHIP_TYPES_BY_KEY.values() if relationship_type.selectable]


def relationship_option_text(relationship_type) -> str:
    return relationship_type.display_label


def relationship_taxonomy_choices(
    source_entity: EntityRecord | None = None,
    target_type: str | None = None,
    target_sex: str = "Unknown",
    include_type_key: str = "",
) -> list[TaxonomyChoice]:
    options = relationship_type_options(source_entity, target_type, target_sex)
    choices = []
    for value, label in options:
        key, _role = split_relationship_choice(value)
        relationship_type = RELATIONSHIP_TYPES_BY_KEY[key]
        path = relationship_type.taxonomy_path or relationship_type.display_label
        choices.append(TaxonomyChoice(value, label, path, path.count(" › ")))
    include_type_key, _role = split_relationship_choice(include_type_key)
    if include_type_key and all(split_relationship_choice(item.value)[0] != include_type_key for item in choices):
        relationship_type = RELATIONSHIP_TYPES_BY_KEY.get(include_type_key)
        if relationship_type and source_entity and target_type and relationship_type.supports_pair(source_entity.type, target_type):
            if relationship_type.source_type == relationship_type.target_type == source_entity.type == target_type:
                connected_role = "source" if not relationship_type.directional else "target"
            elif relationship_type._matches(source_entity.type, target_type):
                connected_role = "target"
            else:
                connected_role = "source"
            path = relationship_type.taxonomy_path or relationship_type.display_label
            choices.append(TaxonomyChoice(
                relationship_choice_value(relationship_type, connected_role),
                role_label(relationship_type, connected_role, target_sex), path,
                path.count(" › "), available=False,
            ))
    return choices


def relationship_taxonomy_payload(context_type: str, connected_type: str, sex: str = "Unknown") -> list[dict]:
    source = type("RelationshipChoiceContext", (), {"type": context_type})()
    return [
        {"value": item.value, "label": item.label, "path": item.path, "depth": item.depth,
         "available": item.available, "display": item.display_text}
        for item in relationship_taxonomy_choices(source, connected_type, sex)
    ]


def relationship_form_script(
    entities: list[EntityRecord],
    target_type: str | None = None,
    source_entity: EntityRecord | None = None,
) -> str:
    entity_data = [
        {
            "id": str(entity.id),
            "type": entity.type,
            "sex": entity.metadata.get("sex", "Unknown"),
            "label": f"{entity.title} ({entity.definition.singular})",
            "choices": relationship_taxonomy_payload(source_entity.type, entity.type, entity.metadata.get("sex", "Unknown")) if source_entity else [],
        }
        for entity in entities
        if entity.id != (source_entity.id if source_entity else None)
    ]
    choice_types = sorted({entity.type for entity in entities} | {target_type or ""} - {""})
    choices_by_type = {
        entity_type: relationship_taxonomy_payload(source_entity.type, entity_type, "Unknown")
        for entity_type in choice_types
        if source_entity is not None
    }
    choices_by_type_and_sex = {
        sex: {
            entity_type: relationship_taxonomy_payload(source_entity.type, entity_type, sex)
            for entity_type in choice_types
        }
        for sex in ("Male", "Female", "Other", "Unknown")
    } if source_entity is not None else {}
    return f"""
    <script>
    (() => {{
        const entities = {json.dumps(entity_data).replace("</", "<\\/")};
        const choicesByType = {json.dumps(choices_by_type).replace("</", "<\\/")};
        const forcedTargetType = {json.dumps(target_type or "")};
        const target = document.getElementById('target_entity_id');
        const question = document.getElementById('relationship_question');
        const type = document.getElementById('type');
        const typePicker = type ? type.closest('[data-taxonomy-combobox]') : null;
        const newType = document.getElementById('new_entity_type');
        const newNameFields = Array.from(document.querySelectorAll('[name="new_display_name"], [name="new_given_name"], [name="new_family_name"]'));
        const workflowModes = Array.from(document.querySelectorAll('input[name="workflow_mode"]'));
        const panels = Array.from(document.querySelectorAll('[data-workflow-panel]'));
        const entityById = new Map(entities.map((entity) => [entity.id, entity]));
        const selectedMode = () => {{
            const selected = workflowModes.find((item) => item.checked);
            return selected ? selected.value : 'existing';
        }};
        const refreshPanels = () => {{
            const mode = selectedMode();
            panels.forEach((panel) => {{
                const active = panel.dataset.workflowPanel === mode;
                panel.hidden = !active;
                panel.querySelectorAll('input, textarea, select').forEach((field) => {{
                    field.disabled = !active;
                }});
            }});
            refreshInlineFields();
            refreshRelationshipChoices();
        }};
        const fillRelationshipChoices = (choices) => {{
            if (!typePicker) return;
            const data = typePicker.querySelector('[data-taxonomy-data]');
            if (data) data.textContent = JSON.stringify(choices || []);
            typePicker.dispatchEvent(new CustomEvent('taxonomy:replace', {{detail: choices || []}}));
        }};
        const connectedNameFromLabel = (label) => (label || '').replace(/ \\([^)]*\\)$/, '');
        const updateQuestion = (connectedName) => {{
            if (!question) return;
            const name = connectedName || 'the connected entity';
            const currentName = question.dataset.currentName || 'the current entity';
            question.textContent = `What is ${{name}} in relation to ${{currentName}}?`;
        }};
        const activeNewName = () => {{
            const activeType = newType ? newType.value : '';
            const activeSection = document.querySelector(`[data-inline-entity-type="${{activeType}}"]`);
            if (!activeSection) return '';
            if (activeType === 'person') {{
                const given = activeSection.querySelector('[name="new_given_name"]');
                const family = activeSection.querySelector('[name="new_family_name"]');
                return [given ? given.value.trim() : '', family ? family.value.trim() : ''].filter(Boolean).join(' ');
            }}
            const displayName = activeSection.querySelector('[name="new_display_name"]');
            return displayName ? displayName.value.trim() : '';
        }};
        const refreshRelationshipChoices = () => {{
            if (selectedMode() === 'create_new') {{
                fillRelationshipChoices(choicesByType[newType ? newType.value : ''] || []);
                updateQuestion(activeNewName());
                return;
            }}
            const selectedEntity = target ? entityById.get(target.value) : null;
            fillRelationshipChoices(selectedEntity ? selectedEntity.choices : (choicesByType[forcedTargetType] || []));
            updateQuestion(selectedEntity ? connectedNameFromLabel(selectedEntity.label) : '');
        }};
        const filterTargets = () => {{
            if (!target) return;
            const current = target.value;
            target.innerHTML = '<option value="">Select...</option>';
            entities
                .filter((entity) => !forcedTargetType || entity.type === forcedTargetType)
                .forEach((entity) => {{
                    const option = document.createElement('option');
                    option.value = entity.id;
                    option.textContent = entity.label;
                    if (entity.id === current) option.selected = true;
                    target.appendChild(option);
                }});
            refreshRelationshipChoices();
        }};
        const refreshInlineFields = () => {{
            const activeType = newType ? newType.value : '';
            document.querySelectorAll('[data-inline-entity-type]').forEach((section) => {{
                const active = section.dataset.inlineEntityType === activeType && selectedMode() === 'create_new';
                section.hidden = section.dataset.inlineEntityType !== activeType;
                section.querySelectorAll('input, textarea, select').forEach((field) => {{
                    field.disabled = !active;
                }});
            }});
        }};
        if (target) target.addEventListener('change', refreshRelationshipChoices);
        if (newType) newType.addEventListener('change', refreshPanels);
        newNameFields.forEach((field) => field.addEventListener('input', refreshRelationshipChoices));
        document.querySelectorAll("[id^=\'new_sex\']").forEach((field) => field.addEventListener('change', refreshRelationshipChoices));
        workflowModes.forEach((item) => item.addEventListener('change', refreshPanels));
        filterTargets();
        refreshPanels();
    }})();
    </script>
    """


def date_precision_options() -> list[tuple[str, str]]:
    return [(precision, precision.replace("_", " ").title()) for precision in DATE_PRECISIONS]




def inference_audit_panel(relationship: RelationshipRecord) -> str:
    if not getattr(relationship, "created_from_inference", False):
        return ""
    try:
        provenance = json.loads(getattr(relationship, "provenance_json", "") or "{}")
    except json.JSONDecodeError:
        provenance = {}
    support_ids = provenance.get("supporting_relationship_ids", [])
    links = ", ".join(f'<a href="/relationships/{int(item)}">#{int(item)}</a>' for item in support_ids) or "Not recorded"
    evidence = getattr(relationship, "inference_evidence_status", "") or "unknown"
    warning = '<p class="warning-text">The original supporting evidence has changed. Review this relationship when convenient; it remains editable and active.</p>' if evidence == "changed" else ""
    return f'''<section class="panel inference-audit"><h2>Inference history</h2>{warning}<dl>
        <dt>Rule</dt><dd>{escape(str(provenance.get("rule_key", "Not recorded")))}</dd>
        <dt>Source batch</dt><dd>{escape(str(provenance.get("source_batch_id", "Not recorded")))}</dd>
        <dt>Supporting relationships</dt><dd>{links}</dd>
        <dt>Evidence status</dt><dd>{escape(evidence)}</dd>
        <dt>Suggested</dt><dd>{escape(str(provenance.get("inferred_at", "Not recorded")))}</dd>
        <dt>Confirmed</dt><dd>{escape(str(provenance.get("confirmed_at", "Not recorded")))}</dd>
    </dl></section>'''


def inference_review_page(batches, relationships_by_id, history_batches=None) -> str:
    history_batches = history_batches or []
    stacks = []
    for batch, suggestions in batches:
        pending = [item for item in suggestions if item.status == "pending"]
        reviewed_count = len(suggestions) - len(pending)
        if pending:
            item = pending[0]
            relationship_type = RELATIONSHIP_TYPES_BY_KEY[item.type_key]
            label = relationship_type.label_for_role("source", item.source.metadata.get("sex", ""))
            chain_parts = []
            for relationship_id in item.supporting_relationship_ids:
                supporting = relationships_by_id.get(relationship_id)
                if supporting:
                    chain_parts.append(f'<a href="/relationships/{supporting.id}">{escape(supporting.source.title)} {escape(supporting.label)} {escape(supporting.target.title)}</a>')
            chain = " &rarr; ".join(chain_parts) or "Supporting records unavailable"
            dates = escape(format_date_with_precision(item.started_at, item.started_at_precision)) if item.started_at else "Unknown"
            card = f'''<article class="inference-card">
                <div class="inference-progress"><span>Suggestion {reviewed_count + 1} of {len(suggestions)}</span><span>{len(pending)} remaining</span></div>
                <p class="eyebrow">Suggested relationship</p><h3>{escape(item.source.title)} {escape(label)} {escape(item.target.title)}</h3>
                <p><strong>People:</strong> <a href="/{item.source.slug}/{item.source.id}">{escape(item.source.title)}</a> and <a href="/{item.target.slug}/{item.target.id}">{escape(item.target.title)}</a></p>
                <div class="inference-reason"><strong>Why this was suggested</strong><p>{chain}</p><p>Rule: {escape(item.rule_key)}</p></div>
                <p><strong>Suggested start date:</strong> {dates}</p>
                <form class="inference-actions" method="post" action="/relationships/inferences/{item.id}/review">
                    <button class="button" name="decision" value="confirm">Confirm relationship</button>
                    <button class="button secondary" name="decision" value="reject">Reject suggestion</button>
                </form></article>'''
        else:
            card = '<div class="inference-complete"><h3>Batch complete</h3><p>This batch will be archived automatically.</p></div>'
        stacks.append(f'''<section class="panel inference-batch"><div><p class="eyebrow">Review batch {batch['id']}</p><h2>{escape(batch['trigger_type'].replace('_', ' ').title())}</h2></div>{card}</section>''')
    content = "".join(stacks) if stacks else '<p class="empty">No inference batches await review.</p>'
    history = inference_history_section(history_batches)
    return f'''<section class="page-heading split"><div><h1>Inference Review Queue</h1><p>Review one deterministic suggestion at a time. Suggestions are not relationships until confirmed.</p></div><a class="button secondary" href="/relationships">Relationships</a></section>{content}{history}'''



def inference_history_section(history_batches) -> str:
    if not history_batches:
        return '<section class="panel inference-history"><h2>Historic batches</h2><p class="empty">No completed batches yet.</p></section>'
    batches = []
    for batch, suggestions in history_batches:
        items = []
        for item in suggestions:
            relationship_type = RELATIONSHIP_TYPES_BY_KEY[item.type_key]
            label = relationship_type.label_for_role("source", item.source.metadata.get("sex", ""))
            undo = ""
            if item.status in {"confirmed", "rejected"}:
                undo = f'''<form method="post" action="/relationships/inferences/{item.id}/undo"><button class="link-button" type="submit">Undo</button></form>'''
            items.append(f'''<li><span><strong>{escape(item.source.title)} {escape(label)} {escape(item.target.title)}</strong><small>{escape(item.status)} / reviewed {escape(item.reviewed_at or "unknown")}</small></span>{undo}</li>''')
        batches.append(f'''<section class="history-batch"><h3>Batch {batch['id']} / {escape(batch['trigger_type'].replace('_', ' ').title())} / {len(suggestions)} suggestions</h3><ul>{''.join(items)}</ul></section>''')
    return f'''<section class="inference-history-controls"><button class="button secondary" type="button" id="toggle-inference-history" aria-expanded="false" aria-controls="inference-history">Show archived batches ({len(history_batches)})</button></section>
    <section class="panel inference-history" id="inference-history" hidden><h2>Historic batches</h2><p>Completed batches are archived automatically. Undo reopens the batch and returns that suggestion to review.</p>{''.join(batches)}</section>
    <script>(() => {{ const button = document.getElementById('toggle-inference-history'); const history = document.getElementById('inference-history'); if (!button || !history) return; button.addEventListener('click', () => {{ const showing = history.hidden; history.hidden = !showing; button.setAttribute('aria-expanded', String(showing)); button.textContent = showing ? 'Hide archived batches' : 'Show archived batches ({len(history_batches)})'; if (showing) history.scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }}); }})();</script>'''
