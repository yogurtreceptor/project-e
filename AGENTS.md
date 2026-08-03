# Project E agent guide

## Scope

Project E is a local-first Personal Information Platform for one private user. It stores canonical People, Organisations, Locations, Projects, Documents, Assets and Events; first-class Relationships; and local operational records such as Calendars, reminders and Inbox deliveries. Phases 1 and 2 are complete. Phase 3 spatial-intelligence planning is in progress. Personal operational intelligence remains a longer-term direction.

## Commands

- Run: `python3 run.py`
- Test: `python3 -m unittest discover -s tests`
- Compile: `python3 -m compileall app run.py tests`

## Technical route map

- The runtime is standard-library Python with SQLite and no third-party Python packages. Runtime data belongs under Git-ignored `instance/`.
- `app/db.py` and `app/views.py` are stable persistence and rendering facades. Keep focused work behind them.
- `app/db_schema.py` owns fresh-schema creation, the append-only migration ledger and migration-safe repair. Repositories and services own focused persistence and behaviour.
- `app/view_pages/` owns pages; `app/web.py` owns routing, request parsing and responses.
- Follow the nearest existing module and test patterns instead of creating parallel abstractions.

## Product and authority boundaries

- Be entity-first and relationship-first: one canonical record per real object, with deterministic views over the same data.
- Keep core records and workflows useful without WAN access. Optional map resources may use replaceable network services.
- Prefer simple, maintainable, free/open-source architecture. Add a dependency only when the standard library and current code cannot reasonably meet the need, and document why.
- The implementation prompt authorises work. Plans and roadmap items provide context, not permission.
- Phase 2's Calendar, Event, reminder, Inbox, scheduling and registered-automation behaviour remains current architecture. Phase 3 planning is an evolving desired state, not an implementation checklist.
- Deterministic maintenance may recalculate derived state and create contracted operational or audit records. Creating, editing, archiving or deleting a canonical Event requires explicit user approval.
- Do not introduce AI/agent workflows, autonomous external effects, arbitrary executable code, external notification or calendar channels, distributed workers or queues, login, multi-user accounts, WAN-dependent core operation, mobile access or cloud dependencies without separate explicit authorisation. A specifically authorised bounded AI capability must remain within canonical-data, validation, privacy, audit and user-control boundaries.

## Repository workflow

1. Treat current code and repository documentation as source of truth. Inspect the working tree and preserve unrelated work.
2. Reviews, diagnoses and audits are read-only unless changes are explicitly requested. For implementation, make the smallest coherent change behind established boundaries.
3. Evolve schemas forward and preserve the migration ledger. Verify fresh creation and representative upgrade paths when applicable.
4. Add focused behavioural and regression tests. Ordinary tests should use `tests/database_test_support.py`; tests of schema creation or migration must call the real initialisation path. Test count is not a target—remove a test only when its contract is obsolete or demonstrably duplicated.
5. Run the full test and compile commands before finishing, or report why they could not run. Smoke-test changed UI workflows on a temporary port where practical.
6. Update every existing document made inaccurate by the change. Prefer the responsible existing document over a new one.
7. Commit completed changes unless the user says not to. Use a concise subject and a body explaining what changed and why; omit agent/model/tool attribution.

During active development prefer clean architecture, then a practical migration, then a development database reset, and only then compatibility. Remove obsolete implementations rather than adding duplicate sources of truth. Ask before permanently changing product direction or establishing a material new long-term convention.

## Documentation routing

Load only the documents relevant to the task:

- Purpose and direction: `PROJECT_GOAL.md`, `ROADMAP.md`, `docs/future_direction.md`.
- Delivered phases and active planning: `docs/phase_1_spec.md`, `docs/phase_2_workspace.md`, `docs/phase_3_spatial_intelligence_planning.md`.
- Current technical contracts: `docs/architecture.md`, `docs/database_design.md`, `docs/ontology.md`, `docs/glossary.md`, `ARCHITECTURE_DECISIONS.md`.
- Experience and UI: `docs/experience_philosophy.md`, `docs/design/`, `docs/ui_principles.md`.
- Operations: `SECURITY.md`, `docs/reviews/technical_debt_register.md`, `docs/build_log.md`.

Keep status, reference documentation and code aligned. The technical-debt register contains unresolved actionable debt only; remove resolved items. The build log is concise cross-phase history. For an implementation within an active phase, add or amend a dated, numbered **Complete:** item in that phase's expansion workspace. Before committing, update a changed behaviour contract, the active-phase delivery entry and—only when cross-phase history warrants it—the build log.

## Privacy and generated files

Never commit databases, SQLite runtime files, uploaded documents, personal data, credentials, logs, caches, exports, backups or generated artifacts. Keep local data under ignored paths such as `instance/`. Tracked fixtures must be clearly fictional and intentional.

## Codex workspace notes

- If the preferred editor is unavailable, use the working editing alternative rather than retrying it.
- A sandboxed command may fail to start with `No such file or directory`; use the documented escalated alternative when required.
- For a smoke test, run `python3 run.py` on a temporary port, probe it locally and stop it afterward.
