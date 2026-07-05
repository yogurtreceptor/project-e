from html import escape
import json

from app.entities import EntityDefinition
from app.taxonomy import TaxonomyChoice


def error_block(errors: list[str]) -> str:
    if not errors:
        return ""
    return (
        '<div class="errors"><strong>Check the form</strong><ul>'
        + "".join(f"<li>{escape(error)}</li>" for error in errors)
        + "</ul></div>"
    )


def duplicate_warning(matches: list, document_form: bool = False) -> str:
    if not matches:
        return ""
    items = "".join(
        f'<li><a href="/{match.record.slug}/{match.record.id}">{escape(match.record.title)}</a>'
        f'<span>Matched: {escape(", ".join(match.matched_fields))}</span></li>'
        for match in matches
    )
    file_note = (
        "<p>If you selected a new file, select it again before saving.</p>"
        if document_form
        else ""
    )
    return (
        '<div class="warnings"><strong>Possible duplicate records found</strong>'
        '<p>Review these records before creating another canonical record.</p>'
        f'<ul>{items}</ul>{file_note}</div>'
    )


def input_field(
    name: str,
    label: str,
    values: dict[str, str],
    multiline: bool = False,
    input_type: str = "text",
    attrs: str = "",
) -> str:
    value = escape(str(values.get(name, "")))
    if multiline:
        control = f'<textarea id="{name}" name="{name}" rows="5">{value}</textarea>'
    else:
        control = f'<input id="{name}" name="{name}" type="{escape(input_type)}" value="{value}"{attrs}>'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'


def entity_field_control(
    field, values: dict[str, str], name: str | None = None,
    field_options: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    name = name or field.name
    field_options = field_options or {}
    field_values = values
    if field.storage_kind == "alias":
        value = escape(str(values.get(name, "")))
        return (
            f'<label for="{escape(name)}"><span>{escape(field.label)}</span>'
            f'<textarea id="{escape(name)}" name="{escape(name)}" rows="4" '
            f'placeholder="One name per line">{value}</textarea>'
            f'<small class="field-help">Enter one alternate, former, trading or abbreviated name per line.</small></label>'
        )
    if field.storage_kind == "taxonomy":
        return taxonomy_field(
            name, field.label, field_options.get(field.name, []), field_values,
            "Choose any level or type to search the complete classification path.",
        )
    if field.storage_kind == "reference":
        if not field_options.get(field.name):
            return hidden_field(name, values)
        selected = {
            part for part in str(values.get(f"{field.name}__ids", values.get(name, ""))).split(",")
            if part
        }
        options = []
        for value, text in field_options.get(field.name, []):
            options.append(
                f'<label class="reference-picker-option" data-search-text="{escape(text.casefold())}">'
                f'<input type="checkbox" name="{escape(name)}" value="{escape(value)}"'
                f'{" checked" if value in selected else ""}>'
                f'<span>{escape(text)}</span></label>'
            )
        return (
            f'<fieldset class="reference-picker" data-reference-picker>'
            f'<legend>{escape(field.label)}</legend>'
            f'<label for="{name}__search"><span>Search {escape(field.label.lower())}</span>'
            f'<input id="{name}__search" type="search" autocomplete="off" '
            f'placeholder="Type to filter..." data-reference-search></label>'
            f'<div class="reference-picker-options" data-reference-options>{"".join(options)}</div>'
            f'<p class="reference-picker-empty" data-reference-empty hidden>No matching options.</p>'
            f'</fieldset>'
        )
    if field.storage_kind == "measurement":
        value = escape(str(values.get(f"{field.name}__value", values.get(name, ""))))
        current_unit = str(values.get(f"{field.name}__unit", ""))
        options = ['<option value="">Select unit...</option>']
        for unit_id, text in field_options.get(field.name, []):
            selected = " selected" if unit_id == current_unit else ""
            options.append(f'<option value="{escape(unit_id)}"{selected}>{escape(text)}</option>')
        return (
            f'<fieldset class="measurement-field"><legend>{escape(field.label)}</legend>'
            f'<label for="{name}"><span>Value</span><input id="{name}" name="{name}" type="number" min="0" step="any" value="{value}"></label>'
            f'<label for="{name}__unit"><span>Unit</span><select id="{name}__unit" name="{name}__unit">{"".join(options)}</select></label></fieldset>'
        )
    if field.default and not str(values.get(name, "")):
        field_values = {**values, name: field.default}
    if field.options and field.allow_custom:
        return custom_value_field(name, field.label, field.options, field_values)
    if field.options:
        return select_field(name, field.label, [(option, option) for option in field.options], field_values)
    attrs = ""
    if field.value_kind == "whole_number":
        attrs = ' min="0" step="1" inputmode="numeric" pattern="[0-9]*"'
    elif field.value_kind == "latitude":
        attrs = ' min="-90" max="90" step="any"'
    elif field.value_kind == "longitude":
        attrs = ' min="-180" max="180" step="any"'
    elif field.input_type == "number":
        attrs = ' step="any"'
    return input_field(name, field.label, field_values, field.multiline, field.input_type, attrs)


def entity_form_fields(
    definition: EntityDefinition,
    values: dict[str, str],
    name_prefix: str = "",
    field_options: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    """Render the shared editable fields used to create an entity."""
    fields = []
    if definition.type != "person":
        fields.append(input_field(f"{name_prefix}display_name", f"{definition.singular} name", values))
    optional_units = []
    rendered_groups = set()
    for field in definition.fields:
        name = f"{name_prefix}{field.name}"
        if field.editable:
            if field.optional:
                if field.optional_group:
                    if field.optional_group in rendered_groups:
                        continue
                    grouped_fields = tuple(
                        item for item in definition.fields
                        if item.editable and item.optional_group == field.optional_group
                    )
                    rendered_groups.add(field.optional_group)
                else:
                    grouped_fields = (field,)
                unit_names = tuple(f"{name_prefix}{item.name}" for item in grouped_fields)
                controls = tuple(
                    entity_field_control(item, values, unit_name, field_options)
                    for item, unit_name in zip(grouped_fields, unit_names)
                )
                label = field.optional_group_label or field.label
                key = f"{name_prefix}{field.optional_group or field.name}"
                populated = any(str(values.get(unit_name, "")).strip() for unit_name in unit_names)
                optional_units.append((key, label, controls, populated, len(grouped_fields) > 1))
                fields.append(optional_detail(key, label, controls, populated, len(grouped_fields) > 1))
            else:
                fields.append(entity_field_control(field, values, name, field_options))
        else:
            fields.append(hidden_field(name, values))
    if optional_units:
        fields.append(optional_details_controls(optional_units, name_prefix))
    if definition.type != "person":
        fields.append(input_field(f"{name_prefix}notes", "Notes", values, multiline=True))
    return "".join(fields)


def optional_detail(
    key: str, label: str, controls: tuple[str, ...], populated: bool, compound: bool,
) -> str:
    content = "".join(controls)
    remove = (
        f'<button class="optional-detail-remove" type="button" data-detail-remove="{escape(key)}" '
        f'aria-label="Hide {escape(label)}" title="Hide this detail; saved data is retained">&times;</button>'
    )
    tag = "fieldset" if compound else "div"
    legend = f'<legend>{escape(label)}</legend>' if compound else ""
    return (
        f'<{tag} class="optional-detail{(" optional-detail-compound" if compound else "")}" '
        f'data-optional-detail="{escape(key)}"{("" if populated else " hidden")}>'
        f'{legend}{remove}{content}</{tag}>'
    )


def optional_details_controls(optional_units: list[tuple], name_prefix: str = "") -> str:
    choices = "".join(
        f'<button class="button secondary optional-detail-add" type="button" data-detail-add="{escape(key)}"'
        f'{(" hidden" if populated else "")}>{escape(label)}</button>'
        for key, label, _, populated, _ in optional_units
    )
    has_choices = any(not populated for _, _, _, populated, _ in optional_units)
    root_id = f"{name_prefix}optional-details".replace("_", "-")
    choices_id = f"{root_id}-choices"
    return f"""
    <div class="optional-details-controls" id="{escape(root_id)}">
        <button class="button secondary optional-details-toggle" type="button" aria-expanded="false" aria-controls="{escape(choices_id)}"{' hidden' if not has_choices else ''}>Add details</button>
        <div class="optional-detail-choices" id="{escape(choices_id)}" hidden>{choices}</div>
    </div>
    <script>
    (() => {{
        const root = document.getElementById('{escape(root_id)}');
        if (!root) return;
        const form = root.closest('form') || document;
        const toggle = root.querySelector('.optional-details-toggle');
        const choices = root.querySelector('.optional-detail-choices');
        const availableChoices = () => [...choices.querySelectorAll('[data-detail-add]')].some((button) => !button.hidden);
        const closeChoices = () => {{
            choices.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
            toggle.hidden = !availableChoices();
        }};
        if (toggle && choices) {{
            toggle.addEventListener('click', () => {{
                choices.hidden = !choices.hidden;
                toggle.setAttribute('aria-expanded', String(!choices.hidden));
            }});
        }}
        root.querySelectorAll('[data-detail-add]').forEach((button) => {{
            button.addEventListener('click', () => {{
                const field = form.querySelector(`[data-optional-detail="${{button.dataset.detailAdd}}"]`);
                if (field) {{
                    field.hidden = false;
                    const input = field.querySelector('input, textarea, select');
                    if (input) input.focus();
                }}
                button.hidden = true;
                closeChoices();
            }});
        }});
        form.querySelectorAll('[data-detail-remove]').forEach((button) => {{
            button.addEventListener('click', () => {{
                const field = form.querySelector(`[data-optional-detail="${{button.dataset.detailRemove}}"]`);
                const choice = root.querySelector(`[data-detail-add="${{button.dataset.detailRemove}}"]`);
                if (field) field.hidden = true;
                if (choice) choice.hidden = false;
                toggle.hidden = false;
                choices.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
                toggle.focus();
            }});
        }});
        form.addEventListener('input', (event) => {{
            const field = event.target.closest('[data-optional-detail]');
            if (!field || !event.target.value) return;
            field.hidden = false;
            const choice = root.querySelector(`[data-detail-add="${{field.dataset.optionalDetail}}"]`);
            if (choice) choice.hidden = true;
            toggle.hidden = !availableChoices();
        }});
        form.querySelectorAll('[data-reference-picker]').forEach((picker) => {{
            const search = picker.querySelector('[data-reference-search]');
            const options = [...picker.querySelectorAll('.reference-picker-option')];
            const empty = picker.querySelector('[data-reference-empty]');
            if (!search) return;
            search.addEventListener('input', () => {{
                const query = search.value.trim().toLocaleLowerCase();
                let visible = 0;
                options.forEach((option) => {{
                    const matches = !query || option.dataset.searchText.includes(query);
                    option.hidden = !matches;
                    if (matches) visible += 1;
                }});
                if (empty) empty.hidden = visible !== 0;
            }});
        }});
    }})();
    </script>
    """


def custom_value_field(
    name: str,
    label: str,
    options: tuple[str, ...],
    values: dict[str, str],
) -> str:
    value = escape(str(values.get(name, "")))
    list_id = f"{name}_options"
    option_html = "".join(f'<option value="{escape(option)}"></option>' for option in options)
    control = f'<input id="{name}" name="{name}" list="{list_id}" value="{value}"><datalist id="{list_id}">{option_html}</datalist>'
    return f'<label for="{name}"><span>{escape(label)}</span>{control}</label>'


def taxonomy_field(
    name: str, label: str, options: list[TaxonomyChoice] | list[tuple[str, str]],
    values: dict[str, str], help_text: str = "",
) -> str:
    current = str(values.get(f"{name}__taxonomy_entry_id", values.get(name, "")))
    choices = [
        option if isinstance(option, TaxonomyChoice)
        else TaxonomyChoice(option[0], option[1], option[1], option[1].count(" › "))
        for option in options
    ]
    data = [
        {"value": item.value, "label": item.label, "path": item.path,
         "depth": item.depth, "available": item.available, "display": item.display_text}
        for item in choices
    ]
    selected = next((item for item in choices if item.value == current), None)
    search_id = f"{name}__search"
    list_id = f"{name}__options"
    safe_data = json.dumps(data).replace("</", "<\\/")
    help_html = f'<p class="field-help">{escape(help_text)}</p>' if help_text else ""
    return (
        f'<div class="taxonomy-combobox" data-taxonomy-combobox><label for="{search_id}"><span>{escape(label)}</span>'
        f'<div class="taxonomy-combobox-input"><input id="{search_id}" type="text" role="combobox" aria-autocomplete="list" '
        f'aria-expanded="false" aria-controls="{list_id}" autocomplete="off" placeholder="Browse or type to search..." '
        f'value="{escape(selected.display_text if selected else "")}" data-taxonomy-input><button type="button" aria-label="Show {escape(label.lower())} options" data-taxonomy-toggle>▾</button></div></label>'
        f'{help_html}<input type="hidden" id="{name}" name="{name}" value="{escape(current)}" data-taxonomy-value>'
        f'<div id="{list_id}" class="taxonomy-combobox-list" role="listbox" hidden data-taxonomy-list></div>'
        f'<p class="taxonomy-combobox-empty" hidden data-taxonomy-empty>No matching taxonomy paths.</p>'
        f'<script type="application/json" data-taxonomy-data>{safe_data}</script></div>'
    )


def hidden_field(name: str, values: dict[str, str]) -> str:
    return f'<input type="hidden" name="{escape(name)}" value="{escape(str(values.get(name, "")))}">'


def file_upload_field(values: dict[str, str]) -> str:
    current_file = values.get("file_name", "")
    current = f'<p class="empty">Current file: {escape(current_file)}</p>' if current_file else ""
    return f"""
    <label for="upload"><span>Upload file</span><input id="upload" name="upload" type="file"></label>
    {current}
    """


def select_field(
    name: str, label: str, options: list[tuple[str, str]], values: dict[str, str]
) -> str:
    current = str(values.get(name, ""))
    option_html = ['<option value="">Select...</option>']
    for value, text in options:
        selected = " selected" if value == current else ""
        option_html.append(
            f'<option value="{escape(value)}"{selected}>{escape(text)}</option>'
        )
    return f'<label for="{name}"><span>{escape(label)}</span><select id="{name}" name="{name}">{"".join(option_html)}</select></label>'


def existing_location_action(definition: EntityDefinition) -> str:
    if definition.type != "location":
        return ""
    return '<a class="button secondary" href="/locations">Existing Locations</a>'


def address_lookup_field() -> str:
    return """
    <div class="address-lookup-field">
        <label for="address_search"><span>Address lookup</span>
            <input id="address_search" name="address_search" type="search" autocomplete="off" placeholder="Enter a full or near-full address">
        </label>
        <div class="address-lookup-actions">
            <button class="button secondary" id="address_search_button" type="button">Search Address</button>
            <span class="address-lookup-status" id="address_lookup_status" role="status"></span>
        </div>
        <div class="address-results" id="address_results"></div>
    </div>
    """


def address_lookup_script() -> str:
    return """
    <script>
    (() => {
        const search = document.getElementById('address_search');
        const button = document.getElementById('address_search_button');
        const resultsList = document.getElementById('address_results');
        const status = document.getElementById('address_lookup_status');
        if (!search || !button || !resultsList || !status) return;
        const fields = ['formatted_address', 'address_line_1', 'address_line_2', 'suburb', 'city', 'state', 'post_code', 'country', 'latitude', 'longitude', 'source'];
        const setStatus = (message) => {
            status.textContent = message;
        };
        const fill = (result) => {
            fields.forEach((name) => {
                const input = document.getElementById(name);
                if (input && result[name] !== undefined) {
                    input.value = result[name];
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
            if (result.label) search.value = result.label;
            setStatus('Address fields filled. You can still edit them manually.');
        };
        const renderResults = (results) => {
            resultsList.innerHTML = '';
            if (!results.length) {
                resultsList.innerHTML = '<p class="empty">No matching addresses found. Try a fuller address, nearby suburb, or enter details manually.</p>';
                return;
            }
            const list = document.createElement('ul');
            results.forEach((result) => {
                const item = document.createElement('li');
                const choose = document.createElement('button');
                choose.type = 'button';
                choose.className = 'link-button address-result-button';
                choose.textContent = result.label || result.formatted_address || 'Unnamed result';
                choose.addEventListener('click', () => fill(result));
                item.appendChild(choose);
                if (result.latitude && result.longitude) {
                    const coordinates = document.createElement('span');
                    coordinates.textContent = `${result.latitude}, ${result.longitude}`;
                    item.appendChild(coordinates);
                }
                list.appendChild(item);
            });
            resultsList.appendChild(list);
        };
        const lookup = async () => {
            const query = search.value.trim();
            if (query.length < 3) {
                setStatus('Enter at least 3 characters.');
                return;
            }
            button.disabled = true;
            setStatus('Searching...');
            resultsList.innerHTML = '';
            try {
                const response = await fetch(`/geocoding/search?q=${encodeURIComponent(query)}`);
                const payload = await response.json();
                renderResults(payload.results || []);
                if (payload.error) setStatus('Lookup unavailable. You can enter the address manually.');
                else setStatus((payload.results || []).length ? 'Choose a result to fill the address fields.' : 'No results found.');
            } catch (error) {
                renderResults([]);
                setStatus('Lookup unavailable. You can enter the address manually.');
            } finally {
                button.disabled = false;
            }
        };
        button.addEventListener('click', lookup);
        search.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                lookup();
            }
        });
    })();
    </script>
    """
