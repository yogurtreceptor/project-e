Project
-------
Operation Eddy

Purpose
-------
Build a local-first Personal Operational Intelligence Platform.

Current Stage
-------------
Stage 1 only.

Primary Goal
------------
Store, organise and navigate structured information.

Core Domains
------------
People
Organisations
Locations
Relationships

Core Principles
---------------
- Entity-first
- Relationship-first
- Local-first
- One canonical record per real-world object
- Multiple views over the same data
- Prefer maintainable solutions
- Prefer free/open-source software

Stage 1 Exclusions
------------------
No AI
No chat interface
No dispatcher
No automation
No scheduling
No login
No WAN

Implementation Preferences
--------------------------
- Lightweight dependencies
- Simple architecture
- SQLite or equivalent local database
- Clean UI
- Meaningful tests only
- Concise documentation

Documentation
-------------
- Treat documentation as part of every feature, behaviour, schema, workflow, and architecture change.
- Before finishing work, audit the relevant planning and reference documents and update every affected one; do not update only the architecture document.
- Keep feature status, roadmap/planning, architecture, database design, glossary/ontology, user workflow, and build log documentation aligned with the current code where relevant.
- Record important implementation decisions, constraints, exclusions, migrations, and follow-up work concisely so future agents can reconstruct the current state from the repository.
- If no documentation change is needed, explicitly verify that during review rather than assuming it.
- Consult `docs/glossary.md` when project terminology is unclear and add or revise terms when a feature introduces new language.

Agent Workflow
--------------
- Codex is the current primary implementation and review tool. Claude Code is optional and not part of the active workflow.
- All agents should rely on repository docs and current code, not assumptions from previous sessions.
- Point-in-time reviews and handoffs are not active guidance; use current code, the roadmap and the live technical-debt register.
- Codex-specific sandbox/workspace notes are not universal instructions for other tools.
- Commit messages must have a concise, descriptive subject explaining the delivered change; never use agent attribution as the subject or sole description.
- When committing, add a lightweight final trailer such as `Agent: Codex` (or `Agent: Claude` if Claude Code is used later) after the descriptive message.
- Do not add per-file signatures or "written by" banners.
- Do not create separate duplicate instructions for each agent unless a workflow difference actually matters.

Codex Workspace Tool Notes
--------------------------
- These troubleshooting notes apply to Codex only.
- In this workspace, sandboxed shell commands have often failed to start with `No such file or directory`.
- If that happens, retry ordinary read/test/run commands with `sandbox_permissions="require_escalated"` and a short justification.
- `sed`, `find`, `git status`, `python3 -m unittest discover -s tests`, and `python3 -m compileall app run.py tests` have worked well when run this way.
- If `apply_patch` fails or sandbox restrictions prevent it, diagnose once, then use a safe, tightly scoped Python/file rewrite instead of repeatedly retrying `apply_patch`.
- For local app checks, start `python3 run.py` on a temporary port, smoke-test with `urllib.request`, then stop it with Ctrl+C through the running command session.
