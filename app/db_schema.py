import sqlite3
from pathlib import Path

from app.db_support import allowed_entity_type_sql, sql_identifier, sql_literal, utc_now
from app.entities import ALL_ENTITY_DEFINITIONS, ENTITY_DEFINITIONS, EntityDefinition
from app.reference_data import create_reference_data_tables
from app.units import create_unit_tables


def connect(database_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database(database_path: Path | str) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        create_schema(connection)


def create_schema(connection: sqlite3.Connection) -> None:
    create_schema_migration_table(connection)
    apply_schema_migrations(connection)
    ensure_current_schema(connection)


def create_schema_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )


def apply_schema_migrations(connection: sqlite3.Connection) -> None:
    applied = {
        row["migration_id"]
        for row in connection.execute("SELECT migration_id FROM schema_migrations")
    }
    for migration_id, migration in SCHEMA_MIGRATIONS:
        if migration_id in applied:
            continue
        migration(connection)
        connection.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (migration_id, utc_now()),
        )


def ensure_current_schema(connection: sqlite3.Connection) -> None:
    create_entity_table(connection)
    ensure_entity_columns(connection)
    ensure_entity_type_constraint(connection)
    create_typed_entity_tables(connection)
    create_relationship_table(connection)
    create_inference_tables(connection)
    create_entity_history_table(connection)
    create_platform_tables(connection)
    create_journal_table(connection)
    create_entity_alias_table(connection)
    create_calendar_table(connection)
    create_birthday_event_links_table(connection)
    create_calendar_history_table(connection)
    create_event_table(connection)
    create_event_recurrence_tables(connection)
    create_calendar_interchange_tables(connection)
    create_task_list_table(connection)
    create_task_table(connection)
    create_task_temporal_tables(connection)
    create_reminder_tables(connection)
    expand_reminder_policy_contexts_for_external_calendars(connection)
    create_scheduler_tables(connection)
    create_automation_tables(connection)
    create_reference_data_tables(connection)
    create_unit_tables(connection)
    from app.taxonomy import create_taxonomy_tables, load_relationship_catalog
    create_taxonomy_tables(connection)
    load_relationship_catalog(connection)


def create_initial_temporal_foundation_tables(
    connection: sqlite3.Connection,
) -> None:
    """Historical Phase 2A schema retained for migration compatibility."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS calendars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            colour TEXT NOT NULL,
            timezone TEXT NOT NULL,
            default_event_duration_minutes INTEGER NOT NULL
                CHECK (default_event_duration_minutes > 0),
            is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT '',
            UNIQUE (name)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_calendars_one_default
            ON calendars (is_default) WHERE is_default = 1;
        CREATE INDEX IF NOT EXISTS idx_calendars_active_order
            ON calendars (archived_at, lower(name), id);

        CREATE TABLE IF NOT EXISTS event_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            colour TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT '',
            UNIQUE (name)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_event_categories_one_default
            ON event_categories (is_default) WHERE is_default = 1;
        CREATE INDEX IF NOT EXISTS idx_event_categories_active_order
            ON event_categories (archived_at, sort_order, lower(name), id);
        """
    )
    now = utc_now()
    if connection.execute("SELECT 1 FROM calendars LIMIT 1").fetchone() is None:
        connection.execute(
            """
            INSERT INTO calendars (
                name, colour, timezone, default_event_duration_minutes,
                is_default, created_at, updated_at
            ) VALUES ('Calendar', '#2563EB', 'Australia/Brisbane', 60, 1, ?, ?)
            """,
            (now, now),
        )
    if connection.execute("SELECT 1 FROM event_categories LIMIT 1").fetchone() is None:
        connection.execute(
            """
            INSERT INTO event_categories (
                name, colour, sort_order, is_default, created_at, updated_at
            ) VALUES ('General', '#2563EB', 0, 1, ?, ?)
            """,
            (now, now),
        )


def create_initial_event_table(connection: sqlite3.Connection) -> None:
    """Historical category-bearing Event schema retained for migration 17."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            entity_id INTEGER PRIMARY KEY
                REFERENCES entities(id) ON DELETE CASCADE,
            calendar_id INTEGER NOT NULL
                REFERENCES calendars(id) ON DELETE RESTRICT,
            category_id INTEGER NOT NULL
                REFERENCES event_categories(id) ON DELETE RESTRICT,
            is_all_day INTEGER NOT NULL CHECK (is_all_day IN (0, 1)),
            start_utc TEXT NOT NULL DEFAULT '',
            end_utc TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date_exclusive TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            date_precision TEXT NOT NULL DEFAULT 'exact'
                CHECK (date_precision IN ('exact', 'approximate')),
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'cancelled')),
            archived_at TEXT NOT NULL DEFAULT '',
            CHECK (
                (
                    is_all_day = 0
                    AND start_utc <> '' AND end_utc <> '' AND start_utc < end_utc
                    AND start_date = '' AND end_date_exclusive = ''
                    AND timezone <> ''
                )
                OR
                (
                    is_all_day = 1
                    AND start_date <> '' AND end_date_exclusive <> ''
                    AND start_date < end_date_exclusive
                    AND start_utc = '' AND end_utc = '' AND timezone = ''
                )
            )
        );
        CREATE INDEX IF NOT EXISTS idx_events_active_time
            ON events (archived_at, is_all_day, start_utc, start_date, entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_calendar
            ON events (calendar_id, archived_at, entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_category
            ON events (category_id, archived_at, entity_id);
        """
    )


def create_calendar_table(connection: sqlite3.Connection) -> None:
    """Create the corrected Calendar-only Event grouping model."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS calendars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            colour TEXT NOT NULL,
            timezone TEXT NOT NULL,
            default_event_duration_minutes INTEGER NOT NULL
                CHECK (default_event_duration_minutes > 0),
            sort_order INTEGER NOT NULL DEFAULT 0,
            kind TEXT NOT NULL DEFAULT 'event' CHECK (kind IN ('event', 'birthday')),
            is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT '',
            UNIQUE (name)
        );
        CREATE INDEX IF NOT EXISTS idx_calendars_active_order
            ON calendars (archived_at, sort_order, lower(name), id);
        """
    )
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(calendars)")
    }
    if "sort_order" not in columns:
        connection.execute(
            "ALTER TABLE calendars ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
        )
    if "kind" not in columns:
        connection.execute("ALTER TABLE calendars ADD COLUMN kind TEXT NOT NULL DEFAULT 'event'")
    connection.execute("DROP INDEX IF EXISTS idx_calendars_one_default")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_calendars_one_default_per_kind ON calendars (kind) WHERE is_default = 1")
    connection.execute("DROP INDEX IF EXISTS idx_calendars_active_order")
    connection.execute(
        """
        CREATE INDEX idx_calendars_active_order
        ON calendars (archived_at, sort_order, lower(name), id)
        """
    )
    now = utc_now()
    if connection.execute("SELECT 1 FROM calendars LIMIT 1").fetchone() is None:
        connection.execute(
            """
            INSERT INTO calendars (
                name, colour, timezone, default_event_duration_minutes,
                sort_order, kind, is_default, created_at, updated_at
            ) VALUES (
                'General', '#2563EB', 'Australia/Brisbane', 60, 0, 'event', 1, ?, ?
            )
            """,
            (now, now),
        )
    if connection.execute("SELECT 1 FROM calendars WHERE kind = 'birthday'").fetchone() is None:
        connection.execute("INSERT INTO calendars (name, colour, timezone, default_event_duration_minutes, sort_order, kind, is_default, created_at, updated_at) VALUES ('Birthdays', '#DB2777', 'Australia/Brisbane', 1440, 1, 'birthday', 1, ?, ?)", (now, now))


def create_calendar_history_table(connection: sqlite3.Connection) -> None:
    """Create append-only management history for local Calendar records."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS calendar_edit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendar_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_edit_history_calendar
            ON calendar_edit_history (calendar_id, created_at, id);
        """
    )


def create_birthday_event_links_table(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS birthday_event_links (person_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE, event_id INTEGER NOT NULL UNIQUE REFERENCES entities(id) ON DELETE CASCADE)")


def migrate_birthday_reminder_policy(connection: sqlite3.Connection) -> None:
    """Move the former derived-birthday default into the Birthdays calendar."""
    birthday_calendar = connection.execute(
        "SELECT id FROM calendars WHERE kind = 'birthday'"
    ).fetchone()
    if birthday_calendar is None:
        return
    legacy = connection.execute(
        """SELECT timings_json FROM reminder_policies
           WHERE context_kind = 'global' AND context_id = 0 AND source_kind = 'birthday'"""
    ).fetchone()
    if legacy is None:
        return
    connection.execute(
        """INSERT INTO reminder_policies (
               context_kind, context_id, source_kind, timings_json, updated_at
           ) VALUES ('calendar', ?, 'event', ?, ?)
           ON CONFLICT(context_kind, context_id, source_kind) DO NOTHING""",
        (int(birthday_calendar["id"]), legacy["timings_json"], utc_now()),
    )
    connection.execute(
        """DELETE FROM reminder_policies
           WHERE context_kind = 'global' AND context_id = 0 AND source_kind = 'birthday'"""
    )


def create_event_table(connection: sqlite3.Connection) -> None:
    """Create canonical planned-time Event storage without categories."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            entity_id INTEGER PRIMARY KEY
                REFERENCES entities(id) ON DELETE CASCADE,
            calendar_id INTEGER NOT NULL
                REFERENCES calendars(id) ON DELETE RESTRICT,
            is_all_day INTEGER NOT NULL CHECK (is_all_day IN (0, 1)),
            start_utc TEXT NOT NULL DEFAULT '',
            end_utc TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL DEFAULT '',
            end_date_exclusive TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            date_precision TEXT NOT NULL DEFAULT 'exact'
                CHECK (date_precision IN ('exact', 'approximate')),
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'cancelled')),
            archived_at TEXT NOT NULL DEFAULT '',
            CHECK (
                (
                    is_all_day = 0
                    AND start_utc <> '' AND end_utc <> '' AND start_utc < end_utc
                    AND start_date = '' AND end_date_exclusive = ''
                    AND timezone <> ''
                )
                OR
                (
                    is_all_day = 1
                    AND start_date <> '' AND end_date_exclusive <> ''
                    AND start_date < end_date_exclusive
                    AND start_utc = '' AND end_utc = '' AND timezone = ''
                )
            )
        );
        CREATE INDEX IF NOT EXISTS idx_events_active_time
            ON events (archived_at, is_all_day, start_utc, start_date, entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_calendar
            ON events (calendar_id, archived_at, entity_id);
        """
    )


def create_event_recurrence_tables(connection: sqlite3.Connection) -> None:
    """Store Event series definitions and traceable occurrence exceptions."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS event_recurrences (
            event_id INTEGER PRIMARY KEY REFERENCES events(entity_id) ON DELETE CASCADE,
            frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
            interval INTEGER NOT NULL CHECK (interval > 0),
            weekdays_json TEXT NOT NULL DEFAULT '[]',
            monthly_ordinal INTEGER NOT NULL DEFAULT 0 CHECK (monthly_ordinal BETWEEN -1 AND 5),
            monthly_weekday INTEGER NOT NULL DEFAULT -1 CHECK (monthly_weekday BETWEEN -1 AND 6),
            until_date TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_recurrence_exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL REFERENCES events(entity_id) ON DELETE CASCADE,
            occurrence_date TEXT NOT NULL,
            recurrence_version INTEGER NOT NULL,
            exception_type TEXT NOT NULL CHECK (exception_type IN ('cancelled', 'override')),
            override_json TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (event_id, occurrence_date, recurrence_version)
        );
        CREATE TABLE IF NOT EXISTS event_recurrence_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_event_id INTEGER NOT NULL REFERENCES events(entity_id) ON DELETE CASCADE,
            successor_event_id INTEGER NOT NULL REFERENCES events(entity_id) ON DELETE CASCADE,
            split_occurrence_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (source_event_id, successor_event_id),
            UNIQUE (source_event_id, split_occurrence_date)
        );
        CREATE INDEX IF NOT EXISTS idx_event_recurrence_exceptions_series
            ON event_recurrence_exceptions (event_id, recurrence_version, occurrence_date);
        CREATE INDEX IF NOT EXISTS idx_event_recurrence_splits_source
            ON event_recurrence_splits (source_event_id, split_occurrence_date);
        """
    )


def create_calendar_interchange_tables(connection: sqlite3.Connection) -> None:
    """Create local interchange identity and read-only URL Calendar cache storage."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS event_icalendar_identities (
            event_id INTEGER PRIMARY KEY REFERENCES events(entity_id) ON DELETE CASCADE,
            source_uid TEXT NOT NULL COLLATE BINARY UNIQUE,
            source_sequence INTEGER NOT NULL DEFAULT 0 CHECK (source_sequence >= 0),
            source_fingerprint TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS calendar_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT NOT NULL UNIQUE,
            final_url TEXT NOT NULL,
            name TEXT NOT NULL,
            colour TEXT NOT NULL,
            timezone TEXT NOT NULL DEFAULT 'Australia/Brisbane',
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            etag TEXT NOT NULL DEFAULT '',
            last_modified TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT '',
            last_checked_at TEXT NOT NULL DEFAULT '',
            last_success_at TEXT NOT NULL DEFAULT '',
            current_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_calendar_subscriptions_order
            ON calendar_subscriptions (enabled DESC, sort_order, lower(name), id);

        CREATE TABLE IF NOT EXISTS external_calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL
                REFERENCES calendar_subscriptions(id) ON DELETE CASCADE,
            source_uid TEXT NOT NULL COLLATE BINARY,
            source_sequence INTEGER NOT NULL DEFAULT 0 CHECK (source_sequence >= 0),
            source_fingerprint TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            start_date TEXT NOT NULL,
            end_date_exclusive TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned'
                CHECK (status IN ('planned', 'cancelled')),
            recurrence_json TEXT NOT NULL DEFAULT '',
            UNIQUE (subscription_id, source_uid),
            CHECK (start_date < end_date_exclusive)
        );
        CREATE INDEX IF NOT EXISTS idx_external_calendar_events_dates
            ON external_calendar_events (
                subscription_id, start_date, end_date_exclusive, id
            );
        """
    )


def create_task_list_table(connection: sqlite3.Connection) -> None:
    """Create local Task-list configuration without a second classification layer."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS task_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT ''
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_task_lists_one_default
            ON task_lists (is_default) WHERE is_default = 1;
        CREATE INDEX IF NOT EXISTS idx_task_lists_active_name
            ON task_lists (archived_at, lower(name), id);
        """
    )
    if connection.execute("SELECT 1 FROM task_lists LIMIT 1").fetchone() is None:
        now = utc_now()
        connection.execute(
            """INSERT INTO task_lists (name, is_default, created_at, updated_at)
               VALUES ('Tasks', 1, ?, ?)""",
            (now, now),
        )


def create_task_table(connection: sqlite3.Connection) -> None:
    """Create canonical Task storage; temporal session storage follows separately."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
            task_list_id INTEGER NOT NULL REFERENCES task_lists(id) ON DELETE RESTRICT,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'completed')),
            completed_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL DEFAULT '',
            CHECK ((status = 'open' AND completed_at = '')
                   OR (status = 'completed' AND completed_at <> ''))
        );
        CREATE INDEX IF NOT EXISTS idx_tasks_list_status
            ON tasks (task_list_id, archived_at, status, entity_id);
        """
    )


def create_task_temporal_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS task_deadlines (
            task_id INTEGER PRIMARY KEY REFERENCES tasks(entity_id) ON DELETE CASCADE,
            due_date TEXT NOT NULL DEFAULT '', due_utc TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '',
            CHECK ((due_date <> '' AND due_utc = '' AND timezone = '') OR
                   (due_date = '' AND due_utc <> '' AND timezone <> ''))
        );
        CREATE TABLE IF NOT EXISTS task_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(entity_id) ON DELETE CASCADE,
            is_all_day INTEGER NOT NULL CHECK (is_all_day IN (0, 1)),
            start_date TEXT NOT NULL DEFAULT '', end_date_exclusive TEXT NOT NULL DEFAULT '',
            start_utc TEXT NOT NULL DEFAULT '', end_utc TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            CHECK ((is_all_day = 1 AND start_date <> '' AND end_date_exclusive <> '' AND start_date < end_date_exclusive AND start_utc = '' AND end_utc = '' AND timezone = '') OR
                   (is_all_day = 0 AND start_utc <> '' AND end_utc <> '' AND start_utc < end_utc AND timezone <> '' AND start_date = '' AND end_date_exclusive = ''))
        );
        CREATE INDEX IF NOT EXISTS idx_task_sessions_task ON task_sessions(task_id, id);
        CREATE INDEX IF NOT EXISTS idx_task_sessions_time ON task_sessions(is_all_day, start_date, start_utc, task_id);
    """)


def create_reminder_tables(connection: sqlite3.Connection) -> None:
    """Persist Phase 2C reminder policy, delivery identity and Inbox state."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS reminder_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_kind TEXT NOT NULL CHECK (context_kind IN ('global', 'calendar', 'calendar_subscription', 'task_list')),
            context_id INTEGER NOT NULL DEFAULT 0,
            source_kind TEXT NOT NULL CHECK (source_kind IN ('event', 'task_deadline', 'birthday', 'document_expiry')),
            timings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (context_kind, context_id, source_kind)
        );
        CREATE TABLE IF NOT EXISTS reminder_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_kind TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            occurrence_key TEXT NOT NULL DEFAULT '',
            mode TEXT NOT NULL CHECK (mode IN ('default', 'custom', 'disabled')) DEFAULT 'default',
            custom_timings_json TEXT NOT NULL DEFAULT '[]',
            suppressed_timings_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            UNIQUE (source_kind, source_id, occurrence_key)
        );
        CREATE TABLE IF NOT EXISTS inbox_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_key TEXT NOT NULL UNIQUE,
            source_kind TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            occurrence_key TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL,
            timing TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            due_at TEXT NOT NULL,
            delivered_at TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('active', 'acknowledged', 'dismissed', 'resolved', 'snoozed')) DEFAULT 'active',
            next_attention_at TEXT NOT NULL DEFAULT '',
            acted_at TEXT NOT NULL DEFAULT '',
            action_note TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_active_attention ON inbox_items(state, next_attention_at, due_at, id);
        CREATE INDEX IF NOT EXISTS idx_inbox_source_active ON inbox_items(source_kind, source_id, state);
    """)


def expand_reminder_policy_contexts_for_external_calendars(
    connection: sqlite3.Connection,
) -> None:
    """Allow read-only URL Calendars to own Event notification defaults."""
    create_reminder_tables(connection)
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'reminder_policies'"
    ).fetchone()
    if row is not None and "'calendar_subscription'" in (row["sql"] or ""):
        return
    connection.executescript(
        """
        ALTER TABLE reminder_policies RENAME TO reminder_policies_legacy;

        CREATE TABLE reminder_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            context_kind TEXT NOT NULL
                CHECK (context_kind IN (
                    'global', 'calendar', 'calendar_subscription', 'task_list'
                )),
            context_id INTEGER NOT NULL DEFAULT 0,
            source_kind TEXT NOT NULL
                CHECK (source_kind IN (
                    'event', 'task_deadline', 'birthday', 'document_expiry'
                )),
            timings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (context_kind, context_id, source_kind)
        );

        INSERT INTO reminder_policies (
            id, context_kind, context_id, source_kind, timings_json, updated_at
        )
        SELECT
            id, context_kind, context_id, source_kind, timings_json, updated_at
        FROM reminder_policies_legacy;

        DROP TABLE reminder_policies_legacy;
        """
    )


def add_inbox_delivery_timing(connection: sqlite3.Connection) -> None:
    """Add explicit timing to existing deliveries for policy reconciliation."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(inbox_items)")}
    if "timing" not in columns:
        connection.execute("ALTER TABLE inbox_items ADD COLUMN timing TEXT NOT NULL DEFAULT ''")


def create_inbox_action_history_table(connection: sqlite3.Connection) -> None:
    """Retain every Inbox state transition separately from current item state."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS inbox_item_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inbox_item_id INTEGER NOT NULL REFERENCES inbox_items(id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            previous_state TEXT NOT NULL,
            resulting_state TEXT NOT NULL,
            next_attention_at TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            acted_at TEXT NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_inbox_item_actions_item ON inbox_item_actions(inbox_item_id, id)")


def create_scheduler_tables(connection: sqlite3.Connection) -> None:
    """Persist registered local jobs, their execution attempts and recovery state."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            handler_name TEXT NOT NULL,
            interval_seconds INTEGER NOT NULL CHECK (interval_seconds > 0),
            catch_up_policy TEXT NOT NULL CHECK (catch_up_policy IN ('coalesce', 'current_interval', 'one_off', 'historical')),
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            next_run_at TEXT NOT NULL,
            last_run_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'running', 'failed', 'disabled')),
            lease_token TEXT NOT NULL DEFAULT '',
            lease_expires_at TEXT NOT NULL DEFAULT '',
            failure_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_due
            ON scheduled_jobs (enabled, next_run_at, id);
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES scheduled_jobs(id) ON DELETE RESTRICT,
            scheduled_for TEXT NOT NULL,
            trigger_kind TEXT NOT NULL CHECK (trigger_kind IN ('scheduled', 'startup_recovery', 'manual', 'rerun')),
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'expired')),
            details TEXT NOT NULL DEFAULT '',
            failure_reason TEXT NOT NULL DEFAULT '',
            UNIQUE (job_id, scheduled_for, trigger_kind)
        );
        CREATE INDEX IF NOT EXISTS idx_job_runs_job ON job_runs (job_id, started_at DESC, id DESC);
        CREATE TABLE IF NOT EXISTS scheduler_checkpoints (
            checkpoint_key TEXT PRIMARY KEY,
            checkpoint_at TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT ''
        );
    """)


def create_automation_tables(connection: sqlite3.Connection) -> None:
    """Persist registered deterministic automation and approval-bound proposals."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS automation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_key TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            trigger_name TEXT NOT NULL,
            action_name TEXT NOT NULL,
            conditions_json TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS automation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL REFERENCES automation_rules(id) ON DELETE RESTRICT,
            trigger_key TEXT NOT NULL,
            trigger_name TEXT NOT NULL,
            source_kind TEXT NOT NULL DEFAULT '',
            source_id INTEGER NOT NULL DEFAULT 0,
            input_json TEXT NOT NULL DEFAULT '{}',
            outcome_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL CHECK (status IN ('completed', 'skipped', 'failed')),
            failure_reason TEXT NOT NULL DEFAULT '',
            occurred_at TEXT NOT NULL,
            UNIQUE (rule_id, trigger_key)
        );
        CREATE INDEX IF NOT EXISTS idx_automation_runs_rule ON automation_runs(rule_id, occurred_at DESC, id DESC);
        CREATE TABLE IF NOT EXISTS automation_review_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_key TEXT NOT NULL UNIQUE,
            rule_id INTEGER NOT NULL REFERENCES automation_rules(id) ON DELETE RESTRICT,
            automation_run_id INTEGER NOT NULL REFERENCES automation_runs(id) ON DELETE RESTRICT,
            source_kind TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            mutation_kind TEXT NOT NULL CHECK (mutation_kind IN ('create_task')),
            proposed_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            state TEXT NOT NULL CHECK (state IN ('pending', 'approved', 'rejected')),
            created_at TEXT NOT NULL,
            decided_at TEXT NOT NULL DEFAULT '',
            decision_note TEXT NOT NULL DEFAULT '',
            resulting_entity_id INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_automation_review_state ON automation_review_items(state, created_at, id);
    """)


def correct_event_grouping_model(connection: sqlite3.Connection) -> None:
    """Migrate category-bearing development databases to Calendar-only Events."""
    create_calendar_table(connection)
    event_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(events)")
    }
    if "category_id" in event_columns:
        connection.executescript(
            """
            CREATE TABLE events_corrected (
                entity_id INTEGER PRIMARY KEY
                    REFERENCES entities(id) ON DELETE CASCADE,
                calendar_id INTEGER NOT NULL
                    REFERENCES calendars(id) ON DELETE RESTRICT,
                is_all_day INTEGER NOT NULL CHECK (is_all_day IN (0, 1)),
                start_utc TEXT NOT NULL DEFAULT '',
                end_utc TEXT NOT NULL DEFAULT '',
                start_date TEXT NOT NULL DEFAULT '',
                end_date_exclusive TEXT NOT NULL DEFAULT '',
                timezone TEXT NOT NULL DEFAULT '',
                date_precision TEXT NOT NULL DEFAULT 'exact'
                    CHECK (date_precision IN ('exact', 'approximate')),
                status TEXT NOT NULL DEFAULT 'planned'
                    CHECK (status IN ('planned', 'cancelled')),
                archived_at TEXT NOT NULL DEFAULT '',
                CHECK (
                    (
                        is_all_day = 0
                        AND start_utc <> '' AND end_utc <> ''
                        AND start_utc < end_utc
                        AND start_date = '' AND end_date_exclusive = ''
                        AND timezone <> ''
                    )
                    OR
                    (
                        is_all_day = 1
                        AND start_date <> '' AND end_date_exclusive <> ''
                        AND start_date < end_date_exclusive
                        AND start_utc = '' AND end_utc = '' AND timezone = ''
                    )
                )
            );
            INSERT INTO events_corrected (
                entity_id, calendar_id, is_all_day, start_utc, end_utc,
                start_date, end_date_exclusive, timezone, date_precision,
                status, archived_at
            )
            SELECT
                entity_id, calendar_id, is_all_day, start_utc, end_utc,
                start_date, end_date_exclusive, timezone, date_precision,
                status, archived_at
            FROM events;
            DROP TABLE events;
            ALTER TABLE events_corrected RENAME TO events;
            """
        )
    connection.execute(
        """
        UPDATE calendars
        SET name = 'General', updated_at = ?
        WHERE is_default = 1 AND name = 'Calendar'
          AND NOT EXISTS (
              SELECT 1 FROM calendars AS existing
              WHERE existing.name = 'General'
          )
        """,
        (utc_now(),),
    )
    connection.execute("DROP TABLE IF EXISTS event_categories")
    connection.execute(
        "DELETE FROM provenance_metadata WHERE field_name = 'category_id'"
    )
    create_event_table(connection)


def create_journal_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_journal_entries_entity_chronology
            ON journal_entries (entity_type, entity_id, archived_at, created_at, id);
        """
    )


def create_entity_alias_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS entity_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            value TEXT NOT NULL COLLATE NOCASE,
            created_at TEXT NOT NULL,
            UNIQUE (entity_id, value)
        );
        CREATE INDEX IF NOT EXISTS idx_entity_aliases_value
            ON entity_aliases (value COLLATE NOCASE);
        """
    )


def clean_document_domain_fields(connection: sqlite3.Connection) -> None:
    """Remove the superseded issuer scalar and format-like purpose values."""
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'"
    ).fetchone()
    if table is None:
        return
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(documents)")}
    if "issuer" in columns:
        connection.execute("ALTER TABLE documents DROP COLUMN issuer")
    connection.execute(
        "UPDATE documents SET document_type='Other' WHERE document_type IN ('Image','PDF')"
    )


def create_platform_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, actor TEXT NOT NULL DEFAULT 'local_user', notes TEXT NOT NULL DEFAULT '', before_json TEXT NOT NULL DEFAULT '', after_json TEXT NOT NULL DEFAULT '', provenance TEXT NOT NULL DEFAULT 'manual');
        CREATE TABLE IF NOT EXISTS audit_event_records (event_id INTEGER NOT NULL REFERENCES audit_events(id) ON DELETE CASCADE, record_kind TEXT NOT NULL, record_id INTEGER NOT NULL, PRIMARY KEY (event_id, record_kind, record_id));
        CREATE INDEX IF NOT EXISTS idx_audit_records ON audit_event_records(record_kind, record_id);
        CREATE TABLE IF NOT EXISTS provenance_metadata (record_kind TEXT NOT NULL, record_id INTEGER NOT NULL, field_name TEXT NOT NULL, provenance TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (record_kind, record_id, field_name));
        CREATE TABLE IF NOT EXISTS data_quality_finding_state (finding_key TEXT PRIMARY KEY, status TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
    """)


def backfill_platform_audit_events(connection: sqlite3.Connection) -> None:
    """Seed audit visibility for canonical records created before generic audit existed."""
    for row in connection.execute("SELECT id, created_at, updated_at FROM entities ORDER BY id"):
        created = connection.execute(
            "INSERT INTO audit_events(event_type, occurred_at, actor, notes, provenance) VALUES('create', ?, 'system', 'Backfilled from canonical record timestamp', 'unknown')",
            (row["created_at"],),
        )
        connection.execute("INSERT INTO audit_event_records VALUES(?, 'entity', ?)", (created.lastrowid, row["id"]))
        updated = connection.execute(
            "INSERT INTO audit_events(event_type, occurred_at, actor, notes, provenance) VALUES('edit', ?, 'system', 'Backfilled from canonical record timestamp', 'unknown')",
            (row["updated_at"],),
        )
        connection.execute("INSERT INTO audit_event_records VALUES(?, 'entity', ?)", (updated.lastrowid, row["id"]))
    for row in connection.execute("SELECT id, source_entity_id, target_entity_id, created_at FROM relationships ORDER BY id"):
        event = connection.execute(
            "INSERT INTO audit_events(event_type, occurred_at, actor, notes, provenance) VALUES('relationship_change', ?, 'system', 'Relationship created (backfilled)', 'unknown')",
            (row["created_at"],),
        )
        references = ((event.lastrowid, "relationship", row["id"]), (event.lastrowid, "entity", row["source_entity_id"]), (event.lastrowid, "entity", row["target_entity_id"]))
        connection.executemany("INSERT INTO audit_event_records VALUES(?, ?, ?)", references)


def create_entity_history_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS entity_edit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entity_edit_history_entity
            ON entity_edit_history (entity_id, created_at);
        """
    )

def create_entity_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ({allowed_entity_type_sql()})),
            display_name TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_viewed_at TEXT NOT NULL DEFAULT '',
            is_favourite INTEGER NOT NULL DEFAULT 0,
            deleted_at TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_entities_type_name
            ON entities (type, display_name);
        """
    )


def create_typed_entity_tables(connection: sqlite3.Connection) -> None:
    for definition in ENTITY_DEFINITIONS:
        create_typed_table(connection, definition)
        ensure_typed_columns(connection, definition)


def ensure_entity_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(entities)")}
    if "last_viewed_at" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN last_viewed_at TEXT NOT NULL DEFAULT ''")
    if "is_favourite" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN is_favourite INTEGER NOT NULL DEFAULT 0")
    if "deleted_at" not in columns:
        connection.execute("ALTER TABLE entities ADD COLUMN deleted_at TEXT NOT NULL DEFAULT ''")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_entities_deleted_at ON entities(deleted_at)")


def ensure_entity_type_constraint(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'entities'"
    ).fetchone()
    create_sql = row["sql"] if row else ""
    if all(
        sql_literal(definition.type) in create_sql
        for definition in ALL_ENTITY_DEFINITIONS
    ):
        return

    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    try:
        connection.executescript(
            f"""
            CREATE TABLE entities_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ({allowed_entity_type_sql()})),
                display_name TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_viewed_at TEXT NOT NULL DEFAULT '',
                is_favourite INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT NOT NULL DEFAULT ''
            );

            INSERT INTO entities_new (
                id, type, display_name, summary, notes,
                created_at, updated_at, last_viewed_at, is_favourite, deleted_at
            )
            SELECT
                id, type, display_name, summary, notes,
                created_at, updated_at, last_viewed_at, is_favourite, deleted_at
            FROM entities;

            DROP TABLE entities;
            ALTER TABLE entities_new RENAME TO entities;

            CREATE INDEX IF NOT EXISTS idx_entities_type_name
                ON entities (type, display_name);
            CREATE INDEX IF NOT EXISTS idx_entities_deleted_at
                ON entities (deleted_at);
            """
        )
        connection.commit()
    finally:
        connection.execute("PRAGMA foreign_keys = ON")


def create_typed_table(connection: sqlite3.Connection, definition: EntityDefinition) -> None:
    table = sql_identifier(definition.table)
    field_columns = ",\n            ".join(
        f"{sql_identifier(field.name)} TEXT NOT NULL DEFAULT ''"
        for field in definition.fields if field.typed_column
    )
    columns_sql = ",\n            " + field_columns if field_columns else ""
    connection.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            entity_id INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE{columns_sql}
        );
        """
    )


def ensure_typed_columns(connection: sqlite3.Connection, definition: EntityDefinition) -> None:
    table = sql_identifier(definition.table)
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    for field in definition.fields:
        if not field.typed_column:
            continue
        if field.name not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {sql_identifier(field.name)} TEXT NOT NULL DEFAULT ''"
            )
            columns.add(field.name)
        migrate_previous_field_values(connection, definition, field, columns)
        migrate_field_value_aliases(connection, definition, field, columns)


def migrate_previous_field_values(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    field,
    columns: set[str],
) -> None:
    table = sql_identifier(definition.table)
    target = sql_identifier(field.name)
    for previous_name in field.previous_names:
        if previous_name not in columns:
            continue
        previous = sql_identifier(previous_name)
        connection.execute(
            f"""
            UPDATE {table}
            SET {target} = {previous}
            WHERE {target} = '' AND {previous} <> ''
            """
        )


def migrate_field_value_aliases(
    connection: sqlite3.Connection,
    definition: EntityDefinition,
    field,
    columns: set[str],
) -> None:
    if field.name not in columns:
        return
    table = sql_identifier(definition.table)
    column = sql_identifier(field.name)
    for old_value, new_value in field.value_aliases:
        connection.execute(
            f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
            (new_value, old_value),
        )


def create_relationship_table(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            started_at TEXT NOT NULL DEFAULT '',
            started_at_precision TEXT NOT NULL DEFAULT 'exact',
            ended_at TEXT NOT NULL DEFAULT '',
            ended_at_precision TEXT NOT NULL DEFAULT 'exact',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT NOT NULL DEFAULT '',
            CHECK (source_entity_id <> target_entity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_relationships_source
            ON relationships (source_entity_id);

        CREATE INDEX IF NOT EXISTS idx_relationships_target
            ON relationships (target_entity_id);

        CREATE INDEX IF NOT EXISTS idx_relationships_type
            ON relationships (type);
        """
    )
    ensure_relationship_columns(connection)


def ensure_relationship_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(relationships)")}
    if "started_at_precision" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN started_at_precision TEXT NOT NULL DEFAULT 'exact'")
    if "ended_at_precision" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN ended_at_precision TEXT NOT NULL DEFAULT 'exact'")
    if "record_origin" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN record_origin TEXT NOT NULL DEFAULT 'manual'")
    if "inference_suggestion_id" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN inference_suggestion_id INTEGER")
    if "provenance_json" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN provenance_json TEXT NOT NULL DEFAULT ''")
    if "created_from_inference" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN created_from_inference INTEGER NOT NULL DEFAULT 0")
    if "inference_evidence_status" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN inference_evidence_status TEXT NOT NULL DEFAULT ''")
    if "deleted_at" not in columns:
        connection.execute("ALTER TABLE relationships ADD COLUMN deleted_at TEXT NOT NULL DEFAULT ''")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_relationships_deleted_at ON relationships(deleted_at)")
    # Confirmed suggestions are ordinary user-owned relationships. Migrate rows
    # created under the earlier read-only origin model without losing provenance.
    connection.execute("""UPDATE relationships
        SET created_from_inference=1, record_origin='manual',
            inference_evidence_status=CASE WHEN inference_evidence_status='' THEN 'current' ELSE inference_evidence_status END
        WHERE record_origin='inferred' OR inference_suggestion_id IS NOT NULL""")


def create_inference_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS inference_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, trigger_type TEXT NOT NULL,
            trigger_id INTEGER, status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL, dismissed_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS inference_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL REFERENCES inference_batches(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL DEFAULT '', started_at_precision TEXT NOT NULL DEFAULT 'exact',
            status TEXT NOT NULL DEFAULT 'pending', source_type TEXT NOT NULL DEFAULT 'deterministic_rule',
            rule_key TEXT NOT NULL, supporting_relationship_ids TEXT NOT NULL,
            evidence_fingerprint TEXT NOT NULL, created_at TEXT NOT NULL,
            reviewed_at TEXT NOT NULL DEFAULT '',
            CHECK (source_entity_id <> target_entity_id)
        );
        CREATE INDEX IF NOT EXISTS idx_inference_suggestions_status ON inference_suggestions(status, batch_id);
        CREATE INDEX IF NOT EXISTS idx_inference_suggestions_pair ON inference_suggestions(type, source_entity_id, target_entity_id);
        """
    )


SCHEMA_MIGRATIONS = (
    ("20260628_01_core_entities", create_entity_table),
    ("20260628_02_typed_entities", create_typed_entity_tables),
    ("20260628_03_relationships", create_relationship_table),
    ("20260628_04_entity_edit_history", create_entity_history_table),
    ("20260628_05_relationship_inference", create_inference_tables),
    ("20260628_06_platform_infrastructure", create_platform_tables),
    ("20260628_07_backfill_platform_audit", backfill_platform_audit_events),
    ("20260704_08_journal_entries", create_journal_table),
    ("20260704_09_entity_soft_delete", ensure_entity_columns),
    ("20260704_10_reference_data", create_reference_data_tables),
    ("20260704_11_measurement_units", create_unit_tables),
    ("20260704_12_taxonomies", lambda connection: __import__("app.taxonomy", fromlist=["create_taxonomy_tables"]).create_taxonomy_tables(connection)),
    ("20260705_13_entity_aliases", create_entity_alias_table),
    ("20260705_14_document_domain_cleanup", clean_document_domain_fields),
    ("20260705_15_relationship_soft_delete", ensure_relationship_columns),
    (
        "20260719_16_temporal_foundation",
        create_initial_temporal_foundation_tables,
    ),
    ("20260719_17_canonical_events", create_initial_event_table),
    ("20260719_18_remove_event_categories", correct_event_grouping_model),
    ("20260719_19_calendar_management_history", create_calendar_history_table),
    ("20260719_20_event_recurrence", create_event_recurrence_tables),
    ("20260720_21_task_lists_and_tasks", lambda connection: (create_task_list_table(connection), create_task_table(connection))),
    ("20260723_22_task_temporal_values", create_task_temporal_tables),
    ("20260723_23_reminder_and_inbox_foundation", create_reminder_tables),
    ("20260725_24_inbox_delivery_timing", add_inbox_delivery_timing),
    ("20260725_25_inbox_action_history", create_inbox_action_history_table),
    ("20260725_26_operational_scheduler", create_scheduler_tables),
    ("20260725_27_deterministic_automation", create_automation_tables),
    ("20260725_28_birthday_calendar", lambda connection: (create_calendar_table(connection), create_birthday_event_links_table(connection), migrate_birthday_reminder_policy(connection), __import__("app.birthday_calendar", fromlist=["sync_all_birthdays"]).sync_all_birthdays(connection))),
    ("20260730_29_calendar_interchange", create_calendar_interchange_tables),
    (
        "20260730_30_external_calendar_reminders",
        expand_reminder_policy_contexts_for_external_calendars,
    ),
)

SCHEMA_MIGRATION_IDS = tuple(migration_id for migration_id, _ in SCHEMA_MIGRATIONS)
if len(SCHEMA_MIGRATION_IDS) != len(set(SCHEMA_MIGRATION_IDS)):
    raise ValueError("Schema migration identifiers must be unique.")
