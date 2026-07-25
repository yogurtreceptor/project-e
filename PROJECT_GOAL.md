# Project Goal

Project E is a local-first Personal Information Platform: a durable private system for storing, connecting, understanding and eventually acting on meaningful personal information.

The platform must first become genuinely useful to a human user. It should make everyday information easier to capture, find, maintain and navigate through canonical entities, first-class relationships and coherent views. The embedded database remains the canonical source of truth.

The durable foundations are:

- one canonical record per real-world object, connected through explicit relationships
- local ownership and useful core operation without WAN access
- deterministic validation, data-quality controls, provenance and audit history
- multiple human and machine-readable views over the same records
- safe, reviewable write capabilities with explicit control over consequential changes
- maintainable, lightweight and preferably free/open-source technology

The longer-term destination includes operational workflows, automation, AI assistance and agent capabilities. AI is important, but it is a consumer of the platform rather than its organising principle. Human users, automation and AI should ultimately use the same platform capabilities and operate against the same canonical data, validation and safety boundaries.

Phase 1, the Information Platform foundation, is a complete development milestone. Phase 2's original local operational-time and deterministic-automation foundation is complete, and its expanded workspace remains active for focused refinements until Phase 3 is deliberately defined. Phase 2 remains human-first, database-first and AI-independent: Calendar/Event, Task, reminder, Inbox, scheduler and deterministic automation capabilities share validation, audit and provenance boundaries. AI, autonomous goal-directed workflows and autonomous external side effects remain later-phase capabilities; consequential mutations continue to require explicit user control. The [Phase 2 workspace](docs/phase_2_workspace.md) is the detailed status authority.

Project E currently serves one private user without authentication. Future trusted multi-user use is possible, but is not a current requirement; new design choices should avoid needlessly making it impossible.

See the [roadmap](ROADMAP.md) for phased guidance and [future direction](docs/future_direction.md) for the long-term architecture and Odysseus relationship.
