"""Reusable collapsed, searchable IANA-timezone combobox."""

from html import escape

from app.timezones import timezone_catalogue
from app.defaults import PLATFORM_TIMEZONE


def timezone_picker(
    field_id: str, value: str, *, name: str = "timezone", required: bool = True
) -> str:
    """Render an IANA timezone field that reveals choices only on demand."""
    selected = value or PLATFORM_TIMEZONE
    choices = []
    for timezone_name, countries, offset in timezone_catalogue():
        location = f" — {countries}" if countries else ""
        search_text = " ".join((timezone_name, countries, offset)).lower()
        choices.append(
            f'<button type="button" class="timezone-option" role="option" '
            f'data-timezone-value="{escape(timezone_name)}" '
            f'data-timezone-search-text="{escape(search_text)}">'
            f'<strong>{escape(timezone_name)}</strong>'
            f'<span>{escape(offset)}{escape(location)}</span></button>'
        )
    required_attribute = " required" if required else ""
    escaped_id = escape(field_id)
    return f'''<div class="timezone-picker" data-timezone-picker><label for="{escaped_id}"><span>Timezone</span></label><div class="timezone-combobox"><input id="{escaped_id}" name="{escape(name)}" value="{escape(selected)}" autocomplete="off" spellcheck="false" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="{escaped_id}-options" data-timezone-input{required_attribute}><button class="timezone-toggle" type="button" aria-label="Show timezone choices" aria-expanded="false" aria-controls="{escaped_id}-options" data-timezone-toggle>⌄</button><div class="timezone-options" id="{escaped_id}-options" role="listbox" hidden data-timezone-options><p class="help-text">Search by country, city, IANA name, or an offset such as UTC+10.</p><div class="timezone-option-list" data-timezone-option-list>{"".join(choices)}</div><p class="help-text timezone-no-results" hidden data-timezone-no-results>No matching timezones.</p></div></div></div>'''
