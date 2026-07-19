# Phase 2 Plan: Operational Time and Deterministic Automation

## Status, purpose and authority

**Phase 1 — Complete.** Pull request #1 is closed. Phase 1 closed as a development milestone after representative, rather than exhaustive, manual and automated verification. Later residual defects are ordinary maintenance work and do not reopen Phase 1 as a whole.

**Phase 2 — In progress.** Phase 2A implementation was authorised on **2026-07-19**. Completed implementation deliverables are shared temporal normalization; Calendar storage, management and lifecycle safeguards; canonical Event storage and lifecycle services; and standard Event relationship integration. Calendar-originated UI, Event search and related-entity projections, Week/Month projections and recurrence remain pending. Phase 2 becomes **Complete** only after the integrated completion review defined below; an isolated table, page, reminder, scheduled job or automation rule is not completion.

Phase 2 establishes Project E's operational time and deterministic-automation foundation:

```text
structured information → relationships → temporal information → Events
→ calendar projections → Tasks → reminders and attention management
→ scheduling → deterministic automation → later AI-assisted operations
```

The phase remains human-first, database-first, local-first and AI-independent. This document is the canonical Phase 2 scope, architectural direction, implementation sequence, completion standard and exclusion list. It does not itself authorise implementation.

## Enduring architectural principles

### Canonical records and shared platform boundaries

SQLite remains the canonical store. Phase 2 schema work must use migration-safe evolution, conservative dependencies and the existing application-service boundaries. Events and Tasks are canonical first-class peer entities with stable identity, editing, global search, cross-domain navigation, Timeline integration, history, provenance, audit, recent-record behaviour, appropriate duplicate handling, the standard relationship system and the normal recoverable entity lifecycle.

An **Event** represents something that occurs, occurred or is expected to occur. A **Task** represents work that should be performed. A Task is not an Event, and neither is a reminder. Connections among Events, Tasks, People, Organisations, Locations, Projects, Documents and Assets use normal Relationships; separate per-domain foreign keys or nested Event-Task types are not the default.

A **Project** is a peer entity and coordination hub, not the owner of its related records. It may gather Events, Tasks and other entities, but each related record remains independently canonical and may relate to no Project or more than one Project.

### Calendars, occurrences and projections

A **Calendar** is a first-class local Event grouping and configuration record. Every Event belongs to exactly one Calendar, which supplies a name, colour, IANA timezone, default Event duration, ordering, archive state and eventually a default reminder policy. Events remain canonical records; the Calendar does not become a second Event store. A fresh installation supplies one default General Calendar. Calendars alone provide Event grouping, management, filtering and colour; there is no separate Event classification layer.

A calendar view is a projection over canonical records and traceable derived occurrences:

- A **canonical record** is a durable source record such as an Event, Task, Person or Document.
- A **derived occurrence** is a deterministic temporal instance traceable to a canonical source and definition, such as this year's birthday derived from `Person.birth_date`.
- A **calendar projection** is the displayed time-based view of a canonical record or derived occurrence.

Displaying a Task deadline or session, birthday, anniversary, Document expiry, Project target, asset-maintenance date, scheduled Job Run or other system-generated occurrence does not convert it into an Event. Materialising a separate Event is permitted only when deliberately designed as a new canonical record with traceable source and provenance.

### Operational records remain semantically separate

A **reminder** is a policy attached to an Event, Task, derived occurrence or source-record policy. It is behaviour, not an independent domain entity. Delivery, acknowledgement, dismissal, snooze and failure history belong to notification or delivery records rather than the canonical reminder definition.

The operational record types are distinct:

```text
Reminder policy → may produce → actionable notification
Persistent issue → one durable current condition
Audit event → a historical fact
Job run → an execution attempt and result
Review item → a proposed consequential decision
```

These records may link to one another, but must not be flattened into one generic notification, history or job model.

### Idempotency, authority and portability

Logical occurrences, reminder deliveries, recovered notifications, persistent issues, escalations and job runs have stable identities. Database uniqueness constraints and atomic claims enforce deduplication; in-process coordination alone is insufficient. Each persistence contract must identify which material changes update an existing logical record and which create a new identity.

Deterministic automation uses the same validated application services as human interactions and retains normal provenance, audit and history. It may automatically recalculate derived state and create or update notifications, persistent issues, audit records and job-run records. Creating, editing, completing, archiving or deleting a canonical Event or Task requires explicit user approval; automation proposes such a mutation through an actionable review item.

Whole-platform export and import remain the portability boundary. Phase 2 canonical and operational records, their references and schema compatibility must be included in validation. Canonical Events and Tasks use the Recycle Bin lifecycle; derived occurrences, projections, notifications, delivery history, job runs and audit records are derived or historical records rather than Recycle Bin entities.

## Approved product behaviour

### Phase 2A — Temporal foundation

#### Events and Calendars

Events are broad, user-owned time records rather than only appointments or meetings. Intended uses include appointments, birthdays, transport, holidays, work, sleep and time blocking. An Event may be physical, remote, virtual, inferred, derived or not meaningfully tied to a place; Location is optional.

Users may create, rename, archive and order Calendars as local configuration records. An Event derives its colour from its Calendar. Users may temporarily show or hide Calendars as a view filter without mutating the Calendar or its Events. Event-specific colour overrides are not part of the model.

Calendar archival retains each assigned Event and its Calendar identity; it neither archives nor silently moves Events. Existing Events may remain assigned to and be edited without changing an archived Calendar, but archived Calendars cannot be selected for a new Event or a reassignment. Before archiving the default Calendar, a user must explicitly select another active Calendar as default. Calendar deletion is limited to empty, non-default Calendars, including no recycled Event assignments; no bulk reassignment operation is introduced in this milestone.

Human-created Events originate from the Calendar rather than the generic entity-create menu. The initial Calendar provides an **Add Event** action. The fast first layer of Event creation contains title, date and start/end entry, quietly applies the selected or default Calendar, and uses progressive disclosure for Calendar management, notes, relationships, reminders, recurrence and other facts. Relationships are added after creation through Event editing and the standard relationship system, not special People, Location or Project pickers in the initial form.

Every Event selects a Calendar and uses that Calendar's defaults. The default duration and Event timezone are overridable as approved; other default precedence remains unresolved below. The initial Calendar prioritises Week and Month views, starts weeks on Monday, and preserves Calendar context:

- Selecting an Event opens a compact preview with clear Edit and Delete actions.
- Editing opens in a Calendar overlay or panel rather than navigating immediately to a dedicated Event page.
- The timezone remains a compact, readily available creation and edit control rather than a hidden advanced field.
- Direct Week-view time-slot creation, drag-and-drop rescheduling and Event resizing follow only after the overlay-based create and edit workflow is stable.
- Day and agenda/list views follow only after the core Event workflow is stable.

The desktop baseline remains usable at 800 × 600. Phone responsiveness is deferred.

#### Temporal semantics

Phase 2 defines compatible temporal semantics and shared utilities before the full calendar. It does not require one universal temporal base table. Initial Events and Tasks record planned time only; actual start/end tracking is deferred.

A timed Event always has start and end instants. Point-in-time timed Events are not part of the initial model. An all-day Event uses date boundaries and may span multiple days. The user-facing all-day range is inclusive of its selected start and end dates; normalized temporal intervals and occurrence calculations are start-inclusive and end-exclusive. All-day values remain calendar dates rather than UTC instants.

Precise timed values are persisted in UTC. Calendars default to the IANA timezone `Australia/Brisbane` (UTC+10 without daylight saving), and an Event may select another IANA timezone when its originating local time matters. Calendar grids convert Events into the user's current display timezone, while Event details retain the originating timezone. The platform default must be capable of becoming user-configurable later without changing stored instants or existing record meaning.

The shared design covers instants and intervals, all-day values, planned time, deadlines, timezones and daylight-saving behaviour, recurrence, exact and approximate dates, cancellation and rescheduling. Cancellation, reinstatement and rescheduling use dedicated Event service operations while retaining the persisted Event status. An approximate date stores the user's closest known calendar date with an approximate marker; it is not a date range or partial year/month value.

#### Recurrence and lifecycle

Recurring Events retain one traceable series definition. Generated occurrences are deterministic projections, not unrelated duplicate Event records. The initial recurrence vocabulary is daily, weekly, monthly and yearly, with calendar-grade intervals, selected weekdays, ordinal weekdays and bounded date ranges.

Monthly and yearly recurrence uses the selected calendar day. If the 29th, 30th or 31st does not exist in a generated month or year, the occurrence shifts backward to the last valid day; the interface must warn about this behaviour when such a day is selected.

Recurrence is added or changed through Event editing after an ordinary Event exists. Series edits and deletion offer the scopes **this occurrence**, **this and following occurrences**, and **all occurrences**. Occurrence-specific changes use explicit exceptions; prospective changes use a traceable split rather than unrelated replacement Events. A recurrence-definition version change creates new future occurrence identities.

Cancellation, archival and deletion remain distinct:

- A cancelled Event remains historical and appears visibly muted or struck through, even when its scheduled time is in the future.
- Archival removes a no-longer-relevant Event from ordinary Calendar views while retaining it locally and recoverably.
- Permanent deletion is reserved for genuine errors and follows the existing confirmed, recovery-protected lifecycle.

These states remain distinct in persistence, Calendar projection and history. Event archival is independent from Recycle Bin deletion. Restoring a deleted Event preserves its prior archive and cancellation state.

Before the full Calendar is considered integrated, the Event foundation must demonstrate:

```text
create Event → relate it to multiple existing entities → find it in search
→ open it from related entity pages → inspect its history
```

### Phase 2B — Work management

A Task is a small but extensible canonical work record. It remains useful without a Project or Event and may relate independently to Events, Projects, People, Locations, Documents and Assets. Tasks connected to Events remain ordinary Tasks through normal Relationships.

Initial Tasks use one default Tasks list plus simple user-created lists. Users may create, rename and archive lists and move Tasks among them. A Task list is the user's intended category for Tasks, not a second classification layer. Nested lists, sharing, permissions and a separate workflow engine are deferred.

The initial Task lifecycle is **Open**, **Completed** and **Archived**. **In progress**, priority, richer workflow state, hierarchy, recurrence, dependencies and estimates are not initial requirements. Completed Tasks are hidden from the default Task view but remain available through a completed/history filter.

Task creation exposes title, Task list, planned date/time, deadline, relationships and notes directly. Human-created Tasks originate from the Calendar. The dedicated Tasks view organises and completes existing work rather than creating a competing generic path. The Inbox may offer a controlled conversion of an attention item into a Task.

A Task's deadline and planned work sessions are independent and optional. One Task may have multiple planned sessions; each appears as a separate Calendar block while remaining part of the same canonical Task. Events and Task sessions use distinct visual treatments, preserving Calendar-derived Event colours while making Tasks recognizable. Completing a Task removes its future planned blocks, retains past sessions as history, and marks those past blocks with a completed-check treatment.

An open Task that passes its deadline becomes visibly overdue and creates one deduplicated Inbox item. It remains overdue until completion, archival or a deadline change; age increases prominence without creating duplicate items.

Task lists define default reminder timings. An individual Task may remove, alter or add reminders without mutating its list defaults. Recurring Tasks are deferred; recurring work may use a recurring Event or time block until a distinct Task requirement is demonstrated.

Project pages may project upcoming Events, open Tasks, milestones, recent Documents, involved People, related Organisations, Locations, Assets and recent activity. These are coordinated views of peer records, not Project-owned children.

### Phase 2C — Reminder and attention foundation

#### Reminder policy and delivery

The reminder chain is:

```text
source fact → derived occurrence → applicable reminder default
→ optional record-level override → notification delivery
```

Global policies define defaults for source kinds such as birthdays, anniversaries and Document expiries. Calendars and Task lists provide approved context-specific defaults. Reminder resolution broadly proceeds from an occurrence override, to an Event override, to its Calendar policy, then to the applicable global policy. A record-level override supports **use default**, **enable with custom timing**, and **disable for this record**; for Events and Tasks it may remove, alter or add individual reminder timings without changing the applicable default policy. Events support multiple reminder configurations. Reminder storage and detailed resolution mechanics remain deferred to Phase 2C.

Deterministically recurring facts such as birthdays and expiries do not receive a new persistent reminder definition every year. Their occurrences remain traceable to the source fact and current policy.

A reminder timing or policy change creates a new pending delivery identity. Disabling a reminder suppresses pending delivery; re-enabling it delivers only if it is due under the current policy. Notification re-due state and other material changes follow their documented identity contracts.

Initial delivery creates a durable actionable local Inbox item. While Project E is open, the same item may also appear as an in-app popup; this is presentation of the local notification, not a separate delivery channel. An Event reminder popup provides **Open Event**, **Dismiss/Acknowledge**, and **View in inbox**. Email, SMS, external push and operating-system notifications are excluded.

At startup, when a reminder or job-triggered notice became due while the application was unavailable and no matching item exists, Project E creates one deduplicated recovered item retaining the original due time.

#### System Inbox

The Inbox is a dedicated operational attention screen, not a notification dropdown or social feed. It contains due reminders, overdue Tasks, approvals, imports needing review, data-quality decisions, actionable job failures, expiring Documents, suggested Tasks and one-off acknowledgement messages. A restrained global indicator and Home link may show the count of active, not-dismissed items, but the Inbox remains the canonical attention destination.

Each item persists until it is acknowledged, dismissed, snoozed, resolved or otherwise acted upon. It retains its source, reason for attention, original occurrence or due time, creation or delivery time, current state, relevant provenance and only the actions valid for its semantics. Actions may include **Open source**, **Review**, **Approve**, **Reject**, **Resolve**, **Acknowledge**, **Dismiss**, **Snooze**, and **Convert to Task**. Dismissing or snoozing a notification does not mutate its Event, Task, source fact or linked persistent issue.

The Inbox opens to one priority-ordered active feed with a separate Upcoming section. It groups and filters by meaningful item type and state, with source, severity and age filters where useful. Ordering is source-neutral and urgency-led: needs intervention, overdue, due now or soon, due today, upcoming, then informational; within a group the oldest due item appears first. Severity is used only where it changes ordering or treatment, and routine successful background work remains in activity or run history rather than active attention. The detailed severity vocabulary, review layout, transient-message and accessibility rules remain authoritative in [Operational Attention and Review](design/operational_attention_and_review.md).

Reminder snooze is limited to 30 minutes or until Project E next opens. Longer deferral uses conversion to a Task. Snooze retains the original due time and records the next-attention time.

Acted-on items leave the active feed for an Archived view containing the 1,000 most recent dismissed or acknowledged items. Older items move to immutable local deep archive rather than being deleted. Deep archive is not part of normal Inbox browsing; future retrieval may locate and export a copy without removing the retained original. Append-only audit history is unaffected by Inbox retention tiers.

#### Persistent System Health

A persistent issue is a durable condition such as an invalid storage path, unavailable optional service, missing reference data, disabled subsystem or continuously failed recurring job. System Health retains one current record per deduplication key and updates it as evidence, state or severity changes. An unchanged condition does not generate a new daily Inbox item.

Persistent conditions primarily live on a dedicated System Health screen, where the user may move or quarantine an issue. A reversible **Don't remind me** action suppresses further Inbox surfacing without deleting the condition or its history. A high-severity issue creates one regular Inbox item linking to its System Health record; lower-severity conditions remain in System Health unless escalation becomes necessary.

Create or update actionable attention when a condition is first detected, materially worsens, becomes actionable, changes state, resolves in a way worth acknowledging, or crosses a defined escalation threshold. Severity escalation creates a new logical escalation identity. Deduplication, suppression and escalation are required product behaviour.

Consequential review items show current and proposed state, evidence, consequences, reversibility and recovery before confirmation. Rejection records enough disposition to prevent useless resurfacing. Routine success stays in activity or process history.

### Phase 2D — Operational runtime

A scheduled job is executable background work, not an Event or reminder. Calendar views may optionally project scheduled or completed runs, but the job definition and each run retain their own identity and semantics.

Scheduled jobs use database-backed definitions and registered application handlers. A definition may include its handler, enabled state, schedule, next and last run times, status, retry count, timeout, failure reason, concurrency policy and approval requirements. Each execution attempt produces a persistent Job Run. Database rows never contain arbitrary executable Python or user-authored code.

The initial scheduler:

- runs in-process only while Project E is running;
- keeps schedules, registered handlers, locking and run history behind an application-runtime boundary suitable for a later local worker;
- calculates next runs and supports manual execution and enable/disable controls;
- records clean shutdown and startup when possible and retains a durable scheduler checkpoint;
- transactionally claims one active lease per job;
- records failures and expired leases for manual rerun, with no initial automatic retry;
- prevents duplicate runs and duplicate delivery through database identities and atomic claims.

Startup recovery evaluates work and reminder delivery due while Project E was unavailable. Recovery runs scheduled work serially, in scheduled order, one completed run at a time. Each registered job owns an explicit catch-up policy:

- an overdue one-off job runs once;
- reminder and maintenance scans coalesce into one current scan;
- high-frequency work skips stale intervals and runs once for the current interval;
- every missed occurrence runs only for an explicitly historical process.

Jobs may override the applicable default. Recovery remains deterministic and auditable after clean or unclean stops.

Job failures update run history and, where the condition persists, System Health. Intervention produces one appropriately escalated notification rather than repeated failure noise. The first scheduled maintenance checks beyond Event reminders and overdue Tasks remain unspecified; later design must define their record types, trigger conditions and lead times, derive attention from canonical records, and avoid duplicate Events.

This phase does not add a separate worker, service manager, application launch or termination control, external queue or distributed runtime.

### Phase 2E — Deterministic automation

The first automation layer uses explicit, deterministic rules:

```text
Trigger → optional conditions → action
```

The framework supports a deliberately small built-in set of triggers and registered actions. Rules may recalculate derived state; create or update notifications, persistent issues, audit events and Job Runs; identify an overdue Task; deliver a due reminder; update findings from a data-quality scan; or escalate a repeated failure once when intervention is required.

When a rule proposes creating, editing, completing, archiving or deleting a canonical Event or Task—for example, creating work in response to a Document expiry or Project target—it creates an actionable review proposal. Only explicit user approval applies the canonical mutation through the same validated service used by the human interface.

Every execution retains its trigger, conditions, registered action, source records, outcome, provenance and audit history. Automation does not bypass validation, relationships, lifecycle, idempotency or approval boundaries. AI-driven automation is deferred.

### Phase 2F — Stabilisation

Stabilisation integrates and verifies the preceding phases rather than adding an unrelated feature layer. It covers:

- cross-domain Calendar projections over canonical records and derived occurrences;
- recurrence definitions, occurrence identities, exceptions, series splits and timezone behaviour;
- data-quality rules for Events, Tasks, schedules and reminder policies;
- notification, escalation, issue and job-run deduplication under restart and recovery;
- whole-platform export/import of Phase 2 canonical and operational data;
- end-to-end workflow and migration testing;
- review of Inbox noise, persistent warnings, approval boundaries, provenance and audit;
- architecture, database, ontology, glossary, product and development documentation;
- the formal Phase 2 completion review.

## Implementation sequence

The behaviour above is authoritative. The following sequence establishes implementation order without redefining it.

### Phase 2A — Temporal foundation

1. **Complete:** update Phase 2 status and implementation documentation for authorised work.
2. **Complete:** define shared temporal semantics, persistence contracts and migration-safe schema evolution.
3. **Complete:** implement Calendar storage and management services: list/retrieve, validated creation and configuration, ordering, active-default selection, archive/unarchive, audit, provenance and append-only history.
4. **Complete:** implement Calendar lifecycle safeguards: archive retains Event assignments, archived Calendars cannot receive new assignments, no automatic reassignment occurs, and only empty non-default Calendars may be deleted.
5. **Complete:** implement canonical Event storage and validated lifecycle services, including timed/all-day normalization, cancellation, reinstatement, rescheduling and independent archive state.
6. Integrate Event Relationships with existing entity types.
7. Add Event search and related-entity projections.
8. Add Calendar preview and overlay-based Event creation and editing.
9. Build Week and Month Calendar projections over Events.
10. Add the approved recurrence definitions, generated occurrences, exceptions and series operations.

Before Week and Month projections, pass the Event integration checkpoint defined in Phase 2A.

### Phase 2B — Work management

8. Implement Tasks as first-class entities.
9. Add Task lists, Open/Completed/Archived lifecycle and completion behaviour.
10. Integrate Task Relationships with existing entity types.
11. Connect Tasks to Events and Projects through normal Relationships.
12. Add Task and Event projections to Project pages.
13. Add Task deadlines and one-or-more planned work sessions to Calendar projections.

### Phase 2C — Reminder and attention foundation

14. Define the approved reminder-policy contexts and preserve unresolved precedence explicitly.
15. Add record-level reminder overrides and material-change identity handling.
16. Add traceable derived occurrences for birthdays and expiries.
17. Implement local notification delivery, recovery and acknowledgement history.
18. Implement the actionable System Inbox and retention tiers.
19. Implement the separate persistent System Health surface.
20. Add database-enforced deduplication, suppression and escalation behaviour.

### Phase 2D — Operational runtime

21. Implement registered background-job handlers.
22. Implement database-backed schedules and per-job catch-up policies.
23. Add transactional leases, execution records and Job Run history.
24. Add checkpointed serial startup recovery and duplicate-run protection.
25. Add manual execution, manual failure rerun and enable/disable controls.
26. Integrate failures with System Health and actionable escalation.

### Phase 2E — Deterministic automation

27. Implement the trigger-condition-action framework.
28. Add a deliberately small set of built-in triggers and registered actions.
29. Route every action through normal platform services.
30. Add audit and provenance for inputs, decisions and outputs.
31. Add review and approval states for proposed canonical Event or Task mutations.

### Phase 2F — Stabilisation

32. Add approved cross-domain Calendar projections.
33. Verify recurrence, timezone and temporal-boundary behaviour.
34. Add data-quality rules for Events, Tasks, schedules and reminder policies.
35. Add migration, recovery, portability and end-to-end tests.
36. Review system noise, logical idempotency, Inbox deduplication and persistent warnings.
37. Update architecture, database, ontology, glossary, product and development documentation.
38. Conduct the Phase 2 completion review.

## Completion criteria

Phase 2 completes only when an end-to-end review can demonstrate:

```text
Create a Project
→ create an Event related to that Project
→ relate People and a Location to the Event
→ create preparation Tasks related to the Event and Project
→ display the Event, planned Task sessions and Task deadlines in Calendar views
→ create a recurring Event and trace its generated occurrence and exception to its series
→ generate a derived birthday or expiry occurrence from existing canonical data
→ apply an applicable reminder default and a record-level override
→ deliver one useful actionable local notification
→ recover a missed due item without duplicate delivery
→ avoid duplicate Inbox warnings for an unchanged persistent issue
→ run a scheduled background check and record its Job Run separately
→ update persistent System Health where necessary
→ escalate once when user intervention is required
→ present any proposed canonical Event or Task mutation for explicit approval
→ show generated records, decisions and actions in provenance and audit history
→ export and validate the integrated Phase 2 records through whole-platform portability
```

The review must also verify cancellation, archival and permanent deletion remain distinct; canonical records, derived occurrences and projections have not been conflated; and notifications, persistent issues, audit events and Job Runs retain separate identities.

An Event table, rendered Calendar, creatable Tasks, isolated reminder, one scheduler function or one runnable automation rule is insufficient. The capabilities must work together as one operational system.

## Explicit exclusions and staged follow-ups

The following are outside initial Phase 2 scope:

- AI agents, AI-generated autonomous actions, forwarding Inbox items to an AI agent, chat or goal-directed agent workflows.
- Automatic creation, editing, completion, archival or deletion of canonical Events or Tasks without explicit user approval.
- Autonomous external side effects.
- A visual workflow canvas, arbitrary user-authored executable scripts or executable code stored in the database.
- A separate worker, service manager, application launch/termination control, distributed execution, external queue, Redis, Celery or Temporal.
- External Calendar synchronisation, email ingestion, email delivery, SMS, external push and operating-system notifications.
- Replacement of the existing Relationship system, special nested Event-Task types or Project ownership of related records.
- A requirement that every dated record become an Event or that projections become canonical duplicates.
- Actual start/end tracking for initial Events or Tasks.
- Point-in-time timed Events without a bounded end.
- Initial Task priority, In progress state, estimates, hierarchy, dependencies, recurring Tasks, nested lists, sharing, permissions or a separate workflow engine.
- Phone/mobile support.
- Day and agenda/list Calendar views before the Week/Month workflow is stable.
- Direct Week-view slot creation, drag-and-drop rescheduling and Event resizing before overlay creation and editing are stable.
- Unspecified scheduled maintenance checks beyond Event reminders and overdue Tasks; those require later design within the existing Phase 2 boundaries.
- A normal browsing or removal program for immutable deep Inbox archive storage.
- Repeated Inbox items for unchanged persistent issues or routine successful background work.

These exclusions do not remove the documented within-phase follow-ups from the implementation order; they prevent them from being treated as prerequisites for earlier foundations or as authority for unrelated work.

## Preserved ambiguities and decision history

The user-facing Calendar, Event, Task, reminder, Inbox, System Health and archive behaviour was approved on **2026-07-12**. The accepted architectural refinements on **2026-07-19** added explicit Calendars, planned-time-only initial records, bounded timed Events, database-enforced logical idempotency, non-consequential automation, serial recovery, per-job catch-up policies and manual failure rerun. Both decision sets are preserved here.

The following interactions remain deliberately unresolved and must be settled through authorised design work rather than inferred during implementation:

- **Detailed reminder resolution.** The broad precedence is occurrence override, Event override, Calendar policy, then global policy. Storage, merging behaviour, identity changes and conflict resolution remain deferred to Phase 2C.
- **Calendar-originated undated Tasks.** Human-created Tasks originate from the Calendar, while planned sessions and deadlines are optional. The entry interaction for a Task with neither has not been defined.
- **Later scheduled maintenance.** Checks beyond Event reminders and overdue Tasks, including their source records, trigger conditions and lead times, remain unspecified.
- **Detailed implementation mechanics.** Table shapes, route paths, service names, recurrence encoding, exception schema, archive retrieval mechanics and UI details beyond those stated here remain implementation-design work.

The following are deliberate distinctions rather than contradictions:

- An Event can conceptually represent something at a point or over an interval, while the initial timed Event model requires a bounded start and end.
- An all-day range is inclusive in user-facing date selection while normalized interval persistence and occurrence calculations are start-inclusive and end-exclusive.
- The in-app popup is an additional presentation of the same durable local notification, not a separate external delivery channel.
