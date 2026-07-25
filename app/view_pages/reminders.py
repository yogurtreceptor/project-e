from html import escape


_UNITS = (("m", "Minutes"), ("h", "Hours"), ("d", "Days"), ("w", "Weeks"), ("mo", "Calendar months"))


def reminder_timing_fields(prefix: str, timings: list[str], *, label: str, help_text: str, allow_months: bool = False) -> str:
    rows = "".join(_timing_row(prefix, index, timing, allow_months) for index, timing in enumerate(timings))
    template = _timing_row(prefix, "__INDEX__", "", allow_months)
    return f'''<fieldset class="reminder-timings" data-reminder-timings data-reminder-prefix="{escape(prefix)}" data-reminder-maximum="10"><legend>{escape(label)}</legend><p class="help-text">{escape(help_text)}</p><div class="reminder-timing-rows" data-reminder-timing-rows>{rows}</div><template data-reminder-timing-template>{template}</template><button class="button secondary" type="button" data-add-reminder-timing>Add notification</button><p class="help-text">Up to 10 notifications.</p></fieldset>'''


def calendar_reminder_fields(configured_timings: list[str] | None, *, allow_months: bool = False) -> str:
    timings = configured_timings or []
    return f'''<fieldset class="reminder-policy" data-reminder-policy><legend>Event notifications</legend>{reminder_timing_fields("calendar_reminder", timings, label="Notification times", help_text="Add notifications for Events in this Calendar. With no rows, Events use the platform defaults.", allow_months=allow_months)}</fieldset>'''


def reminder_settings_page(title: str, back_url: str, override: dict[str, object], *, occurrence_date: str = "") -> str:
    custom = list(override["custom_timings"])
    suppressed = list(override["suppressed_timings"])
    occurrence = f'<p>Choose whether this change applies to occurrence {escape(occurrence_date)}, it and future occurrences, or the whole series.</p>' if occurrence_date else '<p>Custom notifications add to Calendar defaults. You can remove specific inherited notification times below.</p>'
    scope = f'''<input type="hidden" name="occurrence_date" value="{escape(occurrence_date)}"><label><span>Apply to</span><select name="recurrence_scope"><option value="this">This occurrence</option><option value="following">This and future occurrences</option><option value="all">All occurrences</option></select></label>''' if occurrence_date else ""
    return f'''<section class="page-heading"><p class="eyebrow">Operational attention</p><h1>Reminder settings — {escape(title)}</h1>{occurrence}</section><section class="panel"><form class="record-form" method="post">{scope}{reminder_timing_fields("custom_reminder", custom, label="Additional notifications", help_text="Without Event-specific rows, this Event uses its Calendar notifications. Add up to 10 total effective notifications.")}{reminder_timing_fields("suppressed_reminder", suppressed, label="Remove inherited notifications", help_text="Use the same value and unit as an inherited Calendar notification.")}<div class="actions"><a class="button secondary" href="{escape(back_url)}">Cancel</a><button class="button">Save reminder settings</button></div></form></section>'''


def reminder_policy_page(title: str, back_url: str, *, configured_timings: list[str] | None, inherited_timings: list[str]) -> str:
    configured = configured_timings is not None
    timings = configured_timings or []
    return f'''<section class="page-heading"><p class="eyebrow">Operational attention</p><h1>{escape(title)}</h1><p>Set notification times with individual value and unit controls.</p></section><section class="panel"><form class="record-form" method="post"><label><span>Policy</span><select name="mode"><option value="custom"{" selected" if configured else ""}>Use these notifications</option><option value="inherit"{" selected" if not configured else ""}>Use inherited defaults</option></select></label>{reminder_timing_fields("policy_reminder", timings, label="Notification times", help_text="Each notification is delivered before its source is due.", allow_months=True)}<p class="help-text">Inherited notifications: {escape(", ".join(inherited_timings))}.</p><div class="actions"><a class="button secondary" href="{escape(back_url)}">Cancel</a><button class="button">Save reminder policy</button></div></form></section>'''


def _timing_row(prefix: str, index: int | str, timing: str, allow_months: bool) -> str:
    amount, unit = _timing_parts(timing)
    options = "".join(f'<option value="{value}"{" selected" if value == unit else ""}>{label}</option>' for value, label in _UNITS if allow_months or value != "mo")
    return f'''<div class="reminder-timing-row"><label><span class="visually-hidden">Number</span><input name="{escape(prefix)}_amount_{index}" type="number" min="1" step="1" required value="{escape(amount)}"></label><label><span class="visually-hidden">Unit</span><select name="{escape(prefix)}_unit_{index}">{options}</select></label><button class="button quiet" type="button" data-remove-reminder-timing aria-label="Remove notification">Remove</button></div>'''


def _timing_parts(timing: str) -> tuple[str, str]:
    if timing.endswith("mo"):
        return timing[:-2], "mo"
    return (timing[:-1], timing[-1:]) if timing else ("1", "h")
