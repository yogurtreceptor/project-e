"""Registered deterministic automation with explicit approval boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import sqlite3

from app.audit import record_audit_event
from app.db_support import utc_now
from app.reminder_service import evaluate_due_reminders


REMINDER_SCAN_TRIGGER = "reminder_scan"
DELIVER_DUE_REMINDERS = "deliver_due_reminders"

_BUILT_INS = (
    ("deliver-due-reminders", "Deliver due reminders", REMINDER_SCAN_TRIGGER, DELIVER_DUE_REMINDERS, True),
)


@dataclass(frozen=True)
class AutomationRule:
    id: int; rule_key: str; name: str; trigger_name: str; action_name: str
    conditions_json: str; enabled: bool; created_at: str; updated_at: str


@dataclass(frozen=True)
class AutomationRun:
    id: int; rule_id: int; trigger_key: str; trigger_name: str; source_kind: str
    source_id: int; input_json: str; outcome_json: str; status: str; failure_reason: str; occurred_at: str


def ensure_registered_rules(connection: sqlite3.Connection) -> None:
    now = utc_now()
    for rule_key, name, trigger, action, enabled in _BUILT_INS:
        connection.execute(
            """INSERT INTO automation_rules
               (rule_key, name, trigger_name, action_name, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(rule_key) DO NOTHING""",
            (rule_key, name, trigger, action, int(enabled), now, now),
        )
    connection.commit()


def list_rules(connection: sqlite3.Connection) -> list[AutomationRule]:
    ensure_registered_rules(connection)
    return [_rule(row) for row in connection.execute("SELECT * FROM automation_rules ORDER BY id")]


def list_runs(connection: sqlite3.Connection, rule_id: int, *, limit: int = 20) -> list[AutomationRun]:
    rows = connection.execute("SELECT * FROM automation_runs WHERE rule_id=? ORDER BY occurred_at DESC, id DESC LIMIT ?", (rule_id, max(1, min(limit, 100)))).fetchall()
    return [AutomationRun(**dict(row)) for row in rows]


def set_rule_enabled(connection: sqlite3.Connection, rule_id: int, enabled: bool) -> bool:
    ensure_registered_rules(connection)
    cursor = connection.execute("UPDATE automation_rules SET enabled=?, updated_at=? WHERE id=?", (int(enabled), utc_now(), rule_id))
    if cursor.rowcount:
        record_audit_event(connection, "automation", [("automation_rule", rule_id)], after={"enabled": enabled}, notes="Automation rule enabled" if enabled else "Automation rule disabled", provenance="automation")
    connection.commit()
    return bool(cursor.rowcount)


def dispatch(connection: sqlite3.Connection, trigger_name: str, trigger_key: str, *, now: datetime | None = None) -> int:
    """Run each enabled registered action once for a logical trigger identity."""
    if trigger_name != REMINDER_SCAN_TRIGGER:
        raise ValueError("Unregistered automation trigger.")
    ensure_registered_rules(connection)
    instant = (now or datetime.now(UTC)).astimezone(UTC)
    completed = 0
    for rule in list_rules(connection):
        if not rule.enabled or rule.trigger_name != trigger_name:
            continue
        existing = connection.execute("SELECT id FROM automation_runs WHERE rule_id=? AND trigger_key=?", (rule.id, trigger_key)).fetchone()
        if existing is not None:
            continue
        try:
            outcome = _run_action(connection, rule, trigger_key, instant)
            status, failure = "completed", ""
            completed += 1
        except Exception as exc:
            outcome, status, failure = {}, "failed", str(exc)
        cursor = connection.execute(
            """INSERT INTO automation_runs
               (rule_id, trigger_key, trigger_name, input_json, outcome_json, status, failure_reason, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (rule.id, trigger_key, trigger_name, json.dumps({"at": instant.isoformat(timespec="seconds")}, sort_keys=True), json.dumps(outcome, sort_keys=True), status, failure, utc_now()),
        )
        record_audit_event(connection, "automation", [("automation_rule", rule.id), ("automation_run", int(cursor.lastrowid))], after={"trigger": trigger_name, "outcome": outcome, "status": status}, notes=f"Automation rule executed: {rule.rule_key}", provenance="automation")
        connection.commit()
    return completed


def _run_action(connection: sqlite3.Connection, rule: AutomationRule, trigger_key: str, now: datetime) -> dict[str, object]:
    if rule.action_name == DELIVER_DUE_REMINDERS:
        return {"created_deliveries": evaluate_due_reminders(connection, now=now)}
    raise ValueError("Unregistered automation action.")


def _rule(row: sqlite3.Row) -> AutomationRule:
    values = dict(row); values["enabled"] = bool(values["enabled"]); return AutomationRule(**values)
