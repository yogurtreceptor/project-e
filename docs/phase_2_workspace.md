# Phase 2: Operational Time and Deterministic Automation

## Status and authority

**Complete.** The owner accepted the delivered experience and authorised closure on 2026-08-03. This is a completed development milestone, not a stable-release claim; residual defects remain ordinary maintenance.

This document records the delivered boundary, closure evidence and exclusions. Current mechanics belong in [Architecture](architecture.md) and [Database Design](database_design.md); meaning belongs in [Ontology](ontology.md); rationale belongs in [Architecture Decisions](../ARCHITECTURE_DECISIONS.md). The [Build History](build_log.md) and Git retain delivery chronology.

The experimental Task subsystem was retired after the local database was verified to contain no Task records or linked operational data. ADR-027 and migration `20260801_31_retire_task_subsystem` preserve the safety decision. Future work management requires a fresh authorised design.

## Delivered contract

### Events, Calendars and time

- Event is a canonical entity with Search/Timeline participation, ordinary Relationships, audit/provenance/history and recoverable lifecycle. Human-created Events originate in Calendar workflows rather than a generic Event index/form.
- Every Event belongs to one local Calendar. Calendars alone own Event grouping, colour, timezone, default duration, ordering, archive state and reminder defaults. General is the ordinary default; protected Birthdays contains Person-synchronised yearly Events.
- Timed Events store bounded UTC instants plus originating IANA timezone; all-day Events store start and exclusive end dates. `Australia/Brisbane` is the platform default.
- Cancellation, archive, Recycle Bin deletion/restoration and permanent deletion remain distinct.
- Daily, weekly, monthly and yearly recurrence supports intervals, weekday/ordinal choices and date/count endings. Derived occurrences retain source identity; one-occurrence edits use exceptions and this-and-following changes use traceable series splits.

### Calendar experience

- Month, Monday-first Week and Day are deterministic projections with Calendar visibility filters, ISO/date context and accessible scrollable grids. Week/Day show a live current-time marker.
- The Calendar sidebar provides Create event, Mini Month and independently grouped My/Other calendars. Browser-session context preserves view, date and visibility through Event and Settings workflows.
- Quick create is a draggable/dockable non-modal panel with essential fields, provisional display and a More-options handoff to the full form.
- Calendar Settings uses a focused context-preserving shell. Local Calendar creation is deliberately minimal; editing owns complete applicable configuration and lifecycle.
- The supported baseline is desktop, including the constrained 800×600 Calendar view. Phone/mobile workflows remain excluded.

### Occurrences, reminders and Inbox

One provider boundary adapts Event schedules, protected Birthday Events, cached external Calendar items and Document expiries into stable temporal occurrences. Source records retain ownership of their dates; Calendar display and reminders do not require duplicate Events.

- Reminder policy belongs to Calendars/sources/occurrences, not a standalone entity. Inheritance, override, suppression and disable behaviour resolve to at most ten effective timings.
- Delivery identity is repeat-safe and lifecycle-aware. One active/snoozed Inbox item exists per source occurrence and reason; later due timings replace older visible attention while history remains.
- Inbox is a chronological active queue with exact source actions, fixed ten-minute snooze, semantic navigation count and separate Archive/deep history.
- Event attention resolves on exact-occurrence opening, occurrence end or relevant lifecycle/schedule change. Document-expiry attention remains until dismissal or material source/lifecycle change.
- Reminder policy, Inbox item/action, audit event, Job Run and Automation Run retain distinct identities.

### Local runtime and automation

- Registered Jobs run serially while the application is open. SQLite stores schedules, catch-up policy, leases, checkpoints and append-only Runs. Startup recovery reactivates due snoozes and performs one coalesced due scan; database identity prevents duplicate work.
- Manual execution and failed-run rerun are auditable without shifting the normal schedule.
- Automation Rules select application-registered trigger/action names only; SQLite contains no executable user code. Automation Runs are idempotent per stable trigger identity.
- The sole current automation evaluates reminders through ordinary services. It cannot create, edit, archive or delete a canonical Event. Consequential automation requires separate authorisation and review design.

### iCalendar and external sources

- File import parses and previews bounded supported iCalendar semantics before explicit confirmation; unsupported meaning that cannot be preserved blocks apply. Confirmation creates canonical local Calendar/Event/recurrence records through normal services; stable UID/fingerprint identity makes unchanged repeat import a no-op and prevents silent overwrite.
- Selected export is all-or-nothing ZIP interoperability, with one valid `.ics` member per selected local or cached external source. Unsupported semantics block rather than being lost.
- Other calendars are public-HTTPS read-only sources with independent settings and last-known-good operational cache. Preview rejects unsafe/private destinations, credentials and redirects and enforces size/time limits; potentially sensitive query values stay out of routine logs/audit notes. Refresh validates completely before atomic replacement; failure retains known items and exposes stale/error state.
- Cached external items are not canonical Events: they are uneditable, gain no Relationships/history/Recycle Bin lifecycle and have Calendar-level rather than item-level reminder configuration.
- Whole-platform portability preserves relevant canonical and operational state; Calendar `.ics` export is not backup.

## Delivery and closure evidence

Phase 2 delivered temporal foundations; Event/Calendar lifecycle; Month/Week/Day; recurrence/exceptions; reminder/Inbox; registered scheduler/automation; iCalendar import/export; external Calendar sources; Task retirement; runtime/style compartmentalisation; and integrated portability, audit and migration coverage.

`tests/test_phase_2_closeout.py` repeats the central fictional workflow: related recurring Event and exception; Birthday recurrence; Calendar/Event reminder precedence; one deduplicated Inbox delivery; startup recovery and automation; separate operational identities; distinct Event lifecycle states; and a whole-platform export/import round trip.

Closure evidence passed all 287 tests, compilation, migration/runtime checks and representative desktop review across Calendar, Settings, Inbox, Jobs and Automation at 800×600, 1440×900 and 1920×1080 in both themes. The accepted constrained-Calendar Search accessible-name limitation remains in the technical-debt register.

The owner accepted the delivered experience, Task-free boundary, live debt as non-blocking and deferral list below. Publication/merge remained a separate repository action.

## Explicit exclusions

Phase 2 did not deliver or authorise:

- AI/agent/chat workflows, arbitrary executable automation, autonomous external effects or automatic canonical Event mutation;
- external workers/queues, service-manager control, email/SMS/push/OS notifications, authenticated Calendar APIs, CalDAV, two-way sync or write-back;
- Persistent System Health, general approvals/escalation or a current Task/to-do domain;
- mobile workflows, Agenda/Year views, direct grid creation, drag-reschedule/Event resizing or per-Event iCalendar export;
- converting every dated record into an Event, actual start/end tracking or unbounded timed Events;
- destructive automatic Inbox retention or unspecified recurring maintenance.

New occurrence sources join the shared provider boundary. New Jobs require explicit source, schedule, logical identity and catch-up semantics. Consequential automation requires separately authorised review, validation, provenance, audit and recovery.
