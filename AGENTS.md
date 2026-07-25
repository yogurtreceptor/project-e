Project Scope
-------------
Project E is a local-first Personal Information Platform for one private user. Phase 1 is complete and Phase 2 is in progress. The platform stores, organises and navigates canonical People, Organisations, Locations, Projects, Documents, Assets, Events and Tasks, their Relationships, and local operational records such as Calendars, reminders and Inbox deliveries. Personal operational intelligence remains the longer-term direction.

Quick Commands
--------------
- Run locally: `python3 run.py`
- Run the full test suite: `python3 -m unittest discover -s tests`
- Compile-check the application and tests: `python3 -m compileall app run.py tests`

Technical Route Map
-------------------
- The runtime uses standard-library Python with no third-party Python packages. SQLite is the canonical store.
- `run.py` starts the local HTTP application. Runtime data belongs under Git-ignored `instance/`.
- `app/db.py` and `app/views.py` are stable persistence and rendering facades. Keep focused schema, repository, service and page work behind those boundaries.
- `app/db_schema.py` owns schema creation, the append-only migration ledger and migration-safe repair. Focused persistence lives in repository modules.
- `app/view_pages/` owns focused page rendering. `app/web.py` owns HTTP routing, request parsing and responses.
- `tests/` contains the standard-library `unittest` suite. Follow the nearest existing service, repository, page and test patterns rather than creating parallel abstractions.

Design Principles
-----------------
- Entity-first and relationship-first.
- One canonical record per real-world object, with multiple views and deterministic projections over the same data.
- Local-first: core records and workflows must remain usable without WAN access; optional map resources may use replaceable network services.
- Prefer maintainable, simple architecture and free/open-source dependencies.
- Use SQLite and conservative dependencies. Add a dependency only when the standard library and existing code cannot reasonably meet the need, and document the reason.

Current Phase Boundaries
------------------------
- Implementation prompts define the authorised task. Plans and roadmap items provide context and boundaries, not permission to implement them.
- Phase 2 may include explicitly authorised, local and deterministic reminders, scheduling, registered background jobs and trigger-condition-action automation as defined in `docs/phase_2_workspace.md`.
- Deterministic maintenance may recalculate derived state and create operational or audit records within the documented contracts. Creating, editing, completing, archiving or deleting a canonical Event or Task requires explicit user approval.
- Do not introduce AI or agent workflows, chat, AI decision support, AI-generated autonomous actions, autonomous external side effects, arbitrary executable code, external notification or calendar channels, distributed workers or queues, login, multi-user accounts, WAN-dependent core operation, mobile access or cloud dependencies unless the user explicitly authorises a change in direction.

Repository-First Workflow
-------------------------
- Treat current code and repository documentation as the source of truth; do not rely on assumptions or prior-session handoffs.
- Review, diagnosis and audit requests are read-only unless the user explicitly requests changes.
- Inspect the working tree before editing and preserve unrelated changes. Never overwrite or revert user work outside the requested scope.
- Prefer established module boundaries and stable facades. Make the smallest maintainable change that fully satisfies the task.
- Add focused tests for changed behaviour and regressions. Before finishing implementation, run the full test and compile commands above, or report why a check could not run.
- Schema changes must use forward, migration-safe evolution and preserve the append-only migration ledger. Where applicable, verify both fresh database creation and upgrade from an existing schema.
- For UI work, smoke-test the relevant workflow in the running application where practical, in addition to automated tests.
- Commit completed changes unless the user explicitly says not to commit. Use a concise, descriptive subject and a commit body that records what changed and why. Do not add agent, model or tool attribution to the commit message.

Documentation Responsibilities
------------------------------
Documentation is part of implementation. Proactively update every existing document made inaccurate by a change; prefer updating an appropriate document over creating a new one. Before finishing, audit relevant documents and either update them or explicitly verify that no documentation change is needed.

Repository documents have distinct responsibilities:
- `PROJECT_GOAL.md`: durable product purpose, scope and principles.
- `docs/phase_1_spec.md`: delivered Phase 1 behaviour and acceptance criteria.
- `docs/phase_2_workspace.md`: living Phase 2 scope, delivery record, completion criteria and exclusions; not implementation authority.
- `ROADMAP.md`: phased capability direction and priorities; not implementation authority.
- `docs/future_direction.md`: long-term platform, AI and Odysseus direction; not current architecture.
- `docs/architecture.md`: current application structure and boundaries.
- `docs/database_design.md`: persistence, schema and migration rules.
- `docs/ontology.md`: entity and relationship semantics.
- `docs/glossary.md`: canonical terminology; consult it when language is unclear and update it when new terms are introduced.
- `docs/experience_philosophy.md`, `docs/design/` and `docs/ui_principles.md`: experience direction, current design contracts and durable UI conventions.
- `ARCHITECTURE_DECISIONS.md`: durable architectural decisions and consequences.
- `SECURITY.md`: vulnerability-reporting policy and security-report data boundaries.
- `docs/reviews/technical_debt_register.md`: unresolved actionable debt only; remove resolved items.
- `docs/build_log.md`: concise history of completed work.

Record important behaviour, constraints, migrations and follow-up work in the document responsible for that information, keeping feature status and reference documentation aligned with current code.

Repository Evolution
--------------------
Project E is in active development. Prefer clean architecture, then a practical migration, then a development database reset, and only then backwards compatibility. Remove obsolete fields and implementations instead of adding compatibility layers or duplicate sources of truth. Compatibility becomes a priority once the platform reaches a stable release.

If implementation uncovers a new long-term architectural decision, repository convention, project goal, documentation convention or workflow that is not documented, update the appropriate existing document when it is an obvious consequence of the requested work. If it materially changes project direction or establishes a new long-term convention, ask the user before making it permanent.

Privacy and Generated Files
---------------------------
- Never commit databases, SQLite runtime files, uploaded documents, runtime data, personal data, credentials, logs, caches, exports, backups or other generated artifacts.
- Keep local data under Git-ignored locations such as `instance/`. Tracked fixtures must be clearly fictional, intentional and reviewed.

Codex Workspace Troubleshooting
-------------------------------
These notes apply only to Codex in this workspace.
- Use the most appropriate editing method available in the current environment. If `apply_patch` is unavailable, use the working editing alternative directly rather than retrying unavailable tooling.
- Sandboxed commands may fail to start with `No such file or directory`. Use the working alternative, including `sandbox_permissions="require_escalated"` with a short justification when required.
- For application smoke tests, run `python3 run.py` on a temporary port, probe it locally, and stop the process afterward.
