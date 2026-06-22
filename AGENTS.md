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

Mixed Agent Workflow
--------------------
- Codex and Claude Code may both work on this repository.
- Both agents should rely on repository docs and current code, not assumptions from previous sessions.
- `docs/reviews/claude_handoff.md` is the compact handoff document for Claude Code.
- Codex-specific sandbox/workspace notes should remain clearly marked as Codex-specific and should not be treated as universal Claude Code instructions.
- When committing, use lightweight commit message trailers: `Agent: Codex` or `Agent: Claude`.
- Do not add per-file signatures or "written by" banners.
- Do not create separate duplicate instructions for each agent unless a workflow difference actually matters.

Workspace Tool Notes
--------------------
- In this workspace, sandboxed shell commands have often failed to start with `No such file or directory`.
- If that happens, retry ordinary read/test/run commands with `sandbox_permissions="require_escalated"` and a short justification.
- `sed`, `find`, `git status`, `python3 -m unittest discover -s tests`, and `python3 -m compileall app run.py tests` have worked well when run this way.
- `apply_patch` has sometimes failed to see workspace files; use it first for small edits, but a tightly scoped Python edit script has been the reliable fallback.
- For local app checks, start `python3 run.py` on a temporary port, smoke-test with `urllib.request`, then stop it with Ctrl+C through the running command session.
