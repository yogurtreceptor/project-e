import json
from html import escape

from app.entities import ENTITY_DEFINITIONS, EntityDefinition, EntityRecord
from app.relationships import (
    DATE_PRECISIONS,
    RELATIONSHIP_STATUSES,
    RELATIONSHIP_TYPES,
    RelationshipRecord,
    relationship_choices_for_context,
)
from app.view_pages.common import format_date_with_precision
from app.view_pages.forms import entity_form_fields, error_block, input_field, select_field
from app.graph_layout import GraphLayout


INLINE_RELATIONSHIP_ENTITY_TYPES = {"person", "organisation", "location"}


def family_tree_page(tree: GraphLayout) -> str:
    if not tree.nodes:
        visual = '<p class="empty">No supported family relationships yet. Add parent/child, sibling, spouse or partner relationships between People first.</p>'
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
        nodes = "".join(f'<a href="{escape(node.href)}"><rect x="{node.x - 72}" y="{node.y - 26}" width="144" height="52" rx="8"/><text x="{node.x}" y="{node.y + 5}">{escape(node.label)}</text></a>' for node in tree.nodes)
        visual = f'<div class="family-tree-scroll"><svg class="family-tree" viewBox="0 0 {tree.width} {tree.height}" width="{tree.width}" height="{tree.height}" role="img" aria-label="Family relationship tree">{"".join(lines)}{nodes}</svg></div>'
    return f"""
    <section class="page-heading split">
        <div><p class="eyebrow">Relationship visualisation</p><h1>Family tree</h1><p>A derived view of existing family relationships. No separate family data is stored.</p></div>
        <a class="button secondary" href="/relationships">Back to relationships</a>
    </section>
    <section class="panel family-tree-panel">{visual}</section>
    <section class="family-tree-legend" aria-label="Family tree connector key"><strong>Connector key</strong><span><i class="legend-line legend-partner"></i>Partner / spouse</span><span><i class="legend-line legend-sibling"></i>Sibling</span><span><i class="legend-line legend-parent"></i>Parent / child</span></section>
    <section class="panel"><h2>Included relationships</h2><p>Parent/child links connect adjacent generations, with children grouped only when their complete recorded parent sets match; each group uses an independent connector. Sibling, spouse and partner links are shown on the same generation where the available data permits. Relationships spanning multiple generations remain stored but are shown through the parent/child chain instead of redundant direct lines.</p></section>
    """


def _hierarchy_connector_paths(tree: GraphLayout, positions: dict) -> list[str]:
    """Route every exact incoming-source set through independent ports and lanes."""
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
        if not sources or not targets:
            continue
        bundles.append((source_ids, tuple(sorted(target_ids)), sources, targets))
    bundles.sort(key=lambda bundle: (min(target.x for target in bundle[3]), bundle[0], bundle[1]))

    bundles_by_gap: dict[tuple[int, int], list[tuple]] = {}
    for bundle in bundles:
        source_y = max(source.y for source in bundle[2]) + 26
        target_y = min(target.y for target in bundle[3]) - 26
        bundles_by_gap.setdefault((source_y, target_y), []).append(bundle)

    source_bundles: dict[int, list[tuple[int, ...]]] = {}
    for source_ids, _, _, _ in bundles:
        for source_id in source_ids:
            source_bundles.setdefault(source_id, []).append(source_ids)
    source_ports: dict[tuple[int, tuple[int, ...]], int] = {}
    for source_id, source_sets in source_bundles.items():
        ordered_sets = sorted(source_sets)
        step = min(24, 96 // max(1, len(ordered_sets) - 1))
        start_offset = -(step * (len(ordered_sets) - 1)) // 2
        for index, source_ids in enumerate(ordered_sets):
            source_ports[(source_id, source_ids)] = positions[source_id].x + start_offset + index * step

    paths: list[str] = []
    for (source_y, target_y), gap_bundles in sorted(bundles_by_gap.items()):
        available_height = target_y - source_y
        lane_step = max(8, min(18, available_height // max(4, len(gap_bundles) * 2 + 2)))
        for lane_index, (source_ids, target_ids, sources, targets) in enumerate(gap_bundles):
            parent_bar_y = source_y + lane_step * (lane_index + 1)
            child_bar_y = target_y - lane_step * (len(gap_bundles) - lane_index)
            source_port_pairs = sorted((source.id, source_ports[(source.id, source_ids)]) for source in sources)
            source_xs = sorted(x for _, x in source_port_pairs)
            target_xs = sorted(target.x for target in targets)
            trunk_x = sum(target_xs) // len(target_xs)
            parent_centre_x = (source_xs[0] + source_xs[-1]) // 2
            commands = [f"M {x} {source_y} V {parent_bar_y}" for x in source_xs]
            if len(source_xs) > 1:
                commands.append(f"M {source_xs[0]} {parent_bar_y} H {source_xs[-1]}")
            commands.append(f"M {parent_centre_x} {parent_bar_y} H {trunk_x} V {child_bar_y}")
            if len(target_xs) > 1:
                commands.append(f"M {target_xs[0]} {child_bar_y} H {target_xs[-1]}")
            commands.extend(f"M {x} {child_bar_y} V {target_y}" for x in target_xs)
            source_set = ",".join(str(source_id) for source_id in source_ids)
            target_set = ",".join(str(target_id) for target_id in target_ids)
            source_port_set = ",".join(f"{source_id}:{x}" for source_id, x in source_port_pairs)
            path_data = " ".join(commands)
            paths.append(f'<path class="family-edge-casing" d="{path_data}" aria-hidden="true" />')
            paths.append(
                f'<path class="family-edge family-edge-hierarchy family-edge-bundle" '
                f'data-source-set="{source_set}" data-target-set="{target_set}" '
                f'data-source-ports="{source_port_set}" data-lane="{parent_bar_y},{child_bar_y}" '
                f'd="{path_data}" />'
            )
    return paths


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
                    <td>{escape(relationship.status)}</td>
                    <td class="row-actions">
                        <a href="/relationships/{relationship.id}/edit">Edit</a>
                        <form method="post" action="/relationships/{relationship.id}/delete">
                            <button class="link-button" type="submit">Delete</button>
                        </form>
                    </td>
                </tr>
                """
            )
        content = (
            """
            <table>
                <thead><tr><th>Type</th><th>Source</th><th>Target</th><th>Status</th><th></th></tr></thead>
                <tbody>"""
            + "".join(rows)
            + "</tbody></table>"
        )
    return f"""
    <section class="page-heading split">
        <div>
            <h1>Relationships</h1>
            <p>Browse first-class links between any entity types.</p>
        </div>
        <a class="button secondary" href="/relationships/family-tree">View family tree</a>
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
            <dt>Started</dt><dd>{escape(format_date_with_precision(relationship.started_at, relationship.started_at_precision))}</dd>
            {ended_date}
        </dl>
    </section>
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
        new_entity_workflow(target_type, workflow_mode, values),
        relationship_metadata_fields(source_entity, connected_type, connected_sex, selected_target, values),
    ])
    return f"""
    <section class="page-heading">
        <p class="eyebrow">Relationship</p>
        <h1>{escape(action)} Relationship</h1>
    </section>
    <section class="panel">
        {error_block(errors)}
        <form class="record-form relationship-form" method="post" action="{form_action}">
            {''.join(fields)}
            <div class="actions">
                <a class="button secondary" href="{'/' + context_entity.slug + '/' + str(context_entity.id) if context_entity else '/relationships'}">Cancel</a>
                <button class="button" type="submit">Save</button>
            </div>
        </form>
    </section>
    {relationship_form_script(entities, target_type, source_entity)}
    """


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


def new_entity_workflow(target_type: str | None, workflow_mode: str, values: dict[str, str] | None = None) -> str:
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
                {entity_form_fields(definition, values, name_prefix="new_")}
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
    options = relationship_type_options(source_entity, connected_type, connected_sex)
    current_name = source_entity.title if source_entity else "the current entity"
    connected_name = selected_target.title if selected_target else inline_connected_name(connected_type, values)
    connected_label = connected_name or "the connected entity"
    prompt = f"What is {connected_label} in relation to {current_name}?"
    return f"""
    <fieldset class="relationship-step relationship-metadata">
        <legend>Relationship details</legend>
        <p class="relationship-question" id="relationship_question" data-current-name="{escape(current_name)}">{escape(prompt)}</p>
        {select_field("type", "Relationship", options, values)}
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
    return [(relationship_type.key, relationship_option_text(relationship_type)) for relationship_type in RELATIONSHIP_TYPES if relationship_type.selectable]


def relationship_option_text(relationship_type) -> str:
    return relationship_type.display_label


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
            "choices": relationship_choices_for_context(source_entity.type, entity.type, entity.metadata.get("sex", "Unknown")) if source_entity else [],
        }
        for entity in entities
        if entity.id != (source_entity.id if source_entity else None)
    ]
    choice_types = sorted({entity.type for entity in entities} | {target_type or ""} - {""})
    choices_by_type = {
        entity_type: relationship_choices_for_context(source_entity.type, entity_type, "Unknown")
        for entity_type in choice_types
        if source_entity is not None
    }
    choices_by_type_and_sex = {
        sex: {
            entity_type: relationship_choices_for_context(source_entity.type, entity_type, sex)
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
            if (!type) return;
            const current = type.value;
            type.innerHTML = '<option value="">Select...</option>';
            (choices || []).forEach(([value, label]) => {{
                const option = document.createElement('option');
                option.value = value;
                option.textContent = label;
                if (value === current) option.selected = true;
                type.appendChild(option);
            }});
            if (current && !(choices || []).some(([value]) => value === current)) type.value = '';
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
