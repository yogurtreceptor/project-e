"""Canonical Task and Task-list persistence and lifecycle services."""

from dataclasses import dataclass
import sqlite3

from app.audit import record_audit_event, set_provenance
from app.db_support import utc_now


@dataclass(frozen=True)
class TaskListInput:
    name: str


@dataclass(frozen=True)
class TaskListRecord:
    id: int
    name: str
    is_default: bool
    archived_at: str

    @property
    def is_archived(self) -> bool:
        return bool(self.archived_at)


@dataclass(frozen=True)
class TaskInput:
    title: str
    task_list_id: int | None = None
    notes: str = ""


@dataclass(frozen=True)
class TaskRecord:
    id: int
    title: str
    notes: str
    task_list_id: int
    status: str
    completed_at: str
    archived_at: str
    deleted_at: str
    created_at: str
    updated_at: str

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_archived(self) -> bool:
        return bool(self.archived_at)


def list_task_lists(connection: sqlite3.Connection, *, include_archived: bool = False) -> list[TaskListRecord]:
    clause = "" if include_archived else "WHERE archived_at = ''"
    rows = connection.execute(
        f"SELECT * FROM task_lists {clause} ORDER BY lower(name), id"
    ).fetchall()
    return [_to_task_list(row) for row in rows]


def get_task_list(connection: sqlite3.Connection, task_list_id: int, *, include_archived: bool = False) -> TaskListRecord | None:
    clause = "" if include_archived else "AND archived_at = ''"
    row = connection.execute(
        f"SELECT * FROM task_lists WHERE id = ? {clause}", (task_list_id,)
    ).fetchone()
    return _to_task_list(row) if row is not None else None


def create_task_list(connection: sqlite3.Connection, values: TaskListInput) -> int:
    name = _required_name(values.name, "Task list name")
    now = utc_now()
    try:
        cursor = connection.execute(
            "INSERT INTO task_lists (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name, now, now),
        )
        task_list_id = int(cursor.lastrowid)
        record_audit_event(connection, "create", [("task_list", task_list_id)], after={"name": name}, notes="Task list created")
        set_provenance(connection, "task_list", task_list_id, "name", "manual")
        connection.commit()
        return task_list_id
    except Exception:
        connection.rollback()
        raise


def rename_task_list(connection: sqlite3.Connection, task_list_id: int, name: str) -> bool:
    current = _require_task_list(connection, task_list_id, include_archived=True)
    name = _required_name(name, "Task list name")
    if current.name == name:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE task_lists SET name = ?, updated_at = ? WHERE id = ?", (name, now, task_list_id))
        record_audit_event(connection, "edit", [("task_list", task_list_id)], before={"name": current.name}, after={"name": name}, notes="Task list renamed")
        set_provenance(connection, "task_list", task_list_id, "name", "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def archive_task_list(connection: sqlite3.Connection, task_list_id: int) -> bool:
    current = _require_task_list(connection, task_list_id)
    if current.is_default:
        raise ValueError("Select another active Task list as default before archiving this Task list.")
    now = utc_now()
    try:
        connection.execute("UPDATE task_lists SET archived_at = ?, updated_at = ? WHERE id = ?", (now, now, task_list_id))
        record_audit_event(connection, "archive", [("task_list", task_list_id)], before={"archived_at": ""}, after={"archived_at": now}, notes="Task list archived; assigned Tasks were retained")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def unarchive_task_list(connection: sqlite3.Connection, task_list_id: int) -> bool:
    current = _require_task_list(connection, task_list_id, include_archived=True)
    if not current.is_archived:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE task_lists SET archived_at = '', updated_at = ? WHERE id = ?", (now, task_list_id))
        record_audit_event(connection, "unarchive", [("task_list", task_list_id)], before={"archived_at": current.archived_at}, after={"archived_at": ""}, notes="Task list unarchived")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def set_default_task_list(connection: sqlite3.Connection, task_list_id: int) -> bool:
    current = _require_task_list(connection, task_list_id)
    if current.is_default:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE task_lists SET is_default = 0 WHERE is_default = 1")
        connection.execute("UPDATE task_lists SET is_default = 1, updated_at = ? WHERE id = ?", (now, task_list_id))
        record_audit_event(connection, "edit", [("task_list", task_list_id)], after={"is_default": True}, notes="Task list selected as default")
        set_provenance(connection, "task_list", task_list_id, "is_default", "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def create_task(connection: sqlite3.Connection, task: TaskInput) -> int:
    values = _normalise_task(connection, task)
    now = utc_now()
    try:
        cursor = connection.execute("INSERT INTO entities (type, display_name, summary, notes, created_at, updated_at) VALUES ('task', ?, '', ?, ?, ?)", (values["title"], values["notes"], now, now))
        task_id = int(cursor.lastrowid)
        connection.execute("INSERT INTO tasks (entity_id, task_list_id) VALUES (?, ?)", (task_id, values["task_list_id"]))
        record_audit_event(connection, "create", [("entity", task_id)], after=values, notes="Task created")
        for field_name, value in values.items():
            if value not in ("", None):
                set_provenance(connection, "entity", task_id, field_name, "manual")
        connection.commit()
        return task_id
    except Exception:
        connection.rollback()
        raise


def update_task(connection: sqlite3.Connection, task_id: int, task: TaskInput) -> bool:
    current = _require_task(connection, task_id, include_archived=True)
    values = _normalise_task(connection, task, current.task_list_id)
    before = _task_snapshot(current)
    after = {**before, **values}
    if before == after:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE entities SET display_name = ?, notes = ?, updated_at = ? WHERE id = ? AND deleted_at = ''", (values["title"], values["notes"], now, task_id))
        connection.execute("UPDATE tasks SET task_list_id = ? WHERE entity_id = ?", (values["task_list_id"], task_id))
        record_audit_event(connection, "edit", [("entity", task_id)], before=before, after=after, notes="Task edited")
        for key, value in values.items():
            if before.get(key) != value:
                set_provenance(connection, "entity", task_id, key, "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def complete_task(connection: sqlite3.Connection, task_id: int) -> bool:
    return _change_status(connection, task_id, "open", "completed", "complete", "Task completed")


def reopen_task(connection: sqlite3.Connection, task_id: int) -> bool:
    return _change_status(connection, task_id, "completed", "open", "reopen", "Task reopened")


def archive_task(connection: sqlite3.Connection, task_id: int) -> bool:
    current = _require_task(connection, task_id, include_archived=True)
    if current.is_archived:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE tasks SET archived_at = ? WHERE entity_id = ?", (now, task_id))
        connection.execute("UPDATE entities SET updated_at = ? WHERE id = ?", (now, task_id))
        record_audit_event(connection, "archive", [("entity", task_id)], before={"archived_at": ""}, after={"archived_at": now}, notes="Task archived")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def unarchive_task(connection: sqlite3.Connection, task_id: int) -> bool:
    current = _require_task(connection, task_id, include_archived=True)
    if not current.is_archived:
        return False
    now = utc_now()
    try:
        connection.execute("UPDATE tasks SET archived_at = '' WHERE entity_id = ?", (task_id,))
        connection.execute("UPDATE entities SET updated_at = ? WHERE id = ?", (now, task_id))
        record_audit_event(connection, "unarchive", [("entity", task_id)], before={"archived_at": current.archived_at}, after={"archived_at": ""}, notes="Task unarchived")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def get_task(connection: sqlite3.Connection, task_id: int, *, include_archived: bool = False) -> TaskRecord | None:
    archived = "" if include_archived else "AND task.archived_at = ''"
    row = connection.execute(f"SELECT entity.*, task.* FROM entities AS entity JOIN tasks AS task ON task.entity_id = entity.id WHERE entity.id = ? AND entity.type = 'task' AND entity.deleted_at = '' {archived}", (task_id,)).fetchone()
    return _to_task(row) if row is not None else None


def list_tasks(connection: sqlite3.Connection, *, include_completed: bool = False, include_archived: bool = False) -> list[TaskRecord]:
    completed = "" if include_completed else "AND task.status = 'open'"
    archived = "" if include_archived else "AND task.archived_at = ''"
    rows = connection.execute(f"SELECT entity.*, task.* FROM entities AS entity JOIN tasks AS task ON task.entity_id = entity.id WHERE entity.type = 'task' AND entity.deleted_at = '' {completed} {archived} ORDER BY lower(entity.display_name), entity.id").fetchall()
    return [_to_task(row) for row in rows]


def validate_stored_task(connection: sqlite3.Connection, task_id: int) -> list[str]:
    row = connection.execute("SELECT entity.display_name, task.* FROM tasks AS task JOIN entities AS entity ON entity.id = task.entity_id WHERE task.entity_id = ? AND entity.type = 'task'", (task_id,)).fetchone()
    if row is None:
        return ["Task typed record is missing."]
    errors: list[str] = []
    if not row["display_name"].strip():
        errors.append("Task title is required.")
    if row["status"] not in ("open", "completed"):
        errors.append("Task status is invalid.")
    if row["status"] == "completed" and not row["completed_at"]:
        errors.append("Completed Task has no completion timestamp.")
    if row["status"] == "open" and row["completed_at"]:
        errors.append("Open Task has a completion timestamp.")
    if connection.execute("SELECT 1 FROM task_lists WHERE id = ?", (row["task_list_id"],)).fetchone() is None:
        errors.append("Task list reference is invalid.")
    return errors


def _change_status(connection: sqlite3.Connection, task_id: int, expected: str, replacement: str, action: str, note: str) -> bool:
    current = _require_task(connection, task_id, include_archived=True)
    if current.status == replacement:
        return False
    if current.status != expected:
        raise ValueError(f"Task cannot be changed from {current.status}.")
    now = utc_now()
    completed_at = now if replacement == "completed" else ""
    try:
        connection.execute("UPDATE tasks SET status = ?, completed_at = ? WHERE entity_id = ?", (replacement, completed_at, task_id))
        connection.execute("UPDATE entities SET updated_at = ? WHERE id = ?", (now, task_id))
        record_audit_event(connection, action, [("entity", task_id)], before={"status": expected, "completed_at": current.completed_at}, after={"status": replacement, "completed_at": completed_at}, notes=note)
        set_provenance(connection, "entity", task_id, "status", "manual")
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def _normalise_task(connection: sqlite3.Connection, task: TaskInput, current_list_id: int | None = None) -> dict[str, object]:
    title = _required_name(task.title, "Task title")
    list_id = task.task_list_id if task.task_list_id is not None else current_list_id
    if list_id is None:
        row = connection.execute("SELECT id FROM task_lists WHERE is_default = 1 AND archived_at = ''").fetchone()
    else:
        row = connection.execute("SELECT id, archived_at FROM task_lists WHERE id = ?", (list_id,)).fetchone()
        if row is not None and row["archived_at"] and int(row["id"]) != current_list_id:
            raise ValueError("Archived Task list cannot be selected.")
    if row is None:
        raise ValueError("Task list does not exist or no active default Task list is configured.")
    return {"title": title, "notes": task.notes.strip(), "task_list_id": int(row["id"])}


def _required_name(value: str, label: str) -> str:
    result = value.strip()
    if not result:
        raise ValueError(f"{label} is required.")
    return result


def _require_task_list(connection: sqlite3.Connection, task_list_id: int, *, include_archived: bool = False) -> TaskListRecord:
    record = get_task_list(connection, task_list_id, include_archived=include_archived)
    if record is None:
        raise ValueError("Task list does not exist.")
    return record


def _require_task(connection: sqlite3.Connection, task_id: int, *, include_archived: bool = False) -> TaskRecord:
    record = get_task(connection, task_id, include_archived=include_archived)
    if record is None:
        raise ValueError("Task does not exist.")
    return record


def _to_task_list(row: sqlite3.Row) -> TaskListRecord:
    return TaskListRecord(int(row["id"]), row["name"], bool(row["is_default"]), row["archived_at"])


def _to_task(row: sqlite3.Row) -> TaskRecord:
    return TaskRecord(int(row["id"]), row["display_name"], row["notes"], int(row["task_list_id"]), row["status"], row["completed_at"], row["archived_at"], row["deleted_at"], row["created_at"], row["updated_at"])


def _task_snapshot(task: TaskRecord) -> dict[str, object]:
    return {"title": task.title, "notes": task.notes, "task_list_id": task.task_list_id, "status": task.status, "completed_at": task.completed_at, "archived_at": task.archived_at}
