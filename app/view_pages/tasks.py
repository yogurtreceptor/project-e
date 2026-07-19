"""Dedicated Task capture and organisation pages."""

from html import escape

from app.task_service import TaskListRecord, TaskRecord
from app.view_pages.forms import error_block


def task_form_page(task_lists: list[TaskListRecord], values: dict[str, str], *, errors: list[str] | None = None) -> str:
    options = "".join(
        f'<option value="{item.id}"{" selected" if values.get("task_list_id") == str(item.id) else ""}>{escape(item.name)}</option>'
        for item in task_lists if not item.is_archived
    )
    return f'''<section class="page-heading"><p class="eyebrow">Calendar</p><h1>Add Task</h1><p>Create work with no required date or session. Scheduling follows in the next Task milestone.</p></section><section class="panel"><form class="record-form" method="post" action="/calendar/tasks/new" data-dirty-form>{error_block(errors or [])}<label><span>Title</span><input name="title" required value="{escape(values.get("title", ""))}"></label><label><span>Task list</span><select name="task_list_id">{options}</select></label><label><span>Notes <em>(optional)</em></span><textarea name="notes" rows="4">{escape(values.get("notes", ""))}</textarea></label><div class="actions"><a class="button secondary" href="/calendar">Cancel</a><button class="button" type="submit">Add Task</button></div></form></section>'''


def tasks_page(tasks: list[TaskRecord], task_lists: list[TaskListRecord], *, show_completed: bool, show_archived: bool, errors: list[str] | None = None) -> str:
    list_by_id = {item.id: item for item in task_lists}
    rows = "".join(_task_row(task, list_by_id.get(task.task_list_id), task_lists) for task in tasks)
    filters = f'<a class="button secondary" href="/tasks?completed={"0" if show_completed else "1"}&archived={"1" if show_archived else "0"}">{"Hide" if show_completed else "Show"} completed</a><a class="button secondary" href="/tasks?completed={"1" if show_completed else "0"}&archived={"0" if show_archived else "1"}">{"Hide" if show_archived else "Show"} archived</a>'
    list_rows = "".join(_list_row(item) for item in task_lists)
    return f'''<section class="page-heading split"><div><p class="eyebrow">Work management</p><h1>Tasks</h1><p>Organise and complete canonical work. Create new Tasks from the Calendar.</p></div><div class="actions">{filters}<a class="button" href="/calendar/tasks/new">Add Task</a></div></section>{error_block(errors or [])}<section class="panel"><h2>{"Tasks including completed" if show_completed else "Open Tasks"}</h2><div class="task-list">{rows or '<p class="empty">No Tasks in this view.</p>'}</div></section><section class="panel"><h2>Task lists</h2><div class="task-list">{list_rows}</div><form class="record-form compact-form" method="post" action="/tasks/lists"><label><span>New Task list</span><input name="name" required></label><button class="button" type="submit">Add list</button></form></section>'''


def _task_row(task: TaskRecord, task_list: TaskListRecord | None, task_lists: list[TaskListRecord]) -> str:
    state = "Completed" if task.is_completed else "Open"
    if task.is_archived:
        state += " · Archived"
    task_list_name = task_list.name if task_list else "Unavailable list"
    action = "reopen" if task.is_completed else "complete"
    action_label = "Reopen" if task.is_completed else "Complete"
    archive_action = "unarchive" if task.is_archived else "archive"
    archive_label = "Unarchive" if task.is_archived else "Archive"
    options = "".join(f'<option value="{item.id}"{" selected" if item.id == task.task_list_id else ""}>{escape(item.name)}</option>' for item in task_lists if not item.is_archived)
    return f'''<article class="task-row"><div><h3><a href="/tasks/{task.id}">{escape(task.title)}</a></h3><p>{escape(task_list_name)} · {state}</p>{f'<p>{escape(task.notes)}</p>' if task.notes else ''}</div><div class="actions"><form method="post" action="/tasks/{task.id}/move"><label><span class="visually-hidden">Task list</span><select name="task_list_id">{options}</select></label><button class="button secondary" type="submit">Move</button></form><form method="post" action="/tasks/{task.id}/{action}"><button class="button secondary" type="submit">{action_label}</button></form><form method="post" action="/tasks/{task.id}/{archive_action}"><button class="button secondary" type="submit">{archive_label}</button></form><a class="button secondary" href="/relationships/new?context_entity_id={task.id}">Relationships</a></div></article>'''


def _list_row(task_list: TaskListRecord) -> str:
    state = "Default" if task_list.is_default else "Archived" if task_list.is_archived else "Active"
    action = "unarchive" if task_list.is_archived else "archive"
    label = "Unarchive" if task_list.is_archived else "Archive"
    default = "" if task_list.is_default or task_list.is_archived else f'<form method="post" action="/tasks/lists/{task_list.id}/default"><button class="button secondary" type="submit">Make default</button></form>'
    return f'''<article class="task-row"><div><h3>{escape(task_list.name)}</h3><p>{state}</p></div><div class="actions"><form method="post" action="/tasks/lists/{task_list.id}/rename"><label><span class="visually-hidden">Task list name</span><input name="name" value="{escape(task_list.name)}" required></label><button class="button secondary" type="submit">Rename</button></form>{default}<form method="post" action="/tasks/lists/{task_list.id}/{action}"><button class="button secondary" type="submit">{label}</button></form></div></article>'''


def task_projection_page(task: TaskRecord, task_list: TaskListRecord | None, relationships: list, history: list, audit_events: list) -> str:
    from app.view_pages.entities import audit_history_section
    list_name = task_list.name if task_list else "Unavailable list"
    related = "".join(f'<li><a href="/{relationship.other_entity(task.id).slug}/{relationship.other_entity(task.id).id}">{escape(relationship.other_entity(task.id).title)}</a></li>' for relationship in relationships)
    return f'''<article class="entity-profile"><nav class="breadcrumbs" aria-label="Breadcrumb"><ol><li><a href="/tasks">Tasks</a></li><li aria-current="page">{escape(task.title)}</li></ol></nav><section class="entity-hero panel"><div class="entity-identity"><p class="eyebrow">Task</p><h1>{escape(task.title)}</h1></div><div class="actions"><a class="button secondary" href="/relationships/new?context_entity_id={task.id}">Add relationship</a></div></section><div class="profile-grid"><div class="profile-main"><section class="panel profile-section"><h2>Task details</h2><dl><dt>List</dt><dd>{escape(list_name)}</dd><dt>Status</dt><dd>{escape(task.status.title())}</dd>{f'<dt>Completed</dt><dd>{escape(task.completed_at)}</dd>' if task.completed_at else ''}</dl></section><section class="panel profile-section"><h2>Relationships</h2>{f'<ul class="entity-link-list">{related}</ul>' if related else '<p class="empty">No relationships yet.</p>'}</section><section class="panel profile-section"><h2>Notes</h2><p class="notes">{escape(task.notes) if task.notes else 'No notes yet.'}</p></section></div><aside class="profile-side">{audit_history_section(history, audit_events)}</aside></div></article>'''
