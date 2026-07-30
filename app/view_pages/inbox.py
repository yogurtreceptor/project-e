"""Operational Inbox page for durable local reminder delivery."""

from html import escape
from urllib.parse import urlencode
from app.reminder_service import InboxAction, InboxItem, UpcomingReminder


def inbox_page(items: list[InboxItem], *, archived: bool, action_history: dict[int, list[InboxAction]] | None = None, upcoming: list[UpcomingReminder] | None = None, archived_count: int = 0, deep_archive: bool = False, created: int = 0, page_size: int = 50, page: int = 1) -> str:
    action_history = action_history or {}
    rows = "".join(_item(item, archived, action_history.get(item.id, [])) for item in items) or '<p class="empty">No Inbox items in this view.</p>'
    scan = f'<p class="status-row" role="status">Evaluated reminders; created {created} new item{"s" if created != 1 else ""}.</p>' if created else ""
    view = "Archived" if archived else "Active"
    archive_link = "/inbox?archived=0" if archived else "/inbox?archived=1"
    other = "Active" if archived else "Archived"
    options = "".join(
        '<option value="{}"{}>{}</option>'.format(
            size, " selected" if size == page_size else "", size
        ) for size in (10, 50, 100)
    )
    paging = _archive_paging(page_size, page, archived_count, deep_archive) if archived else ""
    upcoming_rows = "" if archived else _upcoming_section(upcoming or [])
    return f'''<section class="page-heading split"><div><p class="eyebrow">Operational attention</p><h1>Inbox</h1><p>Durable reminders and items requiring action.</p></div><div class="actions"><form method="post" action="/inbox/evaluate"><button class="button" type="submit">Evaluate reminders</button></form><a class="button secondary" href="{archive_link}">{other}</a></div></section>{scan}<section class="panel"><h2>{'Deep archive' if deep_archive else view} items</h2><div class="task-list">{rows}</div>{paging}</section>{upcoming_rows}'''


def global_reminder_policies_page() -> str:
    return '''<section class="page-heading"><p class="eyebrow">Operational attention</p><h1>Global reminder defaults</h1><p>These defaults apply to derived birthdays and Document expiries.</p></section><section class="panel"><div class="actions"><a class="button secondary" href="/inbox/reminders/birthdays">Birthday reminders</a><a class="button secondary" href="/inbox/reminders/document-expiries">Document-expiry reminders</a><a class="button secondary" href="/inbox">Back to Inbox</a></div></section>'''


def _item(item: InboxItem, archived: bool, actions: list[InboxAction]) -> str:
    source = _source_link(item)
    controls = "" if archived else f'''<div class="actions"><a class="button secondary" href="{source}">Open source</a><form method="post" action="/inbox/{item.id}/acknowledge"><button class="button secondary">Acknowledge</button></form><form method="post" action="/inbox/{item.id}/dismiss"><button class="button secondary">Dismiss</button></form><form method="post" action="/inbox/{item.id}/snooze_30m"><button class="button secondary">Snooze 30 min</button></form><form method="post" action="/inbox/{item.id}/snooze_next_open"><button class="button secondary">Until next open</button></form></div>'''
    state = item.state.replace("_", " ").title()
    history = "" if not archived else _history(actions)
    return f'<article class="task-row"><div><h3>{escape(item.title)}</h3><p>{escape(item.reason.title())} · due {escape(item.due_at)} · {escape(state)}</p>{history}</div>{controls}</article>'


def _source_link(item: InboxItem) -> str:
    if item.source_kind == "event":
        if item.source_id < 0:
            return "/calendar?" + urlencode({
                "date": item.occurrence_key[:10],
                "external_preview": item.source_id,
            })
        return f"/events/{item.source_id}"
    if item.source_kind == "task_deadline": return f"/tasks/{item.source_id}"
    return f"/{'people' if item.source_kind == 'birthday' else 'documents'}/{item.source_id}"


def _upcoming_section(items: list[UpcomingReminder]) -> str:
    rows = "".join(
        f'<article class="task-row"><div><h3><a href="{_source_link(item)}">{escape(item.title)}</a></h3><p>Reminder {escape(item.timing)} before · attention {escape(item.attention_at)} · due {escape(item.due_at)}</p></div></article>'
        for item in items
    ) or '<p class="empty">No upcoming reminders in the current reminder window.</p>'
    return f'<section class="panel"><h2>Upcoming</h2><div class="task-list">{rows}</div></section>'


def _archive_paging(page_size: int, page: int, count: int, deep_archive: bool) -> str:
    if deep_archive:
        return '<p><a href="/inbox?archived=1">Back to the most recent archived items</a></p>'
    capped_count = min(count, 500)
    pages = max(1, (capped_count + page_size - 1) // page_size)
    previous = f'<a class="button secondary" href="/inbox?archived=1&page_size={page_size}&page={page - 1}">Previous</a>' if page > 1 else ""
    next_link = f'<a class="button secondary" href="/inbox?archived=1&page_size={page_size}&page={page + 1}">Next</a>' if page < pages else ""
    deep = '<p><a href="/inbox?archived=1&deep=1">Deep archive</a> shows history older than the most recent 500 items as one long scroll.</p>' if count > 500 and page == pages else ""
    return f'<form class="compact-form" method="get" action="/inbox"><input type="hidden" name="archived" value="1"><label><span>Items per page</span><select name="page_size">{"".join("<option value=\"{}\"{}>{}</option>".format(size, " selected" if size == page_size else "", size) for size in (10, 50, 100))}</select></label><button class="button secondary">Apply</button></form><p>Page {page} of {pages}</p><div class="actions">{previous}{next_link}</div>{deep}'


def _history(actions: list[InboxAction]) -> str:
    if not actions:
        return ""
    rows = "".join(f'<li>{escape(action.acted_at)} · {escape(action.action.replace("_", " "))} · {escape(action.resulting_state)}</li>' for action in actions)
    return f'<details><summary>Delivery history</summary><ul class="entity-link-list">{rows}</ul></details>'
