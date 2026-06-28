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
Keep all planning documents current when architecture changes.
Consult `docs/glossary.md` when project terminology is unclear.

Agent Workflow
--------------
- Codex is the current primary implementation and review tool. Claude Code is optional and not part of the active workflow.
- All agents should rely on repository docs and current code, not assumptions from previous sessions.
- `docs/reviews/claude_handoff.md` is retained as historical implementation/refactor guidance; validate it against current code before use.
- Codex-specific sandbox/workspace notes are not universal instructions for other tools.
- When committing, use a lightweight agent trailer such as `Agent: Codex` (or `Agent: Claude` if Claude Code is used later).
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
