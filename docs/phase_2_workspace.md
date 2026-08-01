# Phase 2 Workspace: Operational Time and Deterministic Automation

## Status, purpose and authority

**Phase 1 — Complete.** Pull request #1 is closed. Phase 1 closed as a development milestone after representative, rather than exhaustive, manual and automated verification. Later residual defects are ordinary maintenance work and do not reopen Phase 1 as a whole.

**Phase 2 — Event-focused and active.** Calendar and Event work, reminder delivery and recovery, scheduled Job Runs, registered deterministic automation, portability and data-quality coverage remain active. The experimental Task implementation was retired on 2026-08-01 after the local database was verified to contain no Task records. This workspace remains the living record for Phase 2 refinements and hardening until Phase 3 is deliberately defined. Persistent System Health remains deferred; neither the original closeout nor this workspace authorises it.

> **Task-work-management retirement (2026-08-01).** Task requirements and delivery entries below are preserved only as historical decision and delivery evidence. They are superseded by expansion entry 60 and do not describe current behaviour or constrain a future to-do design. Historical migration IDs remain append-only, while current Task code, schema, tests and relationships have been removed.

Phase 2 establishes Project E's operational time and deterministic-automation foundation:

```text
structured information → relationships → temporal information → Events
→ calendar projections → reminders and attention management
→ scheduling → deterministic automation → later AI-assisted operations
```

The phase remains human-first, database-first, local-first and AI-independent. This document is the canonical Phase 2 scope, architectural direction, implementation sequence, completion standard and exclusion list. The expansion section records delivered refinement work; implementation still requires an explicit user prompt.

## Enduring architectural principles

### Canonical records and shared platform boundaries

SQLite remains the canonical store. Phase 2 schema work must use migration-safe evolution, conservative dependencies and the existing application-service boundaries. Events and Tasks are canonical first-class peer entities with stable identity, editing, global search, cross-domain navigation, Timeline integration, history, provenance, audit, recent-record behaviour, appropriate duplicate handling, the standard relationship system and the normal recoverable entity lifecycle.

An **Event** represents something that occurs, occurred or is expected to occur. A **Task** represents work that should be performed. A Task is not an Event, and neither is a reminder. Connections among Events, Tasks, People, Organisations, Locations, Projects, Documents and Assets use normal Relationships; separate per-domain foreign keys or nested Event-Task types are not the default.

A **Project** is a peer entity and coordination hub, not the owner of its related records. It may gather Events, Tasks and other entities, but each related record remains independently canonical and may relate to no Project or more than one Project.

### Calendars, occurrences and projections

A **Calendar** is a first-class local Event grouping and configuration record. Every canonical Event belongs to exactly one Calendar, which supplies a name, colour, IANA timezone, default Event duration, ordering, archive state and default reminder policy. Events remain canonical records; the Calendar does not become a second Event store. A fresh installation supplies one default General Calendar. Calendars alone provide canonical Event grouping, management, filtering and colour; there is no separate Event classification layer. A public-HTTPS iCalendar subscription is deliberately different: it is an externally owned, read-only source under **Other calendars**, backed by a last-known-good operational cache rather than a local Calendar or canonical Event rows. Its local configuration supplies name, colour, IANA timezone, ordering, enabled state and default Event-notification policy, but no default Event duration because users do not create Events in it.

A calendar view is a projection over canonical records and traceable derived occurrences:

- A **canonical record** is a durable source record such as an Event, Task, Person or Document.
- A **derived occurrence** is a deterministic temporal instance traceable to a canonical source and definition, such as a recurring Event instance or a Document expiry.
- A **calendar projection** is the displayed time-based view of a canonical record or derived occurrence.

Eligible dates owned by Events or other canonical records must enter Calendar, reminder and Inbox behaviour through one shared temporal-occurrence pipeline. Each source adapts its canonical fact into a stable, traceable occurrence consumed by shared projection, policy, delivery and reconciliation services; it does not gain a standalone reminder scanner or Inbox-delivery path. The source record retains ownership of its date, and using the pipeline does not require materialising a canonical Event. A literal Event remains appropriate only when the time record deliberately needs Event identity and lifecycle. Reminders without a meaningful temporal occurrence, including approvals and system failures, retain their own operational semantics.

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

The desktop baseline remains usable at 800 × 600. Phone responsiveness is deferred. The Calendar visual-refinement brief approved on 2026-07-30 may use familiar Google Calendar interaction and layout patterns as reference, but must not alter the local-first Calendar, Event or Relationship model. Its authorised implementation order is recorded in the Phase 2 expansion workspace below.

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

Global policies define defaults for derived source kinds such as Document expiries. The protected Birthdays Calendar owns birthday Event reminder defaults; anniversaries are deferred. Local Calendars and read-only URL Calendars provide approved context-specific defaults. Reminder resolution for a canonical Event broadly proceeds from an occurrence override, to an Event override, to its local Calendar policy, then to the applicable global policy. A cached read-only URL Calendar occurrence instead uses its URL Calendar policy and does not gain a record-level override or canonical reminder definition. The Event notification creator starts from its linked Calendar defaults: no Event-specific rows preserves that inheritance, added rows add timings, and suppression rows remove selected inherited timings. Coincident timings produce one delivery. Existing disabled override persistence remains respected for compatibility, but the current creator does not expose a separate policy-state picker.

Reminder edits on a recurring Event use the established scopes **this event only**, **this event and future recurring events**, and **all instances of this event**. The first scope creates an occurrence-specific reminder exception; the second uses the existing traceable prospective-series split; the third changes the series policy. These edits affect pending and future deliveries only: historical Event occurrences and reminder deliveries are never rewritten or newly delivered.

**Recurring reminder contract.** A this-occurrence edit persists a reminder override against that generated occurrence's stable series/occurrence identity; it does not edit the canonical Event or another occurrence with the same date-like display value. A this-and-following edit first creates the normal traceable series split, then applies the amended reminder policy to the successor series. The predecessor retains its prior policy through its final occurrence, and the successor has its own future occurrence and delivery identities. An all-occurrences edit changes the policy of the current series definition, preserving the identities and delivery history of already occurred instances. In every scope, only pending deliveries for the affected future occurrence identities are recalculated; unaffected pending deliveries remain valid, while acknowledged, dismissed and resolved history is retained unchanged.

The initial default reminder timings are relative to the source's due instant or all-day 09:00 local-time anchor. Local Calendar, URL Calendar and record settings use repeatable positive-integer and unit controls, never a comma-separated text field. A Calendar can configure at most ten default notifications, and an Event can resolve to at most ten effective notifications after Calendar defaults, additions and suppressions are combined:

- Events: 1 hour and 10 minutes before.
- Task deadlines: 3 days, 2 days, 1 day, 6 hours and 1 hour before.
- Birthdays: 1 calendar month, 2 weeks, 1 week, 3 days, 1 day and 12 hours before.
- Document expiries: 1 calendar month, 2 weeks, 1 week, 3 days and 1 day before.

All all-day reminder sources use 09:00 in the configured platform timezone as their due-time anchor rather than midnight. The platform timezone defaults to `Australia/Brisbane` (UTC+10) until a user configuration setting is introduced; that future setting must preserve existing reminder meaning. Calendar-month offsets retain calendar semantics rather than being treated as a fixed number of days.

**Catch-up policy.** Reminder evaluation classifies sources as transient occurrences, persistent conditions or recurring dates. Canonical Events and cached read-only URL Calendar occurrences are transient: a delivery is created only while the occurrence remains upcoming; a past occurrence is not backfilled. Open Task deadlines and active Document expiries are persistent conditions: after their due anchor, normal pending reminder deliveries resolve and one durable overdue item remains until the condition changes or its source lifecycle suppresses it. Birthdays are recurring dates: past annual occurrences are not backfilled, and evaluation considers the next occurrence only. Phase 2D startup recovery applies these same rules.

Deterministically recurring facts do not receive a new persistent reminder definition every year. Their occurrences remain traceable to the source fact and current policy. A Person birthday synchronises to one canonical yearly recurring all-day Event in the protected Birthdays Calendar; a Document expiry remains an all-day derived occurrence owned by its Document. A 29 February birthday Event follows the established month-end backward-shift rule and occurs on 28 February in a non-leap year. Approximate dates do not generate reminders in this milestone; a later design may introduce narrowly defined, explainable circumstances for them.

**Delivery identity and material-change contract.** A delivery identity contains its source kind and stable source identifier, stable logical occurrence identity, due anchor instant, reminder timing, and reason. Identical inputs must reuse one delivery across repeated evaluation. A material change creates a new future pending identity only for an affected delivery: changing its due anchor through rescheduling or a recurrence change; adding or changing an applicable timing; or changing the applicable policy for that future occurrence. When a material change supersedes a due anchor or removes a timing, its active or snoozed pending delivery is resolved as superseded; unchanged timings and unaffected occurrences retain their current deliveries. Disabling a reminder resolves its active or snoozed pending deliveries and suppresses future delivery. Re-enabling evaluates only the current policy and creates a delivery only when it is due. Snooze changes the next-attention time of the same delivery identity. Acknowledging or dismissing retains historical identity and prevents redelivery unless a later material change produces a distinct identity. Refreshing, rendering, opening an Inbox item, or an otherwise immaterial source edit never changes delivery identity or redelivers an item. Startup recovery creates a missed delivery only when its logical pending delivery remains eligible and no matching active or historical delivery already exists.

Initial delivery creates a durable actionable local Inbox item. Email, SMS, external push and operating-system notifications are excluded.

Phase 2C establishes the reminder-resolution and delivery boundary without a background scan or general scheduler. Phase 2D invokes that boundary while Project E is running and at startup; when a reminder or job-triggered notice became due while the application was unavailable and no matching item exists, it creates one deduplicated recovered item retaining the original due time.

#### System Inbox

The Inbox is a dedicated operational attention screen, not a notification dropdown or social feed. Its name deliberately leaves room for later operational producers, but the current implemented queue contains reminder attention only. Email-like addresses, multi-user or agent recipients, approvals, System Health and other future producers are not implied by the current feature. The Browse navigation shows a restrained, semantically warning-coloured count of currently visible reminder items; a visibility-aware local poll refreshes it while the registered scan remains authoritative.

The active queue exposes only source-specific **Open event** or **Open document**, **Dismiss**, and the fixed **Snooze 10 minutes** action. Opening an Event reminder resolves that timing and navigates to the exact Calendar occurrence; opening a Document does not clear persistent Document-expiry attention. Dismiss and snooze mutate delivery state only, never the Event, Document or source fact. Historical acknowledgement, 30-minute snooze and next-open snooze states remain readable but are no longer active reminder actions.

One source occurrence and reason can have at most one active or snoozed item. Each configured timing may appear once: a later timing still appears after an earlier one was opened or dismissed, while a later timing that arrives before the earlier item is acted on resolves and replaces that visible item. Repeated scheduled evaluation cannot duplicate either timing. Historical delivery and transition records remain retained.

The Inbox opens to a chronological, divider-based queue grouped as **Overdue**, **Today**, **Tomorrow** and later dates. It has no separate Upcoming projection, generic **Active items** cards or manual reminder-evaluation control. The registered reminder-delivery job and its System Tools **Run now** action remain the execution boundary. Routine successful background work remains in Job/automation history rather than active Inbox attention.

Event-like attention stores the occurrence's end boundary and resolves automatically when that boundary passes, including while snoozed. All-day reminders resolve at the exclusive local end boundary. Document expiry remains a persistent condition with no automatic attention-expiry boundary: passing the expiry date or opening the Document does not clear it; dismissal or a material source/lifecycle change does. Cancelling, archiving, recycling, deleting or rescheduling a source continues to resolve affected pending attention.

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

18. **Complete (2026-07-26):** correct My calendars visibility-row layout so each checkbox remains at the left edge and its Calendar name uses the remaining sidebar width. Remove the Calendar's derived-and-related-dates section and its unused projection fetch, leaving the Calendar viewport for its primary Event projection.

19. **Complete (2026-07-26):** make My calendars visibility controls immediate and local. Toggling a Calendar now hides or shows its projected Events without a submit action or page reload, retains the selected set in browser session/navigation context, and exposes a right-side vertical-ellipsis link beside each Calendar name to its existing edit form.

The following Calendar visual-refinement brief was approved on **2026-07-30**. Its implementation order is:

20. **Complete (2026-07-30):** move Calendar navigation into the Project E header on Calendar pages only. The header contains a compact **Today** control, sleek previous/next chevrons, the current anchor date without its weekday (for example, **30 July 2026**), the existing Calendar-view selector, and a cog affordance for future Calendar settings. Entry 29 subsequently activated the cog and replaced its temporary **Coming soon!** state with the dedicated settings workspace.

21. **Complete (2026-07-30):** refine the Calendar sidebar's Calendar-group controls. Remove the separate **Manage calendars** button. Give **My calendars** and **Other calendars** independently operable up/down disclosure arrows; collapsing a group hides only its Calendar names and visibility checkboxes and does not change the current visibility filter or any projected Event. Place a single plus control beside **Other calendars** as the entry point for creating every new local Calendar. It targets the existing validated Add Calendar workflow directly, while created local Calendars remain part of **My calendars**. The same entry point is reserved for a later, separately designed workflow for supplied calendars, imported files or external Calendar APIs. **My calendars** has no plus control.

22. **Complete (2026-07-30):** make the Calendar's left sidebar an independently vertically scrollable region, separate from the main Calendar projection and page scrolling. Preserve its existing width, visual boundary and quick-create docking role.

23. **Complete (2026-07-30):** revise Calendar projection sizing so Month view has no page-level vertical scrolling and the complete four-, five- or six-week month grid divides the available Calendar viewport evenly. Month cells become more compact as browser zoom increases, with reduced spacing on short effective viewports; sufficiently small effective viewports remain the acknowledged hard breakpoint. Week and Day retain their independently horizontally and vertically scrollable full 24-hour timed grids.

24. **Complete (2026-07-30):** add a live current-time indicator to Day and Week. A red dot sits at the left edge where the timed grid begins and a red line extends across the current day's timed area at the current local display time. The browser derives the current date and minute in the validated Calendar display timezone and updates the indicator once per minute. It identifies both the present time and the Event occupying that position, if any, without changing canonical Event data.

25. **Planned follow-up, not authorised for implementation by this brief:** define a Year view presenting January through December of the selected year as a full-page family of mini-month grids, with direct navigation to dates within that year. Also define a Schedule view that lists Events chronologically and carries the same live red current-time boundary through the day's sequence. Both views must remain deterministic projections over the existing canonical Calendar and Event model; their detailed interactions require a later implementation brief.

26. **Complete (2026-07-30):** park historical Task service, projection, reminder-delivery and overdue-Inbox tests behind explicit `unittest.skip` markers while Task work management remains dormant. The test bodies remain local and readable for reconsideration during the user-led Task redesign. Active tests continue to enforce the current deferral boundary, including unavailable Task routes and disabled Task automation.

27. **Complete (2026-07-30):** align the Calendar-only header navigation with the left edge of the main Calendar column rather than immediately after the Project E brand, and place the future-settings cog directly beside global Search. Remove the remaining Calendar projection inset so its surface meets the header and sidebar boundaries without a gap. Move each Calendar-group disclosure control to the far right of its heading; **Other calendars** orders its plus control immediately before the disclosure arrow.

28. **Complete (2026-07-30):** move the Calendar-view picker out of the date-navigation cluster and into the right-side header tools, immediately to the left of the future-settings cog.

The following Calendar-settings interface brief was approved on **2026-07-30**. It authorises the dedicated settings shell and reuse of existing local Calendar forms, but not new external Calendar, discovery or file-interchange behaviour. Its implementation order is:

29. **Complete (2026-07-30):** activate the Calendar-header settings cog as the entry point to a dedicated Calendar Settings area. The settings area uses a stripped-back variant of the existing application shell: its slightly narrower left sidebar contains settings navigation rather than Calendar or Project E navigation, and its top bar contains only a **‹ Settings** control. The chevron returns to the exact Calendar Month, Week or Day context from which settings was opened, including its anchor date and visible-Calendar filter. The ordinary Project E brand, global Search and Browse or Calendar controls do not appear in this shell.

30. **Complete (2026-07-30):** build the Calendar Settings sidebar information architecture. Its primary destinations are **General**, **Add Calendar** and **Import/Export**. Add Calendar has a disclosure control immediately to the left of its label and child destinations for **Create New Calendar**, **Browse calendars of interest** and **From URL**. Import/Export exposes its **Import** and **Export** children only while that section is selected; selecting the parent opens and marks Import by default. Active destinations and expanded sections remain visually and accessibly identifiable.

31. **Complete (2026-07-30):** add a non-clickable **Settings for my calendars** sidebar heading below the primary settings destinations. Beneath it, list every active local Calendar from **My calendars** using the same recognisable colour-and-name row treatment as the Calendar sidebar. Each row opens that Calendar's settings form in the main pane, retains the list for rapid switching, and clearly marks the selected Calendar so colours and configuration can be compared without returning to the Calendar projection. When archived Calendars exist, a subdued secondary list keeps them reachable for inspection or unarchiving without mixing them into the active list.

32. **Complete (2026-07-30):** retain the existing validated local Calendar workflows inside the new shell rather than introducing duplicate forms or persistence. **Create New Calendar** initially reused the complete configuration form; entry 45 supersedes that surface with name and colour only. Selecting a Calendar presents name, colour, timezone, default duration, notification defaults and applicable default/archive/delete safeguards. Ordering is now exclusively controlled from the Calendar sidebar under entry 53. Creation and editing submit through the existing Calendar services, use the shared dirty-form protection, and preserve the Calendar return context. After creation, the new Calendar remains visible and selected in **Settings for my calendars** so it can be refined immediately.

33. **Complete (2026-07-30):** provide navigable settings destinations for **General**, **Browse calendars of interest**, **From URL**, Calendar **Import** and Calendar **Export**. General and discovery remain presentation-only **Coming soon!** pages. Entries 35–52 subsequently activate iCalendar upload/import, ZIP export and read-only public-HTTPS URL subscriptions while keeping Calendar interchange distinct from the existing whole-platform portability bundle. VCS and CSV remain unavailable.

34. **Complete (2026-07-30):** add focused route, rendering, active-navigation, disclosure and Calendar-context-return coverage for the settings shell. Existing Calendar creation, editing and lifecycle service tests remain authoritative for functional forms; the former interchange placeholder assertions were replaced when entries 35–52 activated those workflows.

The following Calendar-interchange brief was implemented on **2026-07-30** after inspecting the supplied local Google Calendar iCalendar 2.0 sample. The sample was used only as manual acceptance evidence and was never copied into the repository or imported into runtime data. The delivered boundary is deliberately an **iCalendar (`.ics` or `.ical`)** vertical slice. Legacy vCalendar/VCS and CSV remain unimplemented until their schemas, loss rules and representative fixtures are agreed.

35. **Complete (2026-07-30) — iCalendar boundary and sample profile:** implement Calendar interchange as a focused local service separate from whole-platform portability and external Calendar synchronisation. The supplied sample contains one `VCALENDAR` named **Neo-Pagan Holidays**, an `Australia/Brisbane` Calendar timezone and eight `VEVENT` components: all are date-only, seven use simple yearly recurrence, several span multiple all-day dates, one description is folded across content lines, and the file carries Google/RFC metadata including UID, sequence, status and transparency. This is sufficient for the first all-day recurring import path, but not evidence of timed, invitation, alarm or recurrence-exception compatibility. Test fixtures committed to the repository must be fictional derivatives rather than the user's downloaded file.

36. **Complete (2026-07-30) — bounded parser and neutral preview model:** add a standard-library iCalendar parser behind a dedicated module rather than embedding parsing in HTTP routes. It must validate UTF-8 input, unfold folded content lines, parse content-line names and parameters case-insensitively, unescape iCalendar text values, enforce one `VCALENDAR`, require iCalendar version 2.0 and stable `UID` values, reject malformed nesting or duplicate singleton fields, and apply explicit upload-size and component-count limits. Parsing produces neutral Calendar/Event preview records and diagnostics without opening a database transaction or creating canonical records. `.ics`, `.ical` and `text/calendar` are accepted labels; a filename extension never substitutes for content validation.

37. **Complete (2026-07-30) — preview-first destination choice:** replace the Import placeholder with an upload form and a validation preview. Import supports two explicit destinations: **Add to an existing Calendar**, selected by default and initially pointing to the active default Calendar such as General, or **Create a new Calendar**. Existing-Calendar import adds Events without renaming or reconfiguring that Calendar; the source `X-WR-CALNAME` and `X-WR-TIMEZONE` remain visible as source metadata only. New-Calendar import proposes a name from `X-WR-CALNAME`, falling back to the safe filename stem, and an IANA timezone from `X-WR-TIMEZONE`; its name, colour and timezone are editable, and a conflict requires a unique replacement. The preview shows the destination, Event count, recurring count, date span, per-Event mapping and every warning or unsupported feature. Uploaded bytes are staged only under Git-ignored runtime storage behind a random, single-use, expiring token. Preview and cancellation perform no canonical writes.

38. **Complete (2026-07-30) — first supported Event mapping:** one valid `VEVENT` is a complete import, so a single shared Event can be added directly to General or another selected Calendar without creating a Calendar. On confirmed apply, assign every new Event in that upload to the selected existing Calendar, or create and assign them to a new Calendar only when that mode was explicitly chosen. Map `SUMMARY` to Event title, `DESCRIPTION` to notes, date-only `DTSTART` plus exclusive `DTEND` to Project E's existing all-day interval, `STATUS:CONFIRMED` to planned and `STATUS:CANCELLED` to cancelled. A missing all-day `DTEND` means a one-day Event. Map only recurrence rules that the canonical recurrence model represents without loss: `FREQ` daily, weekly, monthly or yearly; positive `INTERVAL`; supported weekly/ordinal `BYDAY`; and a supported `UNTIL` or `COUNT` boundary. The sample's `RRULE:FREQ=YEARLY` therefore becomes one canonical Event series and derived yearly occurrences, not one materialised Event per year.

39. **Complete (2026-07-30) — explicit compatibility diagnostics:** retain `UID`, `SEQUENCE` and a normalised source fingerprint as interchange metadata, but do not overwrite Project E creation/audit timestamps with `DTSTAMP`, `CREATED` or `LAST-MODIFIED`. `PRODID`, `CALSCALE` and `METHOD:PUBLISH` are validated or reported as informational metadata. `TRANSP` is reported as not represented because Project E has no free/busy model; it does not justify adding a Google-shaped availability field in this slice. Any property that would cause meaningful loss—including `VALARM`, `ATTENDEE`, `ORGANIZER`, `LOCATION`, `URL`, attachments, `RDATE`, `EXDATE`, `RECURRENCE-ID`, multiple recurrence rules or unsupported `RRULE` parts—blocks confirmation rather than being silently discarded. A later brief may map those concepts after representative exports are inspected.

40. **Complete (2026-07-30) — stable source identity and repeat safety:** add one forward, migration-safe Event-iCalendar identity table rather than adding interchange fields to the canonical Event table. It associates one canonical Event or series anchor with a unique source UID, source sequence, last imported fingerprint and import timestamp. Preview classifies each UID as new, already imported unchanged or conflicting. An unchanged repeat is a no-op and creates neither another Event nor an empty duplicate Calendar; a changed source with an existing UID is blocked until a separate, explicitly reviewed update/merge workflow is designed. Duplicate UIDs within one upload are rejected unless a later recurrence-exception implementation deliberately gives them `RECURRENCE-ID` semantics.

41. **Complete (2026-07-30) — atomic and authorised apply:** confirmation is the explicit approval to create the listed canonical Events in the selected destination and, only in new-Calendar mode, the proposed canonical Calendar. Reparse and revalidate the staged bytes, destination Calendar and any editable new-Calendar settings at apply time; do not trust hidden preview counts or allow assignment to an archived destination. Extend the existing Calendar/Event/recurrence service boundaries with transaction ownership and `imported` provenance rather than duplicating SQL. The optional Calendar, Events, recurrence definitions, interchange identities, field provenance, per-record history/audit and one summary import audit record commit in a single transaction; any failure rolls back the whole import. Applying an iCalendar file does not create a subscription, retain a WAN URL, schedule refreshes or later overwrite user edits.

42. **Complete (2026-07-30) — selectable multi-Calendar ZIP export:** replace the Export placeholder with a colour-and-name checklist of Calendar sources. Every active local Calendar is selected by default, with **Select all** and **Clear all** controls; archived local Calendars and enabled external URL subscriptions appear in separate unchecked groups but remain explicitly selectable. The selection is independent of Calendar-view visibility and must contain at least one valid source. A single read-only export returns `application/zip` with one independently valid, safely and uniquely named `.ics` member per selection, including an empty `VCALENDAR` for a selected local Calendar with no exportable Events. Local members carry their own `VCALENDAR` metadata, `X-WR-CALNAME`, `X-WR-TIMEZONE`, active non-recycled and non-archived assigned Events, whole-Event cancellation status and recurrence definitions that the first supported subset can express exactly. Preserve imported UIDs; generate deterministic Project E UIDs for native Events so repeated exports retain identity. An external member is serialized only from that subscription's last successfully validated cache, retains its source UIDs and never causes a network fetch during export. Escape text, use CRLF content lines, fold at the iCalendar byte limit, emit all-day exclusive `DTEND`, and serialize recurrence without materialising occurrences. The ZIP is an interoperability convenience containing ordinary iCalendar files, not a Project E backup and not a replacement for whole-platform portability. Validate every selection before starting the download; if any selected source lacks a usable cache or contains timed Events, occurrence exceptions or another unsupported semantic, show a precise per-source compatibility report and produce no partial or lossy ZIP.

43. **Complete (2026-07-30) — testing and delivery evidence:** cover parser unfolding/escaping, malformed input, limits, a one-`VEVENT` import into General, a multi-Event import into an explicitly new Calendar, destination reassignment protection, date boundaries, multi-day spans, yearly recurrence, unsupported-property blocking, preview-without-writes, single-use staging, explicit confirmation, atomic rollback, imported provenance/audit, fresh and upgraded schemas and UID repeat/conflict behaviour. Export coverage must include default/select-all/clear-all state, empty selection rejection, active and archived Calendar choices, tampered identifiers, safe collision-resistant ZIP member names, exact selected-member inclusion, an empty Calendar member, download headers, all-or-nothing compatibility failure and supported import→ZIP export→member parse equivalence. Add focused route/rendering tests and a live upload/preview/confirm/download smoke test using a temporary database. The local Neo-Pagan sample may be used manually as acceptance evidence but must never be copied into tracked fixtures, runtime examples or commits. Before timed Event interchange is claimed, inspect at least one Google export containing UTC, `TZID` and preferably daylight-saving behaviour; before exception support is claimed, inspect one recurring series with a deleted occurrence and one rescheduled occurrence.

44. **Deferred long-term follow-up, not part of this implementation:** add a singular Event export control only after the Calendar-level interchange workflow is mature. That later design must decide whether exporting a recurring Event means the source series, one generated occurrence or a selected recurrence scope, and must preserve the same UID, exception, timezone and compatibility rules as bulk export. No per-Event export route, button or placeholder is required in the current Calendar Settings work.

The following local-Calendar creation refinement and read-only URL-subscription brief was implemented on **2026-07-30**. It is the separately scoped exception to the earlier blanket external-Calendar exclusion.

45. **Complete (2026-07-30) — minimal local Calendar creation and edit boundary:** reduce **Create New Calendar** to exactly two editable values: **Calendar name** and **Colour**. The create handler must derive all other values from trusted application defaults rather than accepting hidden or manually supplied creation fields: the established `Australia/Brisbane` timezone, 60-minute default Event duration, next available local Calendar order, event Calendar kind and no Calendar reminder override. After creation, select the new Calendar in **Settings for my calendars**. The edit form remains the place to change name, colour, timezone, default duration, reminder defaults and lifecycle settings, but its numeric **Order** field is removed. Focused tests must verify that creation exposes only name and colour, that edit exposes no ordering textbox and that injected creation values cannot bypass the trusted defaults.

46. **Complete (2026-07-30) — external URL Calendar semantics and acceptance example:** activate **From URL** for public, read-only iCalendar subscriptions. A URL subscription is not a local Calendar and its items are not canonical Project E Events: it is an externally owned source projected into the Calendar. It therefore appears as its own colour-and-name row under **Other calendars** and the parallel **Settings for other calendars** settings section, never under **My calendars** or **Settings for my calendars**, and cannot be selected as an Event creation/import destination. The initial acceptance example is `https://public-holidays.dteoh.com/all.ics`. When inspected on 2026-07-30 it returned `text/calendar; charset=utf-8`, identified itself as **All Public Holidays in Australia**, supplied an ETag, and contained 122 date-only `VEVENT` items covering 2025–2027 with stable UIDs, exclusive end dates, transparent availability and folded/escaped descriptions but no recurrence rules. Automated tests must use fictional local fixtures rather than depend on that live service.

47. **Complete (2026-07-30) — safe add-and-preview workflow:** the From URL form initially asks only for an absolute public HTTPS URL. Reject local-file/data schemes, embedded credentials, private/loopback/link-local destinations, unsafe redirect targets, excessive redirects, oversized responses, slow responses and content that fails the shared iCalendar parser. Do not require the remote server's MIME declaration to be perfect, but show the received content type and validate the bytes. The first fetch produces a no-write preview containing final URL, source Calendar name, Event count, date span, unsupported features and proposed display colour. Explicit confirmation creates only the subscription configuration and accepted cache; leaving the preview creates nothing. Treat URL query values as potentially sensitive: do not place the complete URL in routine logs or audit notes.

48. **Complete (2026-07-30) — external configuration and last-known-good cache:** add forward, migration-safe operational tables for URL-subscription configuration, refresh state and parsed external Event items, separate from `calendars`, `entities`, `events` and recurrence identity. A subscription retains its source URL, display name, colour, enabled state, ordering, ETag/Last-Modified validators, last check/success times and current error; cached items use source-scoped UID identity and the neutral iCalendar values needed by projections. Interpret “not held locally” as **not locally owned or canonical**. A small last-known-good local cache is still required so opening the core Calendar never blocks on WAN access and a temporary outage does not erase previously visible holidays. Cache rows do not gain relationships, record-level reminder definitions, edit history, Recycle Bin lifecycle or canonical Event links; entry 59 subsequently adds a Calendar-level reminder policy to the subscription configuration.

49. **Complete (2026-07-30) — conservative refresh and failure behaviour:** perform the initial fetch during preview, expose **Refresh now**, and use the existing registered in-process scheduling boundary to conditionally refresh enabled subscriptions when their last successful check is stale, initially after 24 hours. Send `If-None-Match` and `If-Modified-Since` when validators exist; a `304` updates check state without replacing items. Parse and validate a changed response completely before atomically replacing that source's cache. A timeout, HTTP error, invalid feed or unsupported semantic retains the last-known-good items and records a visible stale/error state in settings; it never partially updates, deletes canonical records or creates an Inbox item. No separate worker or refresh-on-every-Calendar-render behaviour is introduced.

50. **Complete (2026-07-30) — Other calendars interaction:** after confirmation, make the URL source visible by default under **Other calendars** using the same checkbox/disclosure behaviour as other Calendar visibility rows. Its colour distinguishes its read-only items in Month, Week and Day projections; selecting an item opens a read-only source preview without record-level edit, reminder, relationship or delete controls. The From URL page owns only addition and preview. Existing URL calendars are listed individually under **Settings for other calendars**; selecting one opens its Calendar-level settings, URL host, last successful refresh, freshness/error state, **Refresh now**, enable/disable and explicit **Remove calendar** controls. Removing a URL calendar deletes only its subscription configuration and cache after confirmation. It never deletes a canonical Event because none was created.

51. **Complete (2026-07-30) — import, export and portability distinction:** uploading an `.ics`/`.ical` file remains a one-time import that creates canonical local Events in a selected **My calendars** Calendar; adding the same address through From URL instead creates a renewable, read-only **Other calendars** subscription. The selectable Calendar ZIP export may offer enabled URL subscriptions in a separate unchecked group and serializes only their last-known-good cache, without fetching or converting the source into canonical Events. Whole-platform portability retains the subscription configuration and cache as operational local state; neither Calendar export nor portability implies ownership of the third-party source.

52. **Complete (2026-07-30) — URL-subscription testing and documentation:** cover public-HTTPS validation, redirects and destination revalidation, response/time/size limits, MIME tolerance plus content validation, initial preview without writes, confirmation, source-scoped UID replacement, ETag `304`, changed-feed atomic swap, stale-cache retention, refresh scheduling, manual refresh, enable/disable/remove, URL redaction, Other-calendars placement/visibility, read-only item previews and absence of canonical Calendar/Event rows. Use synthetic iCalendar bytes and injected deterministic resolver/fetch boundaries for automated network tests; reserve the supplied Australian public-holidays URL for an optional live smoke test. Update architecture, database, design, route catalogue, build log and this completion ledger when implemented.

53. **Complete (2026-07-30) — drag-only Calendar ordering:** make the Calendar page's left sidebar the sole user-facing ordering surface. Rows within **My calendars** can be dragged to reorder local Calendars; rows within **Other calendars** can be dragged to reorder external sources, but a row cannot cross between the two ownership groups. New local Calendars and URL subscriptions append to their respective groups. Use a visible drag handle with pointer/touch behaviour and a keyboard-operable drag interaction rather than exposing move buttons or numeric order fields. On drop, submit the complete ordered identifier list for that group to a focused reorder service, validate it against the exact active group with no missing, duplicate or foreign identifiers, and atomically normalize persisted order values. Reordering must not change visibility checkboxes, disclosure state, Calendar defaults or Event data; the Calendar Settings lists reflect the resulting order without becoming a second ordering surface. Cover successful local/external moves, unchanged drops, malformed/tampered orders, cross-group rejection, persistence after reload and accessible drag state.

The following Calendar date-context refinement was implemented on **2026-07-30** from the user's written reference. The temporary screenshots were unavailable, but the stated text and grid contracts were sufficient for implementation.

54. **Complete (2026-07-30) — view-specific heading language:** remove the **Week of …** title. Month view continues to show the selected month as its full English month and year, such as **June 2026**. Week view describes the complete Monday–Sunday interval by month context: if all seven days are in one month, use the same full form, **June 2026**; if the week crosses months within one year, abbreviate both months, **Jun – Jul 2026**; if it crosses a year, include both abbreviated month/year pairs, **Dec 2026 – Jan 2027**. Day view continues to show its exact selected date, such as **30 July 2026**, rather than reducing it to month context. Implement this through one focused date-heading formatter so navigation and independent Calendar loads cannot diverge.

55. **Complete (2026-07-30) — Week/Day ISO week companion:** place a visually secondary **Week N** label immediately beside both the Week view's month context and the Day view's exact date, matching the supplied reference's relationship between **June 2026** and **Week 26**. In Week view, derive `N` from the Monday starting the displayed interval; in Day view, derive it from the selected date. Both use ISO-8601 week numbering, the same convention already used by the mini calendar. Keep the view-specific date context as the primary heading and expose the companion as readable text rather than folding it into navigation controls. Month view has no top-bar companion because its individual week rows carry the numbers.

56. **Complete (2026-07-30) — Month-view week-number rail and coverage:** add a slim first column before Monday in the full Month grid. Its header identifies the column as weeks, and each four-, five- or six-week row displays that row's Monday-based ISO week number; the compact visible value may be numeric while its accessible label is **Week N**. The rail participates in the Month grid's row sizing but is not a day tile, Event target or additional navigation control. Give it a fixed compact width while Monday through Sunday retain seven equal flexible columns, preserving the no-page-scroll Month contract and existing compact high-zoom behaviour. Cover one-month and cross-month Week headings, the cross-year heading, exact Day headings, ISO week 1 and week 52/53 boundaries, Week/Day companion visibility, the Month header's lack of a duplicate companion, exact Month row/number alignment, accessible labels and four-/five-/six-row layouts.

57. **Complete (2026-07-30) — interchange delivery validation:** validate the supplied Neo-Pagan Google iCalendar sample through the no-write parser path and the Australian public-holidays URL through the safe fetch path without copying either source into the repository or canonical runtime data. Add isolated live-HTTP upload/preview/confirm/download coverage, focused migration and subscription lifecycle checks, and full-suite compile/test verification. Correct whole-platform portability validation to require one active default Calendar **per Calendar kind**, preserving valid General plus protected Birthdays defaults while Calendar subscription configuration/cache continues to travel inside the SQLite snapshot.

58. **Complete (2026-07-30) — settings ownership grouping:** divide the Calendar Settings sidebar into explicit ownership groups. **Settings for my calendars** retains locally owned/user-created Calendars and built-in local Calendars; **Settings for other calendars** lists URL-backed read-only Calendars with the same colour-and-name navigation treatment. Remove the generic visible **Subscriptions** collection from From URL, make each Other-calendar row open its own management page, and return a newly confirmed URL Calendar directly to that page. Internal subscription/cache terminology remains an implementation detail and does not replace the user-facing Calendar model.

59. **Complete (2026-07-30) — Other-calendar settings and notifications:** give each URL-backed Calendar the same applicable edit controls as a local Calendar: name, colour, IANA timezone and repeatable Calendar-level Event notifications, alongside its existing refresh, enable/disable and removal controls. Deliberately omit default Event duration because users do not create or schedule Events in an externally owned source. Store the notification policy in the shared reminder-policy boundary under a distinct URL Calendar context; cached items remain non-canonical and receive no record-level reminder controls. Reminder evaluation treats their stable source-UID-backed occurrences as transient Events, creates deduplicated local Inbox deliveries, opens the read-only Calendar preview from Inbox, and resolves pending attention when a source item materially changes, disappears, is disabled or is removed. Refresh preserves user-edited settings and stable cache-row identity for unchanged source UIDs.

60. **Complete (2026-08-01) — retire the experimental Task subsystem:** verify the local runtime database contains no canonical Task records, Task relationships, deadline/session rows, reminder deliveries, overrides or review proposals, then remove the Task entity definition, service/page modules, dormant HTTP paths, relationship catalogue entries, Task reminder contexts, Task-only automation actions, proposal storage and skipped legacy tests. Add forward migration `20260801_31_retire_task_subsystem`, retaining the append-only historical migration ledger while removing Task tables and constraints from the current schema. The migration refuses before deletion if any Task record, proposal or relationship exists. Future work management requires a fresh authorised design and migration rather than compatibility with this retired model.

61. **Complete (2026-08-01) — compartmentalise shared runtime boundaries:** split HTTP server configuration, top-level dispatch, low-level request/response support and pure Event-form parsing out of the domain handler; replace mutable handler-class test configuration with immutable per-server settings and shared route-test setup; centralise stable Calendar, timezone, duration and reminder defaults; move entity lifecycle orchestration above focused persistence and extract Inbox transition/resolution persistence for reuse by source services. Preserve the `app/db.py` and `app/views.py` facades and current behaviour while eliminating the previously cyclic eight-module entity/Event/recurrence/reminder/subscription import component. Add focused server-isolation coverage and complete full-suite and compile verification. No schema, user-facing behaviour, ontology or product contract changes are introduced by this refactor.

62. **Complete (2026-08-01) — modularise stylesheet ownership with visual verification:** replace the accumulated application stylesheet with an ordered manifest over focused base, shell, Calendar, shared-component, System Tools, record, discovery, specialist-view and interaction modules while preserving `foundation.css` as the sole token/theme boundary. Make the static handler safely serve valid top-level CSS modules without a duplicated filename registry, and make structural tests resolve the manifest as the source of cascade order. Preserve the previous selector and declaration order exactly while normalising module line endings, then verify representative Home, collection, form, Calendar and Calendar Settings routes in the running application at supported desktop dimensions. Remove the resolved stylesheet-concentration debt; no mobile workflow or user-facing design change is introduced.

63. **Complete (2026-08-01) — add a local README interface gallery:** replace the README's single externally hosted Home image with four tracked, clickable screenshots covering Home, a connected Person profile, Calendar Month view and the derived Family Tree. Capture the images at a consistent supported desktop viewport from a temporary isolated database containing only clearly fictional demonstration records, then discard that database. Keep the gallery assets separate under `docs/assets/screenshots/` so repository presentation does not depend on an external attachment host or expose private runtime data.

64. **Complete (2026-08-01) — adopt a shared temporal-occurrence pipeline direction:** record ADR-028 and align architecture, database, ontology, glossary and attention-design documentation around one extensible route for Event schedules and eligible record-derived dates to reach Calendar projection, reminder evaluation, delivery reconciliation and Inbox attention. Canonical source records continue to own their dates; the shared route does not require every occurrence to become an Event and does not apply to non-temporal operational attention. Record the current hardcoded reminder-source enumeration as unresolved debt for the next authorised Inbox/reminder refactor. This entry delivers documentation and architectural direction only; no runtime or schema refactor is claimed.

### Inbox reminder refinement implementation record

This brief records the direction approved and implemented on **2026-08-01**. The numbered expansion entry below is the delivery claim; this retained brief preserves the agreed scope and verification sequence.

#### Product boundary and agreed behaviour

- Keep **Inbox** as the broad long-term name, while limiting this implementation to reminder attention. Email-like addresses, multi-user delivery, agent recipients, approvals and other future Inbox producers are not introduced.
- Remove the user-facing **Evaluate reminders** control. The registered reminder-delivery job and its System Tools **Run now** control remain the execution boundary.
- Remove the **Upcoming** reminder preview and the **Active items** panel treatment. The default Inbox becomes a quiet chronological review queue made from divided rows rather than a grid of generic cards and buttons.
- Show only currently actionable reminders. Group the list by useful date context such as **Overdue**, **Today**, **Tomorrow** and then later dates, ordered chronologically within each group. An empty Inbox says that the user is caught up.
- Present one visible item for one source occurrence and reason. If another configured timing becomes due for the same occurrence, it replaces the older active or snoozed presentation without explaining consolidation in the interface. Historical delivery and action records remain available in Archive.
- Replace the generic **Open source** and **Acknowledge** controls with a source-specific primary action such as **Open event** or **Open document**, a quiet **Dismiss** action and one icon-only **Snooze 10 minutes** action. The snooze control uses a local clock/`zzz` SVG plus the exact accessible label and hover title **Snooze 10 minutes**. The original due time remains unchanged.
- Opening an Event reminder clears that current reminder before navigating to the occurrence. This applies to canonical Events, recurring occurrences, the protected Birthdays Calendar and cached read-only URL Calendar occurrences. Dismiss also clears the current reminder without changing the Event.
- An untouched Event reminder resolves automatically when that occurrence ends. A snoozed Event reminder also resolves if the occurrence ends before it returns. All-day Events resolve at their exclusive local end boundary, so a birthday remains actionable through its calendar day.
- A Document-expiry reminder is persistent attention. Opening the Document does not clear it, and passing the expiry date does not clear it. It remains until the user explicitly dismisses it or the source condition changes because the expiry is changed, removed, archived, recycled or deleted. The Document continues to own the expiry fact; no standalone Document-reminder subsystem or duplicate canonical Event is introduced.
- Preserve the existing Archive and deep-history retention boundary. The active queue does not distinguish between acknowledged and dismissed reminders because acknowledgement is removed from this reminder interaction. Existing historical states remain readable rather than being rewritten.
- Add an Inbox navigation badge containing the number of currently visible reminder items. Omit the badge at zero, label its scope accessibly, use the shared semantic warning treatment rather than a hardcoded colour, and refresh it with a small local polling endpoint while the page is visible. The scheduled scan remains authoritative, so no socket, worker or external service is required.

#### Implementation sequence

1. **Introduce the shared temporal-occurrence provider boundary.** Define one typed occurrence contract carrying source identity, occurrence identity, title, start/due and end boundaries, reminder-policy context, source destination, projection eligibility and persistence/resolution behaviour. Register providers for canonical Events (including Birthday Events), cached URL Calendar occurrences and Document expiries. Calendar reads projection-eligible occurrences and reminder evaluation reads reminder-eligible occurrences from the same registry; the Document-expiry provider remains hidden from Calendar until that workflow is separately designed. Move source enumeration and source-specific condition tests out of the reminder evaluator and route-level Calendar assembly. Bound recurrence projection by the largest configured lead time so long-lead Birthday and Calendar reminders cannot be missed. A future eligible record date adds a provider rather than another scanner, projection path or Inbox path.
2. **Make active attention logical and deterministic.** Reconcile existing data through a forward migration, store the occurrence's attention-expiry boundary on each Event-like delivery, and add a database invariant that permits at most one active or snoozed item for a source occurrence and reason. Persistent conditions such as Document expiry have no automatic attention-expiry boundary. When evaluation finds several already-due timings during catch-up, materialise only the latest applicable threshold as visible attention. When a later timing becomes due, resolve the superseded active/snoozed row and retain both transitions in history. Repeated evaluation remains idempotent, and source rescheduling or policy changes continue to resolve only affected pending attention.
3. **Implement source-specific lifecycle rules.** During every scheduled evaluation, resolve Event-like attention whose occurrence end has passed. Add an Inbox open-action route that validates the item and source, clears Event-like attention with an explicit `opened_source` history action, and then redirects to the occurrence destination. Document opening performs the redirect without changing Inbox state. Replace the current 30-minute and next-open actions with a fixed ten-minute snooze; remove reminder acknowledgement from the active route and view while preserving old history values.
4. **Replace the Inbox presentation.** Render the chronological date-grouped row list, source-specific labels, compact metadata, restrained secondary actions and the new local snooze icon. Remove manual evaluation status, Upcoming generation/rendering and the generic active-card panel. Restyle Archive to use the same readable row language while retaining its current 500-item paging and deep-history behaviour.
5. **Add the global count projection.** Calculate the initial active logical count when rendering the normal application shell, expose a read-only JSON count route, and add a visibility-aware browser poll that updates the navigation badge without announcing the whole navigation repeatedly. The count excludes archived, dismissed, resolved, future-preview and not-yet-reactivated snoozed items.
6. **Verify and document the delivered contract.** Add focused service, migration, route, rendering, static-asset and JavaScript tests; verify fresh-database creation and upgrade reconciliation; cover timed/all-day/recurring/Birthday/external Event expiry, persistent Document expiry, catch-up consolidation, later timing replacement, snooze, source changes, count accuracy and accessible control names. Run the full unit suite, compile check and a local browser smoke test at the supported desktop viewport. On implementation, update the current-behaviour sections, route catalogue, architecture/database references, debt register, build log and this workspace with a dated numbered **Complete:** entry.

#### Explicit non-goals for this implementation

- Creating internal email addresses, mail transport, user or agent mailboxes, multi-user accounts, assignments or recipient-specific reminder policies.
- Materialising every record-derived date as a canonical Event. The provider contract supplies shared temporal behaviour while the source record retains ownership.
- Adding Document-expiry configuration or a new Document-expiry Calendar view before that future workflow is separately designed.
- Adding a general review/approval queue, System Health, external notifications, operating-system notifications or autonomous action.
- Deleting historic Inbox items or rewriting existing audit, Job Run or automation-run history.

#### Resolved implementation decisions

1. A separately configured later timing still appears once after an earlier reminder was opened or dismissed; only one item for the occurrence and reason is visible at a time.
2. **Open event** lands on the exact occurrence in Calendar context, including recurring and read-only external occurrences.
3. Routine no-op Job Run, automation-run and global-audit noise remains outside this implementation and is recorded as a separate runtime-history follow-up.

65. **Complete (2026-08-01) — refine Inbox reminder attention through the shared temporal pipeline:** add `app/temporal_occurrences.py` as the shared provider boundary for canonical Events, protected Birthday Events, cached URL Calendar occurrences and derived Document expiries; make Calendar and reminder projections consume that boundary; and size recurrence evaluation from configured lead times, correcting long-lead Birthday delivery. Add migration `20260801_32_consolidate_inbox_attention` to reconcile duplicate active timings, store Event occurrence attention-expiry boundaries and enforce one active/snoozed item per source occurrence and reason. Deliver each configured timing once, let later timings replace older visible attention, resolve Event reminders on exact-occurrence open or occurrence end, and keep Document-expiry attention persistent. Replace the card/Upcoming/manual-evaluation Inbox with chronological rows, exact source actions, fixed accessible ten-minute snooze, retained Archive and a visibility-aware semantic navigation count. Preserve historical states and runtime execution history; record the latter's visual noise as separate debt.

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
- Two-way external Calendar synchronisation, authenticated Calendar accounts/APIs, CalDAV, write-back and external mutation remain excluded. The separately planned public-HTTPS, read-only iCalendar URL subscription is the sole scoped external-Calendar exception; email ingestion, email delivery, SMS, external push and operating-system notifications remain excluded.
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

- **Future work management.** The retired Task model creates no product commitment. Any later to-do capability requires separately authorised product design and may use different terminology, identity and workflows.
- **Later scheduled maintenance.** Checks beyond Event reminders and overdue Tasks, including their source records, trigger conditions and lead times, remain unspecified.
- **Detailed implementation mechanics.** Table shapes, route paths, service names, recurrence encoding, exception schema, archive retrieval mechanics and UI details beyond those stated here remain implementation-design work.

The following are deliberate distinctions rather than contradictions:

- An Event can conceptually represent something at a point or over an interval, while the initial timed Event model requires a bounded start and end.
- An all-day range is inclusive in user-facing date selection while normalized interval persistence and occurrence calculations are start-inclusive and end-exclusive.
- The in-app popup is an additional presentation of the same durable local notification, not a separate external delivery channel.
