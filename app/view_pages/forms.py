from html import escape
import json

from app.entities import EntityDefinition


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
    if field.storage_kind == "taxonomy":
        return taxonomy_field(name, field.label, field_options.get(field.name, []), field_values)
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
    optional_fields = []
    for field in definition.fields:
        name = f"{name_prefix}{field.name}"
        if field.editable:
            control = entity_field_control(field, values, name, field_options)
            if field.optional:
                optional_fields.append((field, name, control))
            else:
                fields.append(control)
        else:
            fields.append(hidden_field(name, values))
    if optional_fields:
        fields.append(optional_fields_section(optional_fields, values))
    if definition.type != "person":
        fields.append(input_field(f"{name_prefix}notes", "Notes", values, multiline=True))
    return "".join(fields)


def optional_fields_section(optional_fields: list[tuple], values: dict[str, str]) -> str:
    choices = "".join(
        f'<button class="button secondary optional-field-add" type="button" data-field="{escape(name)}">{escape(field.label)}</button>'
        for field, name, _ in optional_fields
        if not str(values.get(name, "")).strip()
    )
    controls = "".join(
        f'<div class="optional-field" data-optional-field="{escape(name)}"{("" if str(values.get(name, "")).strip() else " hidden")}>{control}</div>'
        for _, name, control in optional_fields
    )
    has_choices = bool(choices)
    return f"""
    <section class="optional-fields">
        <button class="button secondary optional-fields-toggle" type="button" aria-expanded="false" aria-controls="optional-field-choices"{' hidden' if not has_choices else ''}>Add field</button>
        <div class="optional-field-choices" id="optional-field-choices" hidden>{choices}</div>
        {controls}
    </section>
    <script>
    (() => {{
        const toggle = document.querySelector('.optional-fields-toggle');
        const choices = document.querySelector('.optional-field-choices');
        if (toggle && choices) {{
            toggle.addEventListener('click', () => {{
                choices.hidden = !choices.hidden;
                toggle.setAttribute('aria-expanded', String(!choices.hidden));
            }});
        }}
        document.querySelectorAll('.optional-field-add').forEach((button) => {{
            button.addEventListener('click', () => {{
                const field = document.querySelector(`[data-optional-field="${{button.dataset.field}}"]`);
                if (field) {{
                    field.hidden = false;
                    const input = field.querySelector('input, textarea, select');
                    if (input) input.focus();
                }}
                button.remove();
                if (choices) choices.hidden = true;
                if (toggle) {{
                    toggle.setAttribute('aria-expanded', 'false');
                    if (choices && !choices.children.length) toggle.hidden = true;
                }}
            }});
        }});
        document.querySelectorAll('[data-reference-picker]').forEach((picker) => {{
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


def taxonomy_field(name: str, label: str, options: list[tuple[str, str]], values: dict[str, str]) -> str:
    current = str(values.get(f"{name}__taxonomy_entry_id", values.get(name, "")))
    data = [{"id": value, "parts": path.split(" › "), "path": path} for value, path in options]
    roots = []
    for item in data:
        if len(item["parts"]) == 1:
            roots.append(item)
    root_options = ['<option value="">Select...</option>'] + [f'<option value="{escape(item["id"])}">{escape(item["path"])}</option>' for item in roots]
    result_options = ['<option value="">Select a matching path...</option>'] + [f'<option value="{escape(item["id"])}">{escape(item["path"])}</option>' for item in data]
    search_id = f"{name}__search"
    safe_data = json.dumps(data).replace("</", "<\\/")
    return (
        f'<div class="taxonomy-picker" data-taxonomy-picker><label for="{search_id}"><span>Search {escape(label.lower())}</span>'
        f'<input id="{search_id}" type="search" autocomplete="off" placeholder="Type to filter paths..." data-taxonomy-search></label>'
        f'<select aria-label="Matching taxonomy paths" data-taxonomy-results>{"".join(result_options)}</select>'
        f'<input type="hidden" id="{name}" name="{name}" value="{escape(current)}" data-taxonomy-value>'
        f'<label><span>Type</span><select required data-taxonomy-level="0">{"".join(root_options)}</select></label>'
        '<label hidden data-taxonomy-level-wrap="1"><span>Subtype</span><select data-taxonomy-level="1"></select></label>'
        '<label hidden data-taxonomy-level-wrap="2"><span>Specific subtype</span><select data-taxonomy-level="2"></select></label></div>'
        f'''<script>(()=>{{const p=document.currentScript.previousElementSibling;const items={safe_data};const value=p.querySelector("[data-taxonomy-value]");const levels=[...p.querySelectorAll("[data-taxonomy-level]")];const results=p.querySelector("[data-taxonomy-results]");const search=p.querySelector("[data-taxonomy-search]");const byId=new Map(items.map(x=>[x.id,x]));const choose=(id)=>{{const item=byId.get(id);if(!item)return;value.value=id;results.value=id;item.parts.forEach((part,depth)=>{{const match=items.find(x=>x.parts.length===depth+1&&x.parts.every((v,i)=>v===item.parts[i]));if(match){{fill(depth,item.parts.slice(0,depth));levels[depth].value=match.id;}}}});fill(item.parts.length,item.parts);}};const fill=(depth,prefix)=>{{if(depth>2)return;const select=levels[depth],wrap=depth?select.closest("label"):null;const children=items.filter(x=>x.parts.length===depth+1&&prefix.every((v,i)=>x.parts[i]===v));if(wrap)wrap.hidden=!children.length;if(!children.length)return;const old=select.value;select.innerHTML='<option value="">Select...</option>'+children.map(x=>`<option value="${{x.id}}">${{x.parts[depth]}}</option>`).join('');if(children.some(x=>x.id===old))select.value=old;}};levels.forEach((select,depth)=>select.addEventListener('change',()=>{{const item=byId.get(select.value);if(!item)return;value.value=item.id;results.value=item.id;for(let d=depth+1;d<3;d++){{const wrap=levels[d].closest('label');if(wrap)wrap.hidden=true;levels[d].innerHTML='';}}fill(depth+1,item.parts);}}));search.addEventListener('input',()=>{{const q=search.value.trim().toLocaleLowerCase();[...results.options].forEach((o,i)=>{{if(i)o.hidden=!!q&&!o.text.toLocaleLowerCase().includes(q);}});}});results.addEventListener('change',()=>choose(results.value));fill(0,[]);choose(value.value);}})();</script>'''
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
                if (input && result[name] !== undefined) input.value = result[name];
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
