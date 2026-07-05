Project Scope
-------------
Project E is a local-first Personal Information Platform. Personal operational intelligence is the longer-term direction; Stage 1 stores, organises and navigates structured information about People, Organisations, Locations, Projects, Documents, Assets and Relationships.

Design Principles
-----------------
- Entity-first and relationship-first.
- One canonical record per real-world object, with multiple views over the same data.
- Local-first: core records and workflows must remain usable without WAN access; optional map resources may use replaceable network services.
- Prefer maintainable, simple architecture and free/open-source software.
- Use locally hosted PostgreSQL as the canonical database and keep access behind the Project E database boundary. Add dependencies conservatively and document the reason.

Stage 1 Boundaries
------------------
Stage 1 may use deterministic, local and explainable assistance or internal maintenance when it preserves user control. Consequential mutations require explicit user confirmation. Do not introduce AI, chat, dispatcher architecture, decision support, autonomous goal-directed workflows, scheduling, unreviewed consequential actions, autonomous external side effects, login, multi-user accounts, WAN-dependent core operation, mobile access or cloud dependencies. Capabilities crossing those boundaries require explicit user direction.

Repository-First Workflow
-------------------------
- Treat current code and repository documentation as the source of truth; do not rely on assumptions or prior-session handoffs.
- Implementation prompts define the authorised task. Roadmap items provide context, not permission to implement them.
- Review, diagnosis and audit requests are read-only unless the user explicitly requests changes.
- Inspect the working tree before editing and preserve unrelated changes. Never overwrite or revert user work outside the requested scope.
- Prefer established module boundaries and stable facades. Make the smallest maintainable change that fully satisfies the task.
- Add focused tests for changed behaviour and regressions. Before finishing implementation, run `python3 -m unittest discover -s tests` and `python3 -m compileall app run.py tests`, or report why a check could not run.
- Schema changes must use migration-safe evolution. Where applicable, verify both fresh database creation and upgrade from an existing schema.
- For UI work, smoke-test the relevant workflow in the running application where practical, in addition to automated tests.
- Commit completed changes unless the user explicitly says not to commit. Use a concise, descriptive subject and a commit body that records what changed and why. Do not add agent, model or tool attribution to the commit message.

Documentation Responsibilities
------------------------------
Documentation is part of implementation. Proactively update every existing document made inaccurate by a change; prefer updating an appropriate document over creating a new one. Before finishing, audit relevant documents and either update them or explicitly verify that no documentation change is needed.

Repository documents have distinct responsibilities:
- `PROJECT_GOAL.md`: durable product purpose, scope and principles.
- `docs/stage_1_spec.md`: current Stage 1 behaviour and acceptance criteria.
- `ROADMAP.md`: phased capability direction and current priorities; not implementation authority.
- `docs/future_direction.md`: long-term platform, AI and Odysseus direction; not current architecture.
- `docs/architecture.md`: current application structure and boundaries.
- `docs/database_design.md`: persistence, schema and migration rules.
- `docs/ontology.md`: entity and relationship semantics.
- `docs/glossary.md`: canonical terminology; consult it when language is unclear and update it when new terms are introduced.
- `docs/ui_principles.md`: durable interaction and presentation conventions.
- `ARCHITECTURE_DECISIONS.md`: durable architectural decisions and consequences.
- `docs/reviews/technical_debt_register.md`: unresolved actionable debt only; remove resolved items.
- `docs/build_log.md`: concise history of completed work.

Record important behaviour, constraints, migrations and follow-up work in the document responsible for that information, keeping feature status and reference documentation aligned with current code.

Repository Evolution
--------------------
Project E is in active development. Prefer clean architecture, then a practical migration, then a development database reset, and only then backwards compatibility. Remove obsolete fields and implementations instead of adding compatibility layers or duplicate sources of truth. Compatibility becomes a priority once the platform reaches a stable release.

If implementation uncovers a new long-term architectural decision, repository convention, project goal, documentation convention or workflow that is not documented, update the appropriate existing documentation when it is an obvious consequence of the requested work. If it materially changes project direction or establishes a new long-term convention, ask the user before making it permanent.

Privacy and Generated Files
---------------------------
- Never commit PostgreSQL data or dumps, uploaded documents, runtime data, personal data, logs, caches, exports, backups or other generated artifacts.
- Keep local data under Git-ignored locations such as `instance/`. Tracked fixtures must be clearly fictional, intentional and reviewed.

Codex Workspace Troubleshooting
-------------------------------
These notes apply only to Codex in this workspace.
- Use the most appropriate editing method available in the current environment. If `apply_patch` is unavailable, edit files directly with Python or standard shell tools. Do not retry unavailable tooling.
- Sandboxed commands may fail to start with `No such file or directory`. Use the working alternative directly, including `sandbox_permissions="require_escalated"` with a short justification when required.
- For application smoke tests, run `python3 run.py` on a temporary port, probe it locally, and stop the process afterward.
