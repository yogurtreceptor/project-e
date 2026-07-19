# Phase 2 Plan: Operational Time and Deterministic Automation

## Status and purpose

**Phase 1 — Complete.** Pull request #1 is closed. Phase 1 closed as a development milestone after representative, rather than exhaustive, manual and automated verification. Later residual defects are ordinary maintenance work and do not reopen Phase 1 as a whole.

**Phase 2 — Planned.** Planned work is not delivered work. When authorised implementation begins, status becomes **Phase 2 — In progress**. **Phase 2 — Complete** is reserved for the completion review described below; a table, page, isolated reminder or one running job is not completion.

Phase 2 adds Project E's operational time and automation foundation, progressing from structured information and relationships through temporal information, Events, calendar projections, Tasks, reminders and attention management, scheduling, deterministic automation, and only later AI-assisted operations. It remains human-first, database-first, local-first and AI-independent. AI is not part of the initial Phase 2 implementation.

This plan is the canonical Phase 2 scope and architectural direction. It does not itself authorise implementation.

## Planning decisions

### 2026-07-12 — Broad Event model and desktop baseline

- Events will start as a broad, user-owned model for time-based life and operational records, rather than being limited to appointments or meetings. Initial intended uses include appointments, birthdays, transport, holidays, work, sleep and time blocking.
- Event categories are useful for organising those different uses and should be part of the Phase 2A design work. Categories must not create separate Event storage models or weaken the standard relationship, audit and lifecycle behaviour.
- Categories will not be a hard-coded application list. Fresh installations provide one general/default category; users create, rename, archive and organise their own additional categories through local reference data.
- Each user-managed Event category has a Calendar colour. Events inherit their category colour by default.
- Calendar users can temporarily show or hide individual categories. This is a view filter only and does not change, archive or otherwise mutate the category or its Events.
- Selecting an Event from the Calendar opens a compact preview first, with clear Edit and Delete actions, rather than navigating immediately to a full Event detail page.
- Event editing opens in a Calendar overlay or panel, preserving Calendar context rather than navigating to a dedicated Event page.
- Week-view drag-and-drop rescheduling and Event resizing are planned follow-up interactions, implemented only after the overlay-based create and edit workflow is stable.
- The initial Event form prioritises a fast first layer containing only title, date, and start/end entry. The default category is applied quietly; category management, notes, relationships, reminders, recurrence and other facts belong in progressive disclosure.
- All-day is an explicit Event option. It supports date-only records such as birthdays and holidays, including blocking out days; timed Events remain available for appointments and time blocks.
- All-day Events support an inclusive start-to-end date range from the initial implementation, allowing one canonical Event to represent a multi-day holiday or block.
- Recurring Events require Google Calendar-style deletion scope: delete this occurrence, this and following occurrences, or all occurrences. The implementation must retain one traceable series definition and explicit exception/split records rather than materialising unrelated duplicate Event records.
- Recurrence is progressive disclosure: users create an ordinary Event first and add or alter recurrence through Edit. Series edits use the same scope as deletion—this occurrence, this and following occurrences, or all occurrences.
- Cancellation is distinct from removal. A cancelled Event remains a historical record and is visibly muted or struck through, including when its scheduled time is still in the future. Archiving removes a no-longer-relevant Event from ordinary calendar views while retaining it locally and recoverably; permanent deletion is reserved for genuine errors. These states must remain distinct in data model, calendar projection and history.
- Relationships are added after Event creation through the Event edit workflow and the standard relationship system; the initial create form does not contain special People, Location or Project pickers.
- Reminder policies are defined per user-managed Event category, including the general/default category. Each Event starts from its category defaults but may remove, alter or add individual reminder timings; an Event-level configuration therefore overrides rather than mutates the category policy.
- Initial reminder delivery creates a durable actionable inbox item and, while the application is open, a visible in-app popup with a route to the full inbox context. External push, SMS and email are future delivery channels and are not part of the initial local implementation.
- The in-app reminder popup provides Open Event, Dismiss/Acknowledge and View in inbox actions. The inbox may later provide richer controlled actions such as creating or moving work into a Task list. Forwarding an item to an AI agent for action is explicitly deferred beyond Phase 2, pending the later authority and review model.
- The initial Calendar prioritises Week and Month views. Day and agenda/list views are deferred until the core Event workflow is stable.
- Human-created Events originate from the Calendar rather than a generic global/entity-create menu. The initial Calendar provides an Add Event action; direct Week-view time-slot selection that prefills the form is a later enhancement. Future deterministic rules may create Events only through the same validated platform-service boundary.
- Calendar weeks begin on Monday.
- Events should support multiple reminder configurations appropriate to their category and purpose; reminder delivery remains part of the later Phase 2C attention work rather than an implicit first Event implementation.
- Desktop visual testing has found the current interface acceptable down to 800 x 600. Phone responsiveness remains deliberately deferred; this does not alter the existing desktop-first scope.

## Core model

### Events are first-class entities

An **Event** represents something that occurs, occurred or is expected to occur at a point in time or over an interval: a social gathering, meeting, appointment, work shift, study session, sleep, travel, maintenance activity, milestone, deadline or system-generated temporal occurrence. It has stable identity and participates in global search, edit and audit history, recycle-bin lifecycle, recently viewed records, duplicate handling where appropriate, entity relationships, cross-domain navigation and timeline integration.

An Event may be remote, virtual, inferred, derived or not meaningfully tied to a physical place; Location is optional. Events connect to People, Organisations, Locations, Projects, Documents, Assets and Tasks through the standard relationship system—for example, a Person attends or organises an Event, an Organisation hosts it, an Event occurs at a Location or relates to a Project, a Document supports it, an Asset is used during it, and a Task prepares for or follows it. Do not add separate foreign-key fields for every related domain unless a documented integrity or performance reason requires one.

### Tasks are first-class entities

A **Task** represents work that should be performed. It is neither an Event nor a reminder. A Task may have one or more planned work sessions, a deadline and a completion date. It can independently relate to Projects, Events, People, Assets, Documents and Locations, and must be useful without a Project or Event. Tasks connected to Events remain ordinary Task entities through normal relationships; there is no separate nested event-task type. Priority, richer workflow state, hierarchy, recurrence and dependencies are future extensions, not initial Task requirements.

Planning direction: the initial Task model is deliberately small but extensible. Tasks stand alone as canonical work records, may have optional planned start/end time or a deadline, and project onto Calendar without becoming duplicate Events. Richer hierarchy, recurrence, dependencies and workflow complexity are deferred until concrete use establishes their value.
Initial Tasks use one default Tasks list plus simple user-created lists. List behaviour is limited to create, rename, archive and move Task; nested lists, sharing, permissions and a separate workflow engine are deferred.
The initial Task lifecycle is Open, Completed and Archived only. An In progress state is deliberately deferred.
Task creation exposes title, Task list, planned date/time, deadline, relationships and notes directly; priority is not included. Here Task list is the user’s intended meaning of category, not a second classification layer.
Human-created Tasks originate from the Calendar. The Inbox may later create a Task from an attention item; the dedicated Tasks view organises and completes existing work rather than providing a competing generic creation path.
A Task’s deadline and planned work sessions are independent and optional. One Task may have multiple planned sessions; each session appears as its own Calendar block while remaining part of the same canonical Task. Completing a Task removes its future planned blocks and retains past sessions as history. An open Task that passes its deadline becomes visibly overdue and creates one deduplicated inbox item; it stays overdue until completion, archival or deadline change.
Task lists define default reminder timings. Individual Tasks may remove, alter or add reminders without changing their Task-list defaults. Completed Tasks are hidden from the default Task view but retained in a completed/history filter. Recurring Tasks are deliberately deferred: recurring work may instead be represented by a recurring Event/time block until a distinct Task need is demonstrated.

### Projects coordinate; they do not own

A Project is a peer entity and a coordination hub, not a hierarchical owner of related records. A Project may gather Events, Tasks, People, Organisations, Locations, Documents, Assets, milestones and activity history. A related record can have no Project or more than one Project. Future Project pages should project upcoming Events, open Tasks, milestones, recent Documents, involved People, related Organisations, Locations, Assets and recent activity without making those records children owned by the Project.

### Calendar is a projection, not a source of truth

The Calendar displays time-based information from canonical records and must not maintain an independent duplicate event store. Its first projection primarily displays Events. Later it may display Task deadlines or starts, Project targets, Document expiries, birthdays, anniversaries, asset-maintenance dates, scheduled job runs and system-generated occurrences; those remain their original record types.

- A **canonical record** is the durable source record, such as an Event, Task, Person or Document.
- A **derived occurrence** is a deterministic time occurrence traceable to a canonical source and definition, such as this year's birthday from `Person.birth_date`.
- A **calendar projection** is a displayed time-based view of a canonical record or derived occurrence.

Displaying a record on a calendar never converts it into an Event unless the product deliberately materialises a separately traceable derived Event.
Events and planned Task sessions share Calendar space but use distinct visual treatments so users can recognise appointments or other happenings versus planned work at a glance. Event category colours remain meaningful; Task blocks are visually identifiable as Tasks.
Past Calendar sessions of a completed Task remain visible as history and show a clear completed-check treatment.

## Shared temporal semantics

Phase 2 starts by defining consistent time semantics and shared utilities before building the full calendar. The model must consider `starts_at`, `ends_at`, `all_day`, `timezone`, `status`, `planned_start`, `planned_end`, `actual_start`, `actual_end`, `due_at`, `completed_at`, `recurrence`, approximate or uncertain time, and source. It need not force every domain into one universal temporal base table; the immediate requirement is compatible semantics and shared utilities so Events, Tasks, schedules and derived occurrences do not invent incompatible date logic.

Precise timed values are persisted in UTC. Calendar display and new timed Events default to the user’s current timezone; the initial operating baseline is `Australia/Brisbane` (UTC+10 without daylight saving), with Monday as the first day of the calendar week. Timed Events retain an IANA event timezone where a different local zone is material, preventing ambiguity for travel and cross-zone appointments. Calendar grids show each Event converted into the user’s current timezone (for example, 10:00 Perth displays as 12:00 in Brisbane), while Event details retain the originating timezone. The timezone is a compact, readily available control on both Event creation and edit screens, rather than an Add details field. The platform default must be designed to become user-configurable later without changing stored instants or the meaning of existing records. All-day date ranges remain calendar dates rather than UTC instants.

The design must explicitly define point-in-time Events, intervals, all-day Events, planned versus actual time, deadlines, time zones, recurring definitions, generated recurrence occurrences, daylight-saving behaviour, approximate or partly known dates, cancellation and rescheduling. Recurrence initially supports only daily, weekly, monthly and yearly rules. Monthly and yearly rules use the selected calendar day. Selecting the 29th, 30th or 31st must warn that a shorter month or year period shifts the generated occurrence backward to its last valid day: 31st to 30th, then 29th, then 28th as required. Generated occurrences remain traceable to their definition and source; they are not duplicate canonical Event records. The first implementation does not attempt every recurrence edge case.

## Reminders, notifications and attention

A **reminder** is an attention or notification rule attached to another record or produced by a global policy. It is not an independent first-class domain entity, Event or Task. Events and Tasks may each have one or more reminder configurations, while other source entities may produce reminder-capable derived occurrences.

Global reminder policies define category defaults: for example, seven days before birthdays, thirty days before document expiry, one day before Task deadlines, or no anniversary reminders. Entity-level overrides support **use global default**, **enable with custom timing** and **disable reminders for this record**. The required chain is:

```text
underlying fact → derived occurrence → reminder policy → optional entity override → notification delivery
Person.birth_date → yearly birthday occurrence → global birthday policy → person override → delivery
```

Avoid creating a new persistent reminder definition every year where the result can be deterministically derived from the source fact and current policy. Persistent delivery records are appropriate for delivery history, acknowledgement, snoozing, failure handling and audit; they are notification or delivery records, not the canonical reminder definition. Initial delivery creates actionable local inbox items and, while the application is open, an in-app popup linked to the inbox item; email, SMS, external push and operating-system notifications are excluded.

The actionable **system inbox** contains attention items: due reminders, overdue Tasks, approvals, imports needing review, data-quality decisions, failing background jobs, expiring Documents, suggested Tasks and one-off acknowledgement messages. Actions may include open source, acknowledge, dismiss, snooze, convert to Task, resolve, approve and reject. An item persists until it is dismissed, resolved, acknowledged or otherwise acted upon, retaining its creation timestamp and original due time. At startup, if a reminder or job-triggered notice became due while the application was unavailable and no matching item exists, the platform creates one deduplicated recovered item that retains that original due time.
The Inbox is a dedicated attention screen rather than a notification dropdown. It groups and filters items by type, including reminders, overdue Tasks, approvals and system-related items.
The Inbox opens to one priority-ordered active feed, with a separate Upcoming section for attention that is not yet due.
Inbox ordering is source-neutral and urgency-led: needs intervention, overdue, due now or soon, due today, upcoming, then informational. Within each group, the oldest due item appears first. Overdue work gains prominence with age but does not generate duplicate items.
Reminder snooze is deliberately short: 30 minutes or until Project E next opens. For a longer deferral, the Inbox offers conversion into a Task rather than arbitrary long snoozes.
Acted-on Inbox items leave the main feed for an Archived view. The Inbox retains the 1,000 most recent dismissed or acknowledged items in that view to keep attention history useful without unbounded growth.
Older Inbox items move to a deeper local archive rather than being deleted. The 1,000-item Archived view is a convenient recent-history layer; append-only audit history remains intact regardless of Inbox retention tier.
Deep archive storage is immutable local retention, analogous to microfiche. A future archive-retrieval program may locate and export a copy without removing the original from deep storage; it is not part of normal Inbox browsing.

The inbox is distinct from **persistent system health** (also called active issues, configuration issues, active warnings or operational status). A disabled optional subsystem, invalid storage path, unavailable service, missing reference data or continuously failed recurring job is a durable condition with one current record whose state changes. It is not a new daily inbox item. Create or update one actionable item when first detected, severity materially increases, action becomes necessary, state changes, it resolves, or a defined escalation threshold is reached. Deduplication and suppression are mandatory to prevent system noise.
Persistent conditions primarily live on a dedicated System Health screen rather than becoming routine Inbox traffic. A user may move or quarantine an issue there; a reversible Don’t remind me action suppresses further Inbox surfacing without deleting the condition or its history.
A high-severity system problem creates one regular Inbox item with a direct link to its System Health record; lower-severity conditions remain in System Health unless escalation is required.

```text
Notification: something happened or needs attention.
Persistent issue: a condition remains true.
Audit event: a historical fact occurred.
Job run: an execution attempt and its result.
```

These records remain separate and each retains appropriate audit and provenance.

## Scheduler and deterministic automation

A **scheduled job** is executable background work, not a Calendar Event and not a reminder. Its model may include a registered `handler`, enabled state, schedule, `next_run_at`, `last_run_at`, status, retry count, timeout, failure reason, concurrency policy, execution history and approval requirements. Calendar views may project scheduled or completed runs, but do not store jobs as Events.

The initial scheduler is lightweight and suitable for the local single-user application: it runs in-process while the application is running and evaluates recovery on startup. It provides database-backed schedules, registered job handlers, next-run calculation, persistent run history, failure recording, startup recovery, duplicate-run and duplicate-delivery protection, manual execution and enable/disable controls. Schedules, handlers, run history and locking sit behind an application-runtime boundary so a later local worker can execute the same contract independently. Phase 2 does not add that worker, a service manager, an external queue, or application launch/termination behaviour. Handlers refer to registered platform capabilities, for example `system.run_data_quality_scan`; arbitrary executable Python must never be stored in the database. Temporal, Celery, Redis and distributed queues are not required.
Startup recovery is an explicit catch-up procedure: it evaluates work and reminder deliveries that should have occurred while Project E was closed, then creates the required deduplicated Inbox items with their original due times.
The first scheduled maintenance checks beyond Event reminders and overdue Tasks remain deliberately unspecified. Their record types, trigger conditions and lead times will be configured through later design work; all such checks must derive attention from canonical records and must not create duplicate Events.

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
5. Add Event search, related-entity projections, Calendar preview and overlay-edit workflows.
6. Build calendar projections over Events.
7. Add basic recurrence support.

Before the full calendar, verify: create an Event → connect it to multiple existing entities → find it through search → open it from related entity pages → inspect its history.

### Phase 2B — Work management

8. Implement Tasks as first-class entities.
9. Add Task list, Open/Completed/Archived lifecycle and completion behaviour.
10. Integrate Task relationships.
11. Connect Tasks to Events and Projects through normal relationships.
12. Add Task and Event projections to Project pages.
13. Add Task deadlines and one-or-more planned work sessions to Calendar projections.

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
