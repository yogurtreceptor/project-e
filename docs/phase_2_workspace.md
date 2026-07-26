# Phase 2 Workspace: Operational Time and Deterministic Automation

## Status, purpose and authority

**Phase 1 — Complete.** Pull request #1 is closed. Phase 1 closed as a development milestone after representative, rather than exhaustive, manual and automated verification. Later residual defects are ordinary maintenance work and do not reopen Phase 1 as a whole.

**Phase 2 — Event-focused and active.** Calendar and Event work, reminder delivery and recovery, scheduled Job Runs, registered deterministic automation, portability and data-quality coverage remain active. The previously delivered Task work-management implementation is retained but dormant pending a later, user-led to-do design; it has no normal routes, navigation, search, Calendar projection, Inbox delivery or automation interaction. This workspace remains the living record for Phase 2 refinements and hardening until Phase 3 is deliberately defined. Persistent System Health remains deferred; neither the original closeout nor this workspace authorises it.

> **Task-work-management deferral (2026-07-26).** Historical Task requirements and delivery entries below record the work that was completed before this decision; they are not current user-facing behaviour. Existing Task records, migrations, services and validation remain preserved for future reconsideration, rather than being deleted or moved into an archive directory.

Phase 2 establishes Project E's operational time and deterministic-automation foundation:

```text
structured information → relationships → temporal information → Events
→ calendar projections → Tasks → reminders and attention management
→ scheduling → deterministic automation → later AI-assisted operations
```

The phase remains human-first, database-first, local-first and AI-independent. This document is the canonical Phase 2 scope, architectural direction, implementation sequence, completion standard and exclusion list. The expansion section records delivered refinement work; implementation still requires an explicit user prompt.

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

Human-created Events originate from the Calendar rather than a generic entity-create menu. The Calendar provides a compact **Create event** control that opens an in-calendar quick-create panel with the essential scheduling fields, close control, direct save action and **More options** handoff. The panel is non-modal, draggable by its title bar and dockable into the sidebar; an unsaved Event is rendered provisionally in the active Calendar projection as its schedule changes. Calendar creation preserves the current Month, Week or Day view, anchor date and visible-Calendar filter through quick creation, More options, and full Event creation. The browser session retains that Calendar context for Calendar navigation, and Event preview edit/delete flows return to it after completion or cancellation; this is a local presentation preference rather than stored user data. More options carries every entered quick-create value into the existing dedicated full form. Event free text is presented as a progressive **Description** control that expands only when selected and grows with its content; storage remains the existing canonical notes field. The Event full form contains title, Calendar, all-day choice, either an inclusive date range or timed start/end datetimes, timezone and description; it selects the default Calendar and applies its default duration and timezone for a new form. Existing Events open a dedicated editing form from their Calendar preview. Relationships are added after creation or from Event editing through the standard relationship system, not special People, Location or Project pickers in the initial form. Calendar management, reminders, recurrence and other facts remain outside this first form.

#### Calendar refinement delivery record

The active Phase 2 expansion workspace records the following delivered Calendar refinements in detail so later consolidation does not lose their interaction contracts:

- The Calendar has one clearly labelled top-level **Create event** control; it does not duplicate Event creation in the toolbar.
- Event creation opens a compact quick-create panel in the Calendar rather than changing page. The panel has close, save and More options controls; More options serialises currently entered values into the complete form.
- Quick-create panels do not dim the Calendar, can be repositioned by dragging their title bar and may dock into the sidebar, temporarily replacing sidebar navigation without overflowing its width.
- While an Event is unsaved, the Calendar renders it as a distinct provisional projection. Timed previews use their actual duration, clip or continue across visible days, and render the typed title; the preview disappears when the panel closes.
- Event and Task free text is named **Description** in the interface. It begins as an unobtrusive trigger and expands to a one-line textarea when selected, then grows with the entered content. The underlying canonical `notes` persistence field is unchanged.
- The browser session remembers the last explicit Calendar Month, Week or Day context, including anchor date and visible Calendar filter. Calendar navigation restores it. Creation, More options, Event preview edit, cancellation, save and deletion preserve the originating context through validated Calendar-only return targets.

Every Event selects a Calendar and uses that Calendar's defaults. The default duration and Event timezone are overridable as approved; other default precedence remains unresolved below. The initial Calendar provides Month, Week and Day views, starts weeks on Monday, and preserves Calendar context:

- Selecting an Event opens a compact preview with clear Edit and Delete actions.
- Editing opens in a dedicated Calendar Event form rather than the generic read-only Event projection.
- The timezone remains a compact, readily available creation and edit control rather than a hidden advanced field.
- Week and Day views render timed Event intervals as duration blocks against an hourly grid, clipping an overnight Event into each affected display day while retaining its visible start/end time.
- Direct Week-view time-slot creation, drag-and-drop rescheduling and Event resizing follow only after the overlay-based create and edit workflow is stable.
- Agenda/list views follow only after the core Event workflow is stable.

The desktop baseline remains usable at 800 × 600. Phone responsiveness is deferred. A later visual-design review may use familiar Google Calendar interaction and layout patterns as reference, but must not alter the local-first Calendar, Event or Relationship model. That review is deferred until current functional workflows are confirmed.

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

Initial Tasks use one default Tasks list plus simple user-created lists. Users may create, rename and archive lists and move Tasks among them. Archiving a list retains its assigned Tasks but prevents new assignment; list deletion is deferred. A Task list is the user's intended category for Tasks, not a second classification layer. Nested lists, sharing, permissions and a separate workflow engine are deferred.

The initial Task lifecycle is **Open**, **Completed** and **Archived**. **In progress**, priority, richer workflow state, hierarchy, recurrence, dependencies and estimates are not initial requirements. Completed Tasks are hidden from the default Task view but remain available through a completed/history filter.

Human-created Tasks originate from the Calendar. The first capture form exposes title, Task list and notes, and deliberately supports an undated Task with no separate capture route. It routes relationship work through the standard post-creation Relationship workflow. A subsequent 2B temporal milestone will expose optional planned sessions and deadline fields in that same form. The dedicated Tasks view organises, moves, archives and completes existing work rather than creating a competing generic path. The Inbox may offer a controlled conversion of an attention item into a Task. A later capture refinement will prefill a new Task's all-day deadline to three calendar days after capture; a newly added timed session uses a one-hour duration unless the user changes it.

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

Global policies define defaults for the initial derived source kinds: birthdays and Document expiries. Anniversaries are deferred. Calendars and Task lists provide approved context-specific defaults. Reminder resolution broadly proceeds from an occurrence override, to an Event override, to its Calendar policy, then to the applicable global policy. The Event notification creator starts from its linked Calendar defaults: no Event-specific rows preserves that inheritance, added rows add timings, and suppression rows remove selected inherited timings. Coincident timings produce one delivery. Existing disabled override persistence remains respected for compatibility, but the current creator does not expose a separate policy-state picker. Initial Task reminders apply to deadlines only, not planned sessions.

Reminder edits on a recurring Event use the established scopes **this event only**, **this event and future recurring events**, and **all instances of this event**. The first scope creates an occurrence-specific reminder exception; the second uses the existing traceable prospective-series split; the third changes the series policy. These edits affect pending and future deliveries only: historical Event occurrences and reminder deliveries are never rewritten or newly delivered.

**Recurring reminder contract.** A this-occurrence edit persists a reminder override against that generated occurrence's stable series/occurrence identity; it does not edit the canonical Event or another occurrence with the same date-like display value. A this-and-following edit first creates the normal traceable series split, then applies the amended reminder policy to the successor series. The predecessor retains its prior policy through its final occurrence, and the successor has its own future occurrence and delivery identities. An all-occurrences edit changes the policy of the current series definition, preserving the identities and delivery history of already occurred instances. In every scope, only pending deliveries for the affected future occurrence identities are recalculated; unaffected pending deliveries remain valid, while acknowledged, dismissed and resolved history is retained unchanged.

The initial default reminder timings are relative to the source's due instant or all-day 09:00 local-time anchor. Calendar and record settings use repeatable positive-integer and unit controls, never a comma-separated text field. A Calendar can configure at most ten default notifications, and an Event can resolve to at most ten effective notifications after Calendar defaults, additions and suppressions are combined:

- Events: 1 hour and 10 minutes before.
- Task deadlines: 3 days, 2 days, 1 day, 6 hours and 1 hour before.
- Birthdays: 1 calendar month, 2 weeks, 1 week, 3 days, 1 day and 12 hours before.
- Document expiries: 1 calendar month, 2 weeks, 1 week, 3 days and 1 day before.

All all-day reminder sources use 09:00 in the configured platform timezone as their due-time anchor rather than midnight. The platform timezone defaults to `Australia/Brisbane` (UTC+10) until a user configuration setting is introduced; that future setting must preserve existing reminder meaning. Calendar-month offsets retain calendar semantics rather than being treated as a fixed number of days.

**Catch-up policy.** Reminder evaluation classifies sources as transient occurrences, persistent conditions or recurring dates. Events are transient: a delivery is created only while the Event remains upcoming; a past Event is not backfilled. Open Task deadlines and active Document expiries are persistent conditions: after their due anchor, normal pending reminder deliveries resolve and one durable overdue item remains until the condition changes or its source lifecycle suppresses it. Birthdays are recurring dates: past annual occurrences are not backfilled, and evaluation considers the next occurrence only. Phase 2D startup recovery applies these same rules.

Deterministically recurring facts such as birthdays and expiries do not receive a new persistent reminder definition every year. Their occurrences remain traceable to the source fact and current policy. Birthdays and Document expiries project as all-day derived occurrences, not canonical Event records. A 29 February birthday follows the established month-end backward-shift rule and occurs on 28 February in a non-leap year. Approximate dates do not generate reminders in this milestone; a later design may introduce narrowly defined, explainable circumstances for them.

**Delivery identity and material-change contract.** A delivery identity contains its source kind and stable source identifier, stable logical occurrence identity, due anchor instant, reminder timing, and reason. Identical inputs must reuse one delivery across repeated evaluation. A material change creates a new future pending identity only for an affected delivery: changing its due anchor through rescheduling or a recurrence change; adding or changing an applicable timing; or changing the applicable policy for that future occurrence. When a material change supersedes a due anchor or removes a timing, its active or snoozed pending delivery is resolved as superseded; unchanged timings and unaffected occurrences retain their current deliveries. Disabling a reminder resolves its active or snoozed pending deliveries and suppresses future delivery. Re-enabling evaluates only the current policy and creates a delivery only when it is due. Snooze changes the next-attention time of the same delivery identity. Acknowledging or dismissing retains historical identity and prevents redelivery unless a later material change produces a distinct identity. Refreshing, rendering, opening an Inbox item, or an otherwise immaterial source edit never changes delivery identity or redelivers an item. Startup recovery creates a missed delivery only when its logical pending delivery remains eligible and no matching active or historical delivery already exists.

Initial delivery creates a durable actionable local Inbox item. While Project E is open, the same item may also appear as an in-app popup; this is presentation of the local notification, not a separate delivery channel. An Event reminder popup provides **Open Event**, **Dismiss/Acknowledge**, and **View in inbox**. Email, SMS, external push and operating-system notifications are excluded.

Phase 2C establishes the reminder-resolution and delivery boundary without a background scan or general scheduler. Phase 2D invokes that boundary while Project E is running and at startup; when a reminder or job-triggered notice became due while the application was unavailable and no matching item exists, it creates one deduplicated recovered item retaining the original due time.

#### System Inbox

The Inbox is a dedicated operational attention screen, not a notification dropdown or social feed. It contains due reminders, overdue Tasks, approvals, imports needing review, data-quality decisions, actionable job failures, expiring Documents, suggested Tasks and one-off acknowledgement messages. A restrained global indicator and Home link may show the count of active, not-dismissed items, but the Inbox remains the canonical attention destination.

Each item persists until it is acknowledged, dismissed, snoozed, resolved or otherwise acted upon. It retains its source, reason for attention, original occurrence or due time, creation or delivery time, current state, relevant provenance and only the actions valid for its semantics. Actions may include **Open source**, **Review**, **Approve**, **Reject**, **Resolve**, **Acknowledge**, **Dismiss**, **Snooze**, and **Convert to Task**. Dismissing or snoozing a notification does not mutate its Event, Task, source fact or linked persistent issue.

When a source no longer has the relevant due condition—for example an Event is cancelled, archived or recycled; a Task is completed, archived or recycled; or a Person or Document is recycled—future reminder deliveries are suppressed and any active reminder notification is resolved. Historical dismissed and acknowledged deliveries remain retained. Changing a deadline or expiry date produces new pending deliveries under the changed due time and resolves active reminder attention for the superseded due condition.

The Inbox opens to one priority-ordered active feed with a separate Upcoming section. It groups and filters by meaningful item type and state, with source, severity and age filters where useful. Ordering is source-neutral and urgency-led: needs intervention, overdue, due now or soon, due today, upcoming, then informational; within a group the oldest due item appears first. Severity is used only where it changes ordering or treatment, and routine successful background work remains in activity or run history rather than active attention. The detailed severity vocabulary, review layout, transient-message and accessibility rules remain authoritative in [Operational Attention and Review](design/operational_attention_and_review.md).

Reminder snooze is limited to 30 minutes or until Project E next opens. Longer deferral uses conversion to a Task. Snooze retains the original due time and records the next-attention time.

Acted-on items leave the active feed for an Archived view containing the 500 most recent items. The user may select 10, 50 or 100 items per page, producing respectively 50, 10 or 5 pages over that same retained set. A visible Deep archive control follows the 500th item and opens a prototype long-scroll view of all older retained Inbox history. No Inbox record is deleted or removed by this retention presentation, and append-only audit history is unaffected. More capable deep-archive retrieval and presentation remain later work.

#### Persistent System Health (deferred)

Persistent System Health is deferred from Phase 2C and Phase 2D. It should be introduced only after concrete condition producers and user actions are separately designed; the reminder and scheduler foundations must not add speculative health checks, a generic issue surface or escalation behaviour merely to fill that future role.

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

Job failures update Job Run history for manual inspection and rerun. Persistent System Health and escalation remain deferred. The first scheduled maintenance checks beyond Event reminders and overdue Tasks remain unspecified; later design must define their record types, trigger conditions and lead times, derive attention from canonical records, and avoid duplicate Events.

This phase does not add a separate worker, service manager, application launch or termination control, external queue or distributed runtime.

### Phase 2E — Deterministic automation

The first automation layer uses explicit, deterministic rules:

```text
Trigger → optional conditions → action
```

The framework supports a deliberately small built-in set of triggers and registered actions. Rules may recalculate derived state; create or update notifications, audit events and Job Runs; identify an overdue Task; deliver a due reminder; or update findings from a data-quality scan. Persistent issues and escalation remain deferred.

When a rule proposes creating, editing, completing, archiving or deleting a canonical Event or Task—for example, creating work in response to a Document expiry or Project target—it creates an actionable review proposal. Only explicit user approval applies the canonical mutation through the same validated service used by the human interface.

Every execution retains its trigger, conditions, registered action, source records, outcome, provenance and audit history. Automation does not bypass validation, relationships, lifecycle, idempotency or approval boundaries. AI-driven automation is deferred.

### Phase 2F — Stabilisation

Stabilisation integrates and verifies the preceding phases rather than adding an unrelated feature layer. It covers:

- cross-domain Calendar projections over canonical records and derived occurrences;
- recurrence definitions, occurrence identities, exceptions, series splits and timezone behaviour;
- data-quality rules for Events, Tasks, schedules and reminder policies;
- notification and job-run deduplication under restart and recovery;
- whole-platform export/import of Phase 2 canonical and operational data;
- end-to-end workflow and migration testing;
- review of Inbox noise, approval boundaries, provenance and audit;
- architecture, database, ontology, glossary, product and development documentation;
- the formal Phase 2 completion review.

## Implementation sequence

The behaviour above is authoritative product direction. The following sequence is the delivery record and implementation order: its **Complete** markers report implemented work, do not redefine the approved behaviour, and must remain aligned with the current architecture and database documentation. Numbering restarts within each Phase 2 subphase.

### Phase 2A — Temporal foundation

1. **Complete:** update Phase 2 status and implementation documentation for authorised work.
2. **Complete:** define shared temporal semantics, persistence contracts and migration-safe schema evolution.
3. **Complete:** implement Calendar storage and management services: list/retrieve, validated creation and configuration, ordering, active-default selection, archive/unarchive, audit, provenance and append-only history.
4. **Complete:** implement Calendar lifecycle safeguards: archive retains Event assignments, archived Calendars cannot receive new assignments, no automatic reassignment occurs, and only empty non-default Calendars may be deleted.
5. **Complete:** implement canonical Event storage and validated lifecycle services, including timed/all-day normalization, cancellation, reinstatement, rescheduling and independent archive state.
6. **Complete:** integrate Event Relationships with existing entity types.
7. **Complete:** add Event search and read-only related-entity projections. Events are searchable by their canonical title/notes and relationship context, can be filtered as Events, and open from Search or existing related-record links into a read-only projection with Calendar-derived colour, temporal/lifecycle facts, relationships and change history. This deliberately does not provide generic Event browsing, creation or editing.
8. **Complete:** add Calendar-originated Event creation and editing. The `/calendar` workflow provides dedicated forms with Calendar defaults, all-day and timed scheduling, readily available timezone, notes, post-creation relationship entry, and edit/reschedule actions routed through the existing Event services. The Calendar projection remains an Event-free overview and preview surface.
9. **Complete:** build Month, Monday-first Week and Day Calendar projections over canonical Events. Week and Day convert timed Event instants into the active default Calendar timezone and render their occupied duration on an hourly grid, including a clipped continuation block for overnight spans; Month retains a compact interval overview. All views retain all-day date boundaries, display Calendar-derived colour and cancelled treatment, and support non-mutating visible-Calendar filters. Selecting an Event opens a compact Calendar preview with Edit and confirmed Recycle Bin Delete actions.
10. **Complete:** add the approved recurrence definitions, generated occurrences, exceptions and series operations through Event editing. Recurrence definitions, versioned deterministic daily/weekly/monthly/yearly projection, bounded end dates, month-end backward shifting, selected-weekday and ordinal-weekday controls, persisted cancellation and override exceptions, and traceable successor-series splits are implemented. Calendar previews carry occurrence identity into the Event editor and deletion workflow, which offer **this occurrence**, **this and following**, and **all occurrences** scopes. Scoped recurrence mutations record Event history, audit and provenance.

**Complete:** the Event integration checkpoint defined in Phase 2A now passes: Events can be created and edited from the Calendar, projected in Month, Week and Day views, related to multiple peers, found through Search, opened from related-record contexts, and inspected with their history. Recurrence scopes and Calendar management complete the remaining Phase 2A functional requirements.

### Phase 2B — Work management

1. **Complete:** implement canonical Tasks and Task lists with migration-safe storage, a seeded default Tasks list, active-list assignment validation, list creation/rename/archive/default selection, standard Entity identity, Search, Recycle Bin, audit and provenance integration.
2. **Complete:** add Open/Completed/Archived Task lifecycle behaviour. Completion records a timestamp; completed Tasks are hidden from the default Task view and may be reopened. Task archive remains distinct from Recycle Bin deletion.
3. **Complete:** integrate pair-aware Task Relationships with every current peer entity, including Events, Projects and other Tasks, through the standard Relationship lifecycle.
4. **Complete:** add Calendar-originated undated Task creation and a dedicated Task organisation/read-only record view. This milestone intentionally does not add a generic Task CRUD route or a second capture path.
5. **Complete:** implement optional Task deadline persistence: a date-only all-day deadline or a local date/time plus IANA timezone. Deadlines remain separate from Calendar occupancy.
6. **Complete:** implement repeatable optional planned sessions, each all-day or a bounded timed interval using the shared temporal contract, with Calendar deadline/session projections. Completing a Task permanently removes its future sessions while retaining past session history; Task sessions remain neutral rather than Calendar-coloured.
7. **Complete:** add read-only Project-page projections for related upcoming Events and open Tasks. Projects coordinate peer records through normal Relationships and do not own them.

### Phase 2C — Reminder and attention foundation

1. **Complete:** define local Calendar, Task-list and global derived-source reminder-policy contexts, default timings, record and occurrence overrides, and the delivery identity/material-change contract.
2. **Complete:** add record-level Event and Task-deadline overrides with additive custom timings, inherited-timing suppression and disable behaviour. Recurring Event edits use this-occurrence, this-and-following and all-occurrences scopes through the existing occurrence and series-split model.
3. **Complete:** add traceable all-day birthday and Document-expiry reminder occurrences, including Brisbane anchors, calendar-month timing, February-29 backward shifting and approximate-date exclusion.
4. **Complete:** implement durable local notification persistence, manual reminder evaluation and append-only Inbox delivery/action history. Phase 2D adds scheduled delivery and startup recovery.
5. **Complete:** implement the actionable System Inbox: active attention, derived Upcoming preview, acknowledge/dismiss/snooze actions, urgency ordering, the 500-item paged Archive tier and distinct deep-history view.
6. **Complete:** add database-enforced reminder and Inbox-delivery deduplication, timing-aware material-change reconciliation, lifecycle suppression and snooze reactivation. The recovery-matching identity contract is defined here; Phase 2D invokes it during startup recovery.
7. **Complete:** defer persistent System Health, issue suppression and escalation until concrete condition producers and actions are authorised.

**Complete:** Phase 2C now provides the local reminder and attention foundation. Its deterministic catch-up policy treats Events as transient occurrences, overdue Tasks and Document expiries as persistent conditions, and birthdays as next-occurrence-only recurring dates. Phase 2D is responsible for invoking this completed delivery boundary while Project E is running and during startup recovery.

### Phase 2D — Operational runtime

21. **Complete:** implement registered background-job handlers. The initial registered handler is the application-owned `reminder-delivery` scan; no database row can contain executable user-authored code.
22. **Complete:** implement database-backed schedules and per-job catch-up policies. The initial enabled job runs once per minute and uses the approved coalesced catch-up policy; no speculative disabled jobs are seeded.
23. **Complete:** add transactional leases, execution records and Job Run history. An expiring active lease is recorded as an expired Run, while ordinary handler failure is retained as a failed Run without automatic retry.
24. **Complete:** add checkpointed serial startup recovery and duplicate-run protection. Startup reactivates next-open snoozes, runs one coalesced reminder scan when due, and records a durable startup checkpoint. The normal in-process loop continues only while Project E is open.
25. **Complete:** add System Tools controls for manual execution, manual failure rerun and enable/disable. A manual or rerun attempt is a distinct auditable Job Run and does not move the regular schedule.
26. **Complete:** record failures in Job Run history; persistent System Health and actionable escalation remain deferred pending separately authorised condition design.

### Phase 2E — Deterministic automation

27. **Complete:** implement the database-backed trigger-condition-action framework with registered names only and durable idempotent logical runs.
28. **Complete:** add the small built-in `reminder_scan` trigger with due-reminder delivery, overdue-Task attention, and an opt-in Document-expiry Task-proposal action.
29. **Complete:** route actions through the existing reminder and Task application services; no rule contains executable user-authored code.
30. **Complete:** record rule inputs, outcomes, source evidence, audit records and automation provenance.
31. **Complete:** add pending/approved/rejected review proposals. Approving a proposed Task invokes the standard validated Task service; rejection is durable and cannot later be approved.

### Phase 2F — Stabilisation

32. **Complete:** add Calendar projections for Task deadlines/sessions, birthdays, Document expiries and Project target dates without converting any source into an Event.
33. **Complete:** retain focused recurrence, timezone, all-day-boundary and leap-day tests across the integrated Calendar/reminder workflow.
34. **Complete:** add data-quality checks for stored Event and Task temporal contracts, reminder-policy timing payloads, and registered schedule configuration.
35. **Complete:** cover the forward migration, scheduler recovery, operational export/import validation and end-to-end service boundaries with tests.
36. **Complete:** review system noise and logical idempotency. Overdue Task attention and reminder delivery use separate stable identities; routine successful Job/automation work remains historical. No concrete persistent-issue producer or escalation action was authorised, so System Health remains deferred.
37. **Complete:** update architecture, database, ontology, glossary, product, roadmap and development documentation.
38. **Complete:** conduct and record the Phase 2 completion review.

### Phase 2 expansion workspace

1. **Complete (2026-07-26):** defer Task work management while retaining its migration-safe storage and service implementation for later redesign. Task navigation and direct routes now return no user-facing Task workflow; Tasks are excluded from Calendar creation and projections, global Search, Project projections, Inbox reminder delivery and registered automation. Existing Task-related operational records are retained but hidden, preserving data without letting the dormant feature affect Event-focused Phase 2 work.

2. **Complete (2026-07-25):** replace free-text timezone entry in Calendar, Event, Task deadline and Task-session forms with a local collapsed IANA combobox. It visibly defaults to `Australia/Brisbane`; opening or editing it reveals a searchable, scrollable list with current UTC offsets and country names from the installed timezone database. Searches match country, place, IANA identifier and offset text. Stored values remain validated IANA identifiers, so existing UTC instants and record meaning are unchanged.

2. **Complete (2026-07-25):** add the protected built-in `Birthdays` Calendar. A Person with a birthday owns one linked, canonical, yearly recurring all-day Event in that Calendar; changing the Person name or birthday synchronises that same Event, while deleting/restoring the Person archives/restores it. Birthdays remain a Calendar category rather than a derived event type. Its reminder defaults live in Birthdays Calendar settings; the former global birthday policy migrates there without discarding configured timings.

3. **Complete (2026-07-25):** refine Calendar management with compact circular colour controls and Calendar-level local notification defaults.

4. **Complete (2026-07-25):** place Calendar default notifications on the Calendar edit form alongside colour and default Event duration. Replace comma-separated timing entry and policy-state pickers with repeatable integer-and-unit notification rows and a local Add notification control. Empty Event-specific rows inherit the linked Calendar defaults. Calendar defaults and effective Event reminder sets are capped at ten; persistence remains canonical validated timing-token JSON rather than free-form comma-separated text.

5. **Complete (2026-07-26):** replace the Calendar's separate Add Event and Add Task controls with one **Create** menu. The menu visibly indicates that it expands and contains Event and Task choices while retaining the existing canonical creation routes.

6. **Complete (2026-07-26):** add in-Calendar Event and Task quick-create panels. The panels provide the essential scheduling or deadline fields, close control, direct save action and **More options** handoff. More options serialises the entered quick-create values into the existing complete form; quick save continues to invoke the same validated Event and Task services.

7. **Complete (2026-07-26):** refine quick-create panels into non-modal Calendar overlays. Opening a panel does not dim the Calendar. It can be dragged by its title bar, docked into the sidebar to temporarily replace navigation, undocked again, and closed without retaining a draft. Docked headings, controls and fields remain constrained to the sidebar width.

8. **Complete (2026-07-26):** render a provisional unsaved Event in the active Calendar projection while Event quick-create is open. The provisional projection updates with the typed title and scheduling inputs, uses the actual timed duration, and clips or continues across visible days. It is purely client-side presentation and does not materialise an Event or alter canonical records before save.

9. **Complete (2026-07-26):** rename Event and Task free text from Notes to **Description** in their creation, editing and read-only presentation. The control starts as a compact Description trigger, expands only on selection, and grows with its entered text. Persistence remains the existing canonical `notes` field, so no migration or duplicate source of truth is introduced.

10. **Complete (2026-07-26):** preserve Calendar navigation context. The browser session remembers an explicit Month, Week or Day view together with anchor date and visible-Calendar filter. Calendar navigation restores that context. Quick create, More options, full Event creation, Event preview edit, cancel, save and delete use validated Calendar-only return targets so they return to the originating projection; this is session-local presentation state, not a user preference stored in SQLite.

11. **Complete (2026-07-26):** add the recurrence picker to the full Calendar Event create and edit forms, while keeping it out of the compact quick-create overlay. Its button menu starts at **Does not repeat** and creates deterministic daily, anchor-weekday weekly, anchor-ordinal-weekday monthly, annual-date and Monday–Friday rules. A fourth weekday offers both fourth and last-monthly patterns; a fifth weekday offers last-monthly only. **Custom** opens a local recurrence editor with bounded interval, day/week/month/year selection, selectable weekdays, and Never/on-date/after-occurrence endings. Its monthly menu derives its choices from the Event date: **on day X of the month**, the corresponding **first/second/third/fourth weekday** where applicable, and **last weekday** when the Event is the last such weekday in its month. “After” resolves to the deterministic final occurrence date without adding a second persistence model. Annual 29 February repeats retain the established 28 February non-leap-year behaviour. Editing or deleting a generated recurring occurrence defers the **This event**, **This and following**, or **All events** decision until Save or Delete is pressed. The dialog uses a selectable left-aligned scope list with Cancel and OK actions.

12. **Complete (2026-07-26):** consolidate the Calendar Month, Week and Day controls into one dropdown labelled with the active view and a visible down arrow. Its menu marks the current projection and retains the Calendar anchor date and visible-Calendar filter when switching views.

13. **Complete (2026-07-26):** reserve the Calendar projection's left sidebar for Calendar-specific controls by rendering it empty while retaining its width, surface and quick-create docking target. The shared Browse sidebar remains unchanged on other pages.

14. **Complete (2026-07-26):** add a compact, fixed-height Mini Month Day Picker as the first Calendar-sidebar control, with Create Event directly above it. The Monday-first six-row grid includes ISO week numbers and adjacent-month dates; selected and current dates are visually distinct. Previous/next changes only the picker month; selecting a day changes the canonical Calendar anchor date. All navigation preserves the active Calendar view and filters.

15. **Complete (2026-07-26):** establish the Calendar sidebar's Event-focused information architecture: Create event, Mini Month, **My calendars** and an honest visual-only **Other calendars** section. My calendars contains the protected Birthdays Calendar, General and user-created Calendars; Other calendars reserves the presentation and visibility pattern for future supplied, imported or derived sources without introducing source configuration, external dependencies or a second Event store.

16. **Complete (2026-07-26):** refine Calendar projection density for the supported desktop targets. Month bounds each day cell and links an overflow count to that day's Calendar view; Week and Day retain their complete 24-hour grid inside a height-bounded, horizontally and vertically scrollable region with sticky day and all-day orientation. The initial viewport begins at 07:00 without changing temporal data or the full-day model.

17. **Complete (2026-07-26):** define the shared native action-menu Escape/focus-return contract and correct dirty-form cancellation focus return. An open Views, overflow or Calendar view menu closes on Escape and returns focus to its summary; cancelling a dirty-form warning returns focus to the link that invoked it, with a form-control fallback only when that link is gone.

Journey planning is deferred to the informal [Phase 3 notes](phase_3_notes.md). It is not a Phase 2 closeout requirement and authorises no implementation within this phase.

## Completion criteria

Phase 2 completes only when an end-to-end review can demonstrate:

```text
Create a Project
→ create an Event related to that Project
→ relate People and a Location to the Event
→ create a recurring Event and trace its generated occurrence and exception to its series
→ synchronise a Person birthday to its canonical Birthdays-Calendar Event and project its recurrence, or generate a document-expiry occurrence
→ apply an applicable reminder default and a record-level override
→ deliver one useful actionable local notification
→ recover a missed due item without duplicate delivery
→ run a scheduled background check and record its Job Run separately
→ present any proposed canonical Event mutation for explicit approval
→ show generated records, decisions and actions in provenance and audit history
→ export and validate the integrated Phase 2 records through whole-platform portability
```

The review must also verify cancellation, archival and permanent deletion remain distinct; canonical records, derived occurrences and projections have not been conflated; and notifications, audit events and Job Runs retain separate identities. Persistent System Health remains a separately authorised future capability.

An Event table, rendered Calendar, isolated reminder, one scheduler function or one runnable automation rule is insufficient. The active capabilities must work together as one operational system. The dormant Task implementation is not a current completion prerequisite.

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
- Agenda/list Calendar views before the Week/Day workflow is stable.
- Direct Week-view slot creation, drag-and-drop rescheduling and Event resizing before overlay creation and editing are stable.
- Unspecified scheduled maintenance checks beyond Event reminders and overdue Tasks; those require later design within the existing Phase 2 boundaries.
- Destructive Inbox retention or automatic deletion of historic Inbox records.
- Repeated Inbox items for unchanged conditions or routine successful background work.

These exclusions do not remove the documented within-phase follow-ups from the implementation order; they prevent them from being treated as prerequisites for earlier foundations or as authority for unrelated work.

## Preserved ambiguities and decision history

The user-facing Calendar, Event, Task, reminder, Inbox, System Health and archive behaviour was approved on **2026-07-12**. The accepted architectural refinements on **2026-07-19** added explicit Calendars, planned-time-only initial records, bounded timed Events, database-enforced logical idempotency, non-consequential automation, serial recovery, per-job catch-up policies and manual failure rerun. Both decision sets are preserved here.

The following interactions remain deliberately unresolved and must be settled through authorised design work rather than inferred during implementation:

- **Task product redesign.** Calendar-originated Task capture, deadlines, sessions and Calendar projections are historical implementation work and dormant as of 2026-07-26. A user-led Phase 3 redesign must settle the Task model before any route, projection, reminder or automation interaction returns.
- **Later scheduled maintenance.** Checks beyond Event reminders and overdue Tasks, including their source records, trigger conditions and lead times, remain unspecified.
- **Detailed implementation mechanics.** Table shapes, route paths, service names, recurrence encoding, exception schema, archive retrieval mechanics and UI details beyond those stated here remain implementation-design work.

The following are deliberate distinctions rather than contradictions:

- An Event can conceptually represent something at a point or over an interval, while the initial timed Event model requires a bounded start and end.
- An all-day range is inclusive in user-facing date selection while normalized interval persistence and occurrence calculations are start-inclusive and end-exclusive.
- The in-app popup is an additional presentation of the same durable local notification, not a separate external delivery channel.
