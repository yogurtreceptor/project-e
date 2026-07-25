"""Registered, database-backed local scheduling for Phase 2D operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
import threading
import uuid

from app.db_schema import connect
from app.db_support import utc_now
from app.reminder_service import evaluate_due_reminders, reactivate_next_open_snoozes


REMINDER_DELIVERY_JOB = "reminder-delivery"
_LEASE_SECONDS = 120


@dataclass(frozen=True)
class ScheduledJob:
    id: int
    name: str
    handler_name: str
    interval_seconds: int
    catch_up_policy: str
    enabled: bool
    next_run_at: str
    last_run_at: str
    status: str
    failure_reason: str


@dataclass(frozen=True)
class JobRun:
    id: int
    job_id: int
    scheduled_for: str
    trigger_kind: str
    started_at: str
    finished_at: str
    status: str
    details: str
    failure_reason: str


@dataclass(frozen=True)
class _Claim:
    job: ScheduledJob
    run_id: int
    lease_token: str


def ensure_registered_jobs(connection: sqlite3.Connection, *, now: datetime | None = None) -> None:
    """Register only application-owned job definitions; rows never contain code."""
    instant = _utc(now)
    timestamp = _stamp(instant)
    connection.execute(
        """INSERT INTO scheduled_jobs
            (name, handler_name, interval_seconds, catch_up_policy, next_run_at, created_at, updated_at)
            VALUES (?, ?, 60, 'coalesce', ?, ?, ?)
            ON CONFLICT(name) DO NOTHING""",
        (REMINDER_DELIVERY_JOB, REMINDER_DELIVERY_JOB, timestamp, timestamp, timestamp),
    )
    connection.commit()


def list_scheduled_jobs(connection: sqlite3.Connection) -> list[ScheduledJob]:
    rows = connection.execute("SELECT * FROM scheduled_jobs ORDER BY name, id").fetchall()
    return [_job(row) for row in rows]


def list_job_runs(connection: sqlite3.Connection, job_id: int, *, limit: int = 20) -> list[JobRun]:
    rows = connection.execute(
        "SELECT * FROM job_runs WHERE job_id=? ORDER BY started_at DESC, id DESC LIMIT ?",
        (job_id, max(1, min(limit, 100))),
    ).fetchall()
    return [JobRun(**dict(row)) for row in rows]


def set_job_enabled(connection: sqlite3.Connection, job_id: int, enabled: bool, *, now: datetime | None = None) -> bool:
    instant = _utc(now)
    row = connection.execute("SELECT id FROM scheduled_jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        return False
    connection.execute(
        """UPDATE scheduled_jobs SET enabled=?, status=?, lease_token='', lease_expires_at='',
            failure_reason='', next_run_at=CASE WHEN ? THEN ? ELSE next_run_at END, updated_at=? WHERE id=?""",
        (int(enabled), "idle" if enabled else "disabled", int(enabled), _stamp(instant), _stamp(instant), job_id),
    )
    connection.commit()
    return True


def run_due_jobs(connection: sqlite3.Connection, *, now: datetime | None = None, trigger_kind: str = "scheduled") -> int:
    """Run due registered work serially. A coalesced scan runs at most once per call."""
    instant = _utc(now)
    completed = 0
    while claim := _claim_due_job(connection, instant, trigger_kind):
        _execute_claim(connection, claim, instant)
        completed += 1
    return completed


def run_job_now(connection: sqlite3.Connection, job_id: int, *, now: datetime | None = None, rerun: bool = False) -> bool:
    """Create an auditable manual execution without changing the regular schedule."""
    instant = _utc(now)
    row = connection.execute("SELECT * FROM scheduled_jobs WHERE id=?", (job_id,)).fetchone()
    if row is None:
        return False
    job = _job(row)
    token = uuid.uuid4().hex
    scheduled_for = f"{_stamp(instant)}#{token}"
    cursor = connection.execute(
        """INSERT INTO job_runs(job_id, scheduled_for, trigger_kind, started_at, status)
            VALUES (?, ?, ?, ?, 'running')""",
        (job.id, scheduled_for, "rerun" if rerun else "manual", _stamp(instant)),
    )
    connection.commit()
    _execute_claim(connection, _Claim(job, int(cursor.lastrowid), token), instant, manual=True)
    return True


def recover_at_startup(connection: sqlite3.Connection, *, now: datetime | None = None) -> int:
    """Restore next-open attention, then serially coalesce overdue registered scans."""
    instant = _utc(now)
    ensure_registered_jobs(connection, now=instant)
    reactivate_next_open_snoozes(connection)
    completed = run_due_jobs(connection, now=instant, trigger_kind="startup_recovery")
    _set_checkpoint(connection, "startup", instant, f"completed_runs={completed}")
    return completed


def record_clean_shutdown(connection: sqlite3.Connection, *, now: datetime | None = None) -> None:
    _set_checkpoint(connection, "clean_shutdown", _utc(now), "application shutdown")


class SchedulerRuntime:
    """Small in-process boundary that is replaceable by a later local worker."""

    def __init__(self, database_path: Path | str, *, poll_seconds: float = 5.0):
        self.database_path = Path(database_path)
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with connect(self.database_path) as connection:
            recover_at_startup(connection)
        self._thread = threading.Thread(target=self._run, name="project-e-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.poll_seconds + 1)
        with connect(self.database_path) as connection:
            record_clean_shutdown(connection)

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                with connect(self.database_path) as connection:
                    run_due_jobs(connection)
            except sqlite3.Error:
                # The failed run is already durable when a handler raises; a transient
                # database-open failure is retried on the next in-process poll.
                continue


def _claim_due_job(connection: sqlite3.Connection, now: datetime, trigger_kind: str) -> _Claim | None:
    timestamp = _stamp(now)
    connection.execute("BEGIN IMMEDIATE")
    try:
        expired_jobs = connection.execute(
            "SELECT id, interval_seconds FROM scheduled_jobs WHERE status='running' AND lease_expires_at<>'' AND lease_expires_at<=?",
            (timestamp,),
        ).fetchall()
        connection.execute(
            """UPDATE job_runs SET status='expired', finished_at=?, failure_reason='lease expired'
                WHERE status='running' AND job_id IN
                (SELECT id FROM scheduled_jobs WHERE lease_expires_at<>'' AND lease_expires_at<=?)""",
            (timestamp, timestamp),
        )
        connection.executemany(
            """UPDATE scheduled_jobs SET next_run_at=?, status='idle', lease_token='', lease_expires_at='',
                failure_reason='lease expired', updated_at=? WHERE id=?""",
            [(_stamp(now + timedelta(seconds=int(row["interval_seconds"]))), timestamp, int(row["id"])) for row in expired_jobs],
        )
        row = connection.execute(
            """SELECT * FROM scheduled_jobs WHERE enabled=1 AND next_run_at<=?
                AND (lease_expires_at='' OR lease_expires_at<=?) ORDER BY next_run_at, id LIMIT 1""",
            (timestamp, timestamp),
        ).fetchone()
        if row is None:
            connection.commit()
            return None
        job = _job(row)
        token = uuid.uuid4().hex
        cursor = connection.execute(
            """INSERT INTO job_runs(job_id, scheduled_for, trigger_kind, started_at, status)
                VALUES (?, ?, ?, ?, 'running')""",
            (job.id, job.next_run_at, trigger_kind, timestamp),
        )
        connection.execute(
            """UPDATE scheduled_jobs SET status='running', lease_token=?, lease_expires_at=?, updated_at=? WHERE id=?""",
            (token, _stamp(now + timedelta(seconds=_LEASE_SECONDS)), timestamp, job.id),
        )
        connection.commit()
        return _Claim(job, int(cursor.lastrowid), token)
    except Exception:
        connection.rollback()
        raise


def _execute_claim(connection: sqlite3.Connection, claim: _Claim, now: datetime, *, manual: bool = False) -> None:
    timestamp = _stamp(now)
    try:
        details = _run_handler(connection, claim.job.handler_name, now)
    except Exception as exc:
        connection.execute(
            "UPDATE job_runs SET status='failed', finished_at=?, failure_reason=? WHERE id=?",
            (timestamp, str(exc), claim.run_id),
        )
        if not manual:
            _release_after_run(connection, claim.job, claim.lease_token, now, status="failed", failure_reason=str(exc))
        connection.commit()
        return
    connection.execute("UPDATE job_runs SET status='completed', finished_at=?, details=? WHERE id=?", (timestamp, details, claim.run_id))
    if not manual:
        _release_after_run(connection, claim.job, claim.lease_token, now, status="idle")
    connection.commit()


def _release_after_run(connection: sqlite3.Connection, job: ScheduledJob, token: str, now: datetime, *, status: str, failure_reason: str = "") -> None:
    next_run = _stamp(now + timedelta(seconds=job.interval_seconds))
    connection.execute(
        """UPDATE scheduled_jobs SET next_run_at=?, last_run_at=?, status=?, lease_token='', lease_expires_at='',
            failure_reason=?, updated_at=? WHERE id=? AND lease_token=?""",
        (next_run, _stamp(now), status, failure_reason, _stamp(now), job.id, token),
    )


def _run_handler(connection: sqlite3.Connection, handler_name: str, now: datetime) -> str:
    if handler_name == REMINDER_DELIVERY_JOB:
        return f"created_deliveries={evaluate_due_reminders(connection, now=now)}"
    raise ValueError(f"Unregistered scheduler handler: {handler_name}")


def _set_checkpoint(connection: sqlite3.Connection, key: str, now: datetime, details: str) -> None:
    connection.execute(
        """INSERT INTO scheduler_checkpoints(checkpoint_key, checkpoint_at, details) VALUES (?, ?, ?)
            ON CONFLICT(checkpoint_key) DO UPDATE SET checkpoint_at=excluded.checkpoint_at, details=excluded.details""",
        (key, _stamp(now), details),
    )
    connection.commit()


def _job(row: sqlite3.Row) -> ScheduledJob:
    values = dict(row)
    values["enabled"] = bool(values["enabled"])
    values.pop("lease_token", None)
    values.pop("lease_expires_at", None)
    values.pop("created_at", None)
    values.pop("updated_at", None)
    return ScheduledJob(**values)


def _utc(value: datetime | None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")
