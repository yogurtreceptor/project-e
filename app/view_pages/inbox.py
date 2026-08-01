"""Operational Inbox page for durable local reminder attention."""

from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from app.defaults import PLATFORM_TIMEZONE
from app.reminder_service import InboxAction, InboxItem
from app.view_pages.icons import icon


def inbox_page(
    items: list[InboxItem],
    *,
    archived: bool,
    action_history: dict[int, list[InboxAction]] | None = None,
    archived_count: int = 0,
    deep_archive: bool = False,
    page_size: int = 50,
    page: int = 1,
    now: datetime | None = None,
) -> str:
    action_history = action_history or {}
    archive_link = "/inbox" if archived else "/inbox?archived=1"
    archive_label = "Inbox" if archived else "Archive"
    heading = "Deep archive" if deep_archive else "Archive" if archived else "Inbox"
    description = (
        "Reminder delivery and action history."
        if archived
        else "Reminders that need your attention."
    )
    rows = (
        _archive_rows(items, action_history)
        if archived
        else _active_groups(items, now=now)
    )
    paging = (
        _archive_paging(page_size, page, archived_count, deep_archive)
        if archived
        else ""
    )
    return f'''<section class="page-heading split inbox-heading"><div><p class="eyebrow">Reminders</p><h1>{heading}</h1><p>{description}</p></div><a class="button quiet" href="{archive_link}">{archive_label}</a></section><section class="inbox-queue" aria-label="{heading}">{rows}{paging}</section>'''


def global_reminder_policies_page() -> str:
    return '''<section class="page-heading"><p class="eyebrow">Operational attention</p><h1>Global reminder defaults</h1><p>These defaults apply to derived birthdays and Document expiries.</p></section><section class="panel"><div class="actions"><a class="button secondary" href="/inbox/reminders/birthdays">Birthday reminders</a><a class="button secondary" href="/inbox/reminders/document-expiries">Document-expiry reminders</a><a class="button secondary" href="/inbox">Back to Inbox</a></div></section>'''


def _active_groups(items: list[InboxItem], *, now: datetime | None) -> str:
    if not items:
        return '<div class="inbox-empty"><h2>You’re all caught up</h2><p>No reminders need your attention.</p></div>'
    instant = (now or datetime.now(ZoneInfo(PLATFORM_TIMEZONE))).astimezone(
        ZoneInfo(PLATFORM_TIMEZONE)
    )
    groups: list[tuple[str, list[InboxItem]]] = []
    for item in items:
        label = _date_group(item, instant)
        if not groups or groups[-1][0] != label:
            groups.append((label, []))
        groups[-1][1].append(item)
    return "".join(
        f'<section class="inbox-group" aria-labelledby="inbox-group-{index}"><h2 id="inbox-group-{index}">{escape(label)}</h2><div class="inbox-list">{"".join(_item(item, False, []) for item in group)}</div></section>'
        for index, (label, group) in enumerate(groups, start=1)
    )


def _archive_rows(
    items: list[InboxItem], action_history: dict[int, list[InboxAction]]
) -> str:
    if not items:
        return '<div class="inbox-empty"><h2>No archived reminders</h2><p>Completed reminder history will appear here.</p></div>'
    return '<div class="inbox-list inbox-archive-list">' + "".join(
        _item(item, True, action_history.get(item.id, [])) for item in items
    ) + "</div>"


def _item(item: InboxItem, archived: bool, actions: list[InboxAction]) -> str:
    controls = "" if archived else _controls(item)
    state = item.state.replace("_", " ").title()
    source_label = "Document expiry" if item.source_kind == "document_expiry" else "Event"
    due_label = _due_label(item)
    state_label = f" · {escape(state)}" if archived else ""
    history = _history(actions) if archived else ""
    return f'''<article class="inbox-row"><div class="inbox-row-content"><h3>{escape(item.title)}</h3><p class="inbox-row-meta">{source_label} · {due_label}{state_label}</p>{history}</div>{controls}</article>'''


def _controls(item: InboxItem) -> str:
    open_label = "Open document" if item.source_kind == "document_expiry" else "Open event"
    return f'''<div class="inbox-row-actions"><form method="post" action="/inbox/{item.id}/open"><button class="button" type="submit">{open_label}</button></form><form method="post" action="/inbox/{item.id}/snooze_10m"><button class="button quiet icon-button inbox-snooze" type="submit" aria-label="Snooze 10 minutes" title="Snooze 10 minutes">{icon("snooze")}</button></form><form method="post" action="/inbox/{item.id}/dismiss"><button class="button quiet" type="submit">Dismiss</button></form></div>'''


def _date_group(item: InboxItem, now: datetime) -> str:
    due = _local_datetime(item.due_at)
    if item.reason == "overdue" or due.date() < now.date():
        return "Overdue"
    if due.date() == now.date():
        return "Today"
    if due.date() == now.date() + timedelta(days=1):
        return "Tomorrow"
    return f"{due.strftime('%A')}, {due.day} {due.strftime('%B')}"


def _due_label(item: InboxItem) -> str:
    due = _local_datetime(item.due_at)
    full = due.strftime("%A, %d %B %Y at %H:%M %Z")
    if item.reason == "overdue":
        text = f"expired {due.day} {due.strftime('%B %Y')}"
    elif len(item.occurrence_key) == 10:
        text = f"{due.day} {due.strftime('%B %Y')}"
    else:
        text = due.strftime("%H:%M")
    return f'<time datetime="{escape(item.due_at)}" title="{escape(full)}">{escape(text)}</time>'


def _local_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        ZoneInfo(PLATFORM_TIMEZONE)
    )


def _archive_paging(page_size: int, page: int, count: int, deep_archive: bool) -> str:
    if deep_archive:
        return '<p class="inbox-archive-return"><a href="/inbox?archived=1">Back to the most recent archived reminders</a></p>'
    capped_count = min(count, 500)
    pages = max(1, (capped_count + page_size - 1) // page_size)
    previous = f'<a class="button secondary" href="/inbox?archived=1&page_size={page_size}&page={page - 1}">Previous</a>' if page > 1 else ""
    next_link = f'<a class="button secondary" href="/inbox?archived=1&page_size={page_size}&page={page + 1}">Next</a>' if page < pages else ""
    deep = '<p><a href="/inbox?archived=1&deep=1">Deep archive</a> shows history older than the most recent 500 reminders.</p>' if count > 500 and page == pages else ""
    options = "".join(
        f'<option value="{size}"{" selected" if size == page_size else ""}>{size}</option>'
        for size in (10, 50, 100)
    )
    return f'''<nav class="inbox-paging" aria-label="Archive pages"><form class="compact-form" method="get" action="/inbox"><input type="hidden" name="archived" value="1"><label><span>Items per page</span><select name="page_size">{options}</select></label><button class="button secondary">Apply</button></form><p>Page {page} of {pages}</p><div class="actions">{previous}{next_link}</div>{deep}</nav>'''


def _history(actions: list[InboxAction]) -> str:
    if not actions:
        return ""
    rows = "".join(
        f'<li>{escape(action.acted_at)} · {escape(action.action.replace("_", " "))} · {escape(action.resulting_state)}</li>'
        for action in actions
    )
    return f'<details class="inbox-history"><summary>Delivery history</summary><ul>{rows}</ul></details>'
