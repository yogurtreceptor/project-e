"""Operational Inbox page for durable local reminder delivery."""

from html import escape
from app.reminder_service import InboxItem


def inbox_page(items: list[InboxItem], *, archived: bool, created: int = 0, page_size: int = 50, page: int = 1) -> str:
    rows = "".join(_item(item, archived) for item in items) or '<p class="empty">No Inbox items in this view.</p>'
    scan = f'<p class="status-row" role="status">Evaluated reminders; created {created} new item{"s" if created != 1 else ""}.</p>' if created else ""
    view = "Archived" if archived else "Active"
    archive_link = "/inbox?archived=0" if archived else "/inbox?archived=1"
    other = "Active" if archived else "Archived"
    options = "".join(
        '<option value="{}"{}>{}</option>'.format(
            size, " selected" if size == page_size else "", size
        ) for size in (10, 50, 100)
    )
    paging = "" if not archived else f'<form class="compact-form" method="get" action="/inbox"><input type="hidden" name="archived" value="1"><label><span>Items per page</span><select name="page_size">{options}</select></label><button class="button secondary">Apply</button></form><p><a href="/inbox?archived=1&page_size=500&page={page + 1}">Deep archive</a> shows older retained history as one long scroll.</p>'
    return f'''<section class="page-heading split"><div><p class="eyebrow">Operational attention</p><h1>Inbox</h1><p>Durable reminders and items requiring action.</p></div><div class="actions"><form method="post" action="/inbox/evaluate"><button class="button" type="submit">Evaluate reminders</button></form><a class="button secondary" href="{archive_link}">{other}</a></div></section>{scan}<section class="panel"><h2>{view} items</h2><div class="task-list">{rows}</div>{paging}</section>'''


def _item(item: InboxItem, archived: bool) -> str:
    source = _source_link(item)
    actions = "" if archived else f'''<div class="actions"><a class="button secondary" href="{source}">Open source</a><form method="post" action="/inbox/{item.id}/acknowledge"><button class="button secondary">Acknowledge</button></form><form method="post" action="/inbox/{item.id}/dismiss"><button class="button secondary">Dismiss</button></form><form method="post" action="/inbox/{item.id}/snooze_30m"><button class="button secondary">Snooze 30 min</button></form><form method="post" action="/inbox/{item.id}/snooze_next_open"><button class="button secondary">Until next open</button></form></div>'''
    state = item.state.replace("_", " ").title()
    return f'<article class="task-row"><div><h3>{escape(item.title)}</h3><p>{escape(item.reason.title())} · due {escape(item.due_at)} · {escape(state)}</p></div>{actions}</article>'


def _source_link(item: InboxItem) -> str:
    if item.source_kind == "event": return f"/events/{item.source_id}"
    if item.source_kind == "task_deadline": return f"/tasks/{item.source_id}"
    return f"/{'people' if item.source_kind == 'birthday' else 'documents'}/{item.source_id}"
