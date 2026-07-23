from html import escape


def reminder_settings_page(title: str, back_url: str, override: dict[str, object], *, occurrence_date: str = "") -> str:
    mode = str(override["mode"])
    custom = ", ".join(override["custom_timings"])
    suppressed = ", ".join(override["suppressed_timings"])
    occurrence = f'<p>This applies only to occurrence {escape(occurrence_date)}.</p>' if occurrence_date else '<p>This applies to the whole record. Custom timings add to defaults; suppressed timings remove inherited defaults.</p>'
    return f'''<section class="page-heading"><p class="eyebrow">Operational attention</p><h1>Reminder settings — {escape(title)}</h1>{occurrence}</section><section class="panel"><form class="record-form" method="post"><label><span>Reminder policy</span><select name="mode"><option value="default"{" selected" if mode == "default" else ""}>Use defaults</option><option value="custom"{" selected" if mode == "custom" else ""}>Use defaults with custom timings</option><option value="disabled"{" selected" if mode == "disabled" else ""}>Disable reminders</option></select></label><label><span>Add timings</span><input name="custom_timings" value="{escape(custom)}" placeholder="e.g. 2h, 1d"></label><label><span>Suppress inherited timings</span><input name="suppressed_timings" value="{escape(suppressed)}" placeholder="e.g. 10m"></label><p class="help-text">Use comma-separated positive timing tokens: m, h, d, w or mo.</p><div class="actions"><a class="button secondary" href="{escape(back_url)}">Cancel</a><button class="button">Save reminder settings</button></div></form></section>'''
