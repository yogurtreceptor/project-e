# Phase 2 Plan: Operational Time and Deterministic Automation

## Status and purpose

**Phase 1 — Complete.** Pull request #1 is closed. Phase 1 closed as a development milestone after representative, rather than exhaustive, manual and automated verification. Later residual defects are ordinary maintenance work and do not reopen Phase 1 as a whole.

**Phase 2 — Planned.** Planned work is not delivered work. When authorised implementation begins, status becomes **Phase 2 — In progress**. **Phase 2 — Complete** is reserved for the completion review described below; a table, page, isolated reminder or one running job is not completion.

Phase 2 adds Project E's operational time and automation foundation, progressing from structured information and relationships through temporal information, Events, calendar projections, Tasks, reminders and attention management, scheduling, deterministic automation, and only later AI-assisted operations. It remains human-first, database-first, local-first and AI-independent. AI is not part of the initial Phase 2 implementation.

This plan is the canonical Phase 2 scope and architectural direction. It does not itself authorise implementation.

## Core model

### Events are first-class entities

An **Event** represents something that occurs, occurred or is expected to occur at a point in time or over an interval: a social gathering, meeting, appointment, work shift, study session, sleep, travel, maintenance activity, milestone, deadline or system-generated temporal occurrence. It has stable identity and participates in global search, edit and audit history, recycle-bin lifecycle, recently viewed records, duplicate handling where appropriate, entity relationships, cross-domain navigation and timeline integration.

An Event may be remote, virtual, inferred, derived or not meaningfully tied to a physical place; Location is optional. Events connect to People, Organisations, Locations, Projects, Documents, Assets and Tasks through the standard relationship system—for example, a Person attends or organises an Event, an Organisation hosts it, an Event occurs at a Location or relates to a Project, a Document supports it, an Asset is used during it, and a Task prepares for or follows it. Do not add separate foreign-key fields for every related domain unless a documented integrity or performance reason requires one.

### Tasks are first-class entities

A **Task** represents work that should be performed. It is neither an Event nor a reminder. A Task may have planned start and deadline dates, estimated duration, completion date, priority, workflow state and parent/child relationships. It can independently relate to Projects, Events, People, Assets, Documents and Locations, and must be useful without a Project or Event. Tasks connected to Events remain ordinary Task entities through normal relationships; there is no separate nested event-task type.

### Projects coordinate; they do not own

A Project is a peer entity and a coordination hub, not a hierarchical owner of related records. A Project may gather Events, Tasks, People, Organisations, Locations, Documents, Assets, milestones and activity history. A related record can have no Project or more than one Project. Future Project pages should project upcoming Events, open Tasks, milestones, recent Documents, involved People, related Organisations, Locations, Assets and recent activity without making those records children owned by the Project.

### Calendar is a projection, not a source of truth

The Calendar displays time-based information from canonical records and must not maintain an independent duplicate event store. Its first projection primarily displays Events. Later it may display Task deadlines or starts, Project targets, Document expiries, birthdays, anniversaries, asset-maintenance dates, scheduled job runs and system-generated occurrences; those remain their original record types.

- A **canonical record** is the durable source record, such as an Event, Task, Person or Document.
- A **derived occurrence** is a deterministic time occurrence traceable to a canonical source and definition, such as this year's birthday from `Person.birth_date`.
- A **calendar projection** is a displayed time-based view of a canonical record or derived occurrence.

Displaying a record on a calendar never converts it into an Event unless the product deliberately materialises a separately traceable derived Event.

## Shared temporal semantics

Phase 2 starts by defining consistent time semantics and shared utilities before building the full calendar. The model must consider `starts_at`, `ends_at`, `all_day`, `timezone`, `status`, `planned_start`, `planned_end`, `actual_start`, `actual_end`, `due_at`, `completed_at`, `recurrence`, approximate or uncertain time, and source. It need not force every domain into one universal temporal base table; the immediate requirement is compatible semantics and shared utilities so Events, Tasks, schedules and derived occurrences do not invent incompatible date logic.

The design must explicitly define point-in-time Events, intervals, all-day Events, planned versus actual time, deadlines, time zones, recurring definitions, generated recurrence occurrences, daylight-saving behaviour, approximate or partly known dates, cancellation and rescheduling. Recurrence initially supports a constrained daily, weekly, monthly and yearly subset. Generated occurrences remain traceable to their definition and source; the first implementation does not attempt every recurrence edge case.

## Reminders, notifications and attention

A **reminder** is an attention or notification rule attached to another record or produced by a global policy. It is not an independent first-class domain entity, Event or Task. Events and Tasks may each have one or more reminder configurations, while other source entities may produce reminder-capable derived occurrences.

Global reminder policies define category defaults: for example, seven days before birthdays, thirty days before document expiry, one day before Task deadlines, or no anniversary reminders. Entity-level overrides support **use global default**, **enable with custom timing** and **disable reminders for this record**. The required chain is:

```text
underlying fact → derived occurrence → reminder policy → optional entity override → notification delivery
Person.birth_date → yearly birthday occurrence → global birthday policy → person override → delivery
```

Avoid creating a new persistent reminder definition every year where the result can be deterministically derived from the source fact and current policy. Persistent delivery records are appropriate for delivery history, acknowledgement, snoozing, failure handling and audit; they are notification or delivery records, not the canonical reminder definition.

The actionable **system inbox** contains attention items: due reminders, overdue Tasks, approvals, imports needing review, data-quality decisions, failing background jobs, expiring Documents, suggested Tasks and one-off acknowledgement messages. Actions may include open source, acknowledge, dismiss, snooze, convert to Task, resolve, approve and reject.

The inbox is distinct from **persistent system health** (also called active issues, configuration issues, active warnings or operational status). A disabled optional subsystem, invalid storage path, unavailable service, missing reference data or continuously failed recurring job is a durable condition with one current record whose state changes. It is not a new daily inbox item. Create or update one actionable item when first detected, severity materially increases, action becomes necessary, state changes, it resolves, or a defined escalation threshold is reached. Deduplication and suppression are mandatory to prevent system noise.

```text
Notification: something happened or needs attention.
Persistent issue: a condition remains true.
Audit event: a historical fact occurred.
Job run: an execution attempt and its result.
```

These records remain separate and each retains appropriate audit and provenance.

## Scheduler and deterministic automation

A **scheduled job** is executable background work, not a Calendar Event and not a reminder. Its model may include a registered `handler`, enabled state, schedule, `next_run_at`, `last_run_at`, status, retry count, timeout, failure reason, concurrency policy, execution history and approval requirements. Calendar views may project scheduled or completed runs, but do not store jobs as Events.

The initial scheduler is lightweight and suitable for the local single-user application: database-backed schedules, registered job handlers, next-run calculation, persistent run history, failure recording, startup recovery, duplicate-run protection, manual execution and enable/disable controls. Handlers refer to registered platform capabilities, for example `system.run_data_quality_scan`; arbitrary executable Python must never be stored in the database. Temporal, Celery, Redis and distributed queues are not required.

The first automation layer uses explicit deterministic rules:

```text
Trigger → optional conditions → action
```

Examples include a deadline updating overdue state and creating one actionable inbox item; an Event entering its reminder interval; a Document expiry producing a policy-defined notification or Task; a Project target approaching creating a review Task; a quality scan updating persistent issues and surfacing only actionable findings; and repeated job failure escalating once when intervention is required. Automation calls the same application services as the human interface and never bypasses validation, history, provenance or audit. AI-driven automation is deferred. Consequential actions retain human approval states where automatic execution is not appropriate.

## Implementation sequence

### Phase 2A — Temporal foundation

1. Update project status and Phase 2 documentation.
2. Define shared temporal semantics.
3. Implement Events as first-class entities.
4. Integrate Event relationships with existing entity types.
5. Add Event list, detail, search and entity-page projections.
6. Build calendar projections over Events.
7. Add basic recurrence support.

Before the full calendar, verify: create an Event → connect it to multiple existing entities → find it through search → open it from related entity pages → inspect its history.

### Phase 2B — Work management

8. Implement Tasks as first-class entities.
9. Add Task status, priority and completion behaviour.
10. Integrate Task relationships.
11. Connect Tasks to Events and Projects through normal relationships.
12. Add Task and Event projections to Project pages.
13. Add Task deadlines and start dates to calendar projections.

### Phase 2C — Reminder and attention foundation

14. Define global reminder policies.
15. Add entity-level reminder overrides.
16. Add derived occurrences for birthdays and expiries.
17. Implement notification delivery and acknowledgement history.
18. Implement the actionable system inbox.
19. Implement separate persistent system-health or active-issues surface.
20. Add deduplication, suppression and escalation behaviour.

### Phase 2D — Operational runtime

21. Implement registered background jobs.
22. Implement database-backed schedules.
23. Add execution and run history.
24. Add startup recovery and duplicate-run protection.
25. Add manual execution and enable/disable controls.
26. Integrate failures with system health and actionable escalation.

### Phase 2E — Deterministic automation

27. Implement the trigger-condition-action framework.
28. Add a deliberately small set of built-in triggers and actions.
29. Ensure automations use normal platform services.
30. Add audit and provenance for decisions and outputs.
31. Add human approval states where an action should not execute automatically.

### Phase 2F — Stabilisation

32. Add cross-domain calendar projections.
33. Verify recurrence and timezone behaviour.
34. Add data-quality rules for Events, Tasks, schedules and reminder policies.
35. Add end-to-end tests.
36. Review system noise, inbox deduplication and persistent warnings.
37. Update architecture, user and development documentation.
38. Conduct the Phase 2 completion review.

## Completion criteria

Phase 2 completes only when an end-to-end review can demonstrate:

```text
Create a Project
→ create an Event related to that Project
→ relate People and a Location to the Event
→ create preparation Tasks related to the Event and Project
→ display the Event and Task deadlines in calendar views
→ generate a derived birthday or expiry occurrence from existing entity data
→ apply a global reminder policy and entity-level override
→ deliver a useful actionable notification
→ avoid duplicate inbox warnings for an unchanged persistent issue
→ run a scheduled background check and record its outcome
→ update persistent system health where necessary
→ escalate once when user intervention is required
→ show generated records and actions in audit history
```

An Event table, a rendered calendar, creatable Tasks, isolated reminders, one scheduler function or one runnable automation rule is insufficient. The capabilities must work together as one operational system.

## Explicit exclusions

- No AI agents or AI-generated autonomous actions.
- No visual workflow canvas or arbitrary user-authored executable scripts.
- No distributed job execution, Redis or Temporal requirement.
- No external calendar synchronisation initially.
- No email ingestion, SMS or external push delivery initially.
- No replacement of the existing relationship system.
- No requirement that every dated record become an Event.
- No recurring duplicate inbox items for unchanged persistent warnings.
