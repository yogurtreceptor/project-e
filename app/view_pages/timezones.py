"""Reusable searchable IANA-timezone picker."""

from html import escape

from app.timezones import timezone_catalogue


def timezone_picker(
    field_id: str, value: str, *, name: str = "timezone", required: bool = True
) -> str:
    """Render a progressively enhanced, scrollable timezone selector."""
    selected = value or "Australia/Brisbane"
    field_name = name
    options = []
    known = False
    for timezone_name, countries, offset in timezone_catalogue():
        is_selected = timezone_name == selected
        known = known or is_selected
        location = f" — {countries}" if countries else ""
        options.append(
            f'<option value="{escape(timezone_name)}"{" selected" if is_selected else ""}>'
            f'{escape(offset)} · {escape(timezone_name)}{escape(location)}</option>'
        )
    if not known:
        options.insert(0, f'<option value="{escape(selected)}" selected>{escape(selected)}</option>')
    required_attribute = " required" if required else ""
    return f'''<div class="timezone-picker" data-timezone-picker><label for="{escape(field_id)}"><span>Timezone</span></label><input id="{escape(field_id)}-search" type="search" placeholder="Search country, place, or UTC+/- offset" data-timezone-search autocomplete="off"><select id="{escape(field_id)}" name="{escape(field_name)}" size="8" data-timezone-select{required_attribute}>{"".join(options)}</select><p class="help-text">Search by country, city, IANA name, or an offset such as UTC+10.</p></div>'''
