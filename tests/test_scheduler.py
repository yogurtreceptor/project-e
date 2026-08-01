import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.db import connect, initialise_database
from app.event_service import EventInput, create_event
from app.scheduler_service import (
    ensure_registered_jobs, list_job_runs, list_scheduled_jobs, recover_at_startup,
    run_due_jobs, run_job_now, set_job_enabled,
)


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "scheduler.sqlite3"
        initialise_database(self.path)
        self.connection = connect(self.path)

    def tearDown(self) -> None:
        self.connection.close()
        self.directory.cleanup()

    def test_registered_reminder_job_runs_once_and_records_history(self) -> None:
        now = datetime(2025, 12, 31, 23, 55, tzinfo=UTC)
        create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))
        ensure_registered_jobs(self.connection, now=now)

        self.assertEqual(1, run_due_jobs(self.connection, now=now))
        self.assertEqual(0, run_due_jobs(self.connection, now=now))
        job = list_scheduled_jobs(self.connection)[0]
        runs = list_job_runs(self.connection, job.id)
        self.assertEqual(["completed"], [run.status for run in runs])
        self.assertEqual("scheduled", runs[0].trigger_kind)
        self.assertIn("created_deliveries=1", runs[0].details)
        self.assertIn("calendar_subscription_checks=0", runs[0].details)

    def test_startup_recovery_coalesces_delivery_and_records_checkpoint(self) -> None:
        now = datetime(2025, 12, 31, 23, 55, tzinfo=UTC)
        create_event(self.connection, EventInput("Planning", False,
            start_local="2026-01-01T10:00", end_local="2026-01-01T11:00"))

        self.assertEqual(1, recover_at_startup(self.connection, now=now))
        job = list_scheduled_jobs(self.connection)[0]
        self.assertEqual("startup_recovery", list_job_runs(self.connection, job.id)[0].trigger_kind)
        checkpoint = self.connection.execute("SELECT details FROM scheduler_checkpoints WHERE checkpoint_key='startup'").fetchone()
        self.assertEqual("completed_runs=1", checkpoint["details"])

    def test_manual_run_is_auditable_without_moving_regular_schedule(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        ensure_registered_jobs(self.connection, now=now)
        job = list_scheduled_jobs(self.connection)[0]
        next_run = job.next_run_at

        self.assertTrue(run_job_now(self.connection, job.id, now=now))
        self.assertEqual(next_run, list_scheduled_jobs(self.connection)[0].next_run_at)
        self.assertEqual("manual", list_job_runs(self.connection, job.id)[0].trigger_kind)

    def test_disabled_job_does_not_run_until_reenabled(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        ensure_registered_jobs(self.connection, now=now)
        job = list_scheduled_jobs(self.connection)[0]
        self.assertTrue(set_job_enabled(self.connection, job.id, False, now=now))
        self.assertEqual(0, run_due_jobs(self.connection, now=now + timedelta(minutes=2)))
        self.assertTrue(set_job_enabled(self.connection, job.id, True, now=now))
        self.assertEqual(1, run_due_jobs(self.connection, now=now))

    def test_expired_lease_is_retained_for_manual_rerun_without_duplicate_schedule(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=UTC)
        ensure_registered_jobs(self.connection, now=now)
        job = list_scheduled_jobs(self.connection)[0]
        self.connection.execute(
            "UPDATE scheduled_jobs SET status='running', lease_token='old', lease_expires_at=? WHERE id=?",
            ((now - timedelta(seconds=1)).isoformat(timespec="seconds"), job.id),
        )
        self.connection.execute(
            "INSERT INTO job_runs(job_id, scheduled_for, trigger_kind, started_at, status) VALUES (?, ?, 'scheduled', ?, 'running')",
            (job.id, job.next_run_at, job.next_run_at),
        )
        self.connection.commit()

        self.assertEqual(0, run_due_jobs(self.connection, now=now))
        self.assertEqual("expired", list_job_runs(self.connection, job.id)[0].status)
        self.assertGreater(list_scheduled_jobs(self.connection)[0].next_run_at, job.next_run_at)
