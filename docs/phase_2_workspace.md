# Phase 2: Operational Time and Deterministic Automation

## Status and authority

**Complete.** The owner accepted the delivered experience and authorised closure on 2026-08-03. Phase 2 is a completed development milestone, not a claim of exhaustive testing or a stable public release. Residual defects are normal maintenance and do not reopen the phase.

This document records the delivered scope, enduring contract, grouped delivery history, closure evidence and exclusions. Current implementation mechanics belong in [Architecture](architecture.md) and [Database Design](database_design.md); semantics belong in [Ontology](ontology.md) and the [Glossary](glossary.md); detailed decisions remain in `ARCHITECTURE_DECISIONS.md`. The Git history retains the former line-by-line implementation diary.

The experimental Task subsystem was retired on 2026-08-01 after the local database was verified to contain no Task records or linked operational data. ADR-027 and migration `20260801_31_retire_task_subsystem` preserve that decision. Historical Task delivery does not describe current behaviour or constrain a future work-management design.

## Delivered contract

### Canonical Events, Calendars and Relationships

- An **Event** is a canonical first-class entity with stable identity, global Search and Timeline participation, audit/history/provenance, recent-record behaviour, standard Relationships and the normal recoverable entity lifecycle. It may relate to People, Organisations, Locations, Projects, Documents, Assets and other Events; a Project coordinates peers rather than owning them.
- Every Event belongs to exactly one local **Calendar**. A Calendar supplies name, colour, IANA timezone, default Event duration, ordering, archive state and default reminder policy. A fresh database contains default General and protected Birthdays Calendars. Calendars are the sole local Event grouping/configuration layer; there is no parallel Event-category store.
- Users can create, rename, reorder, archive and configure local Calendars. Archived Calendars retain their Event assignments, cannot receive new assignments and may be deleted only when empty and non-default. Changing the default requires another active Calendar.
- Human-created Events originate from Calendar workflows. The generic entity menu and a generic Event index do not provide competing create/edit paths. Event Relationships use the normal post-creation relationship workflow.

### Calendar experience

- Month, Monday-first Week and Day are deterministic projections over canonical Events and derived occurrences. Month uses a bounded four-, five- or six-row grid with ISO week numbers; Week and Day retain independently scrollable 24-hour grids. Timed blocks show duration and clip/continue across display-day boundaries. A live current-time marker appears in Week and Day.
- The Calendar header provides Today, previous/next, view-appropriate date context, the Month/Week/Day selector and Calendar Settings. The Calendar sidebar provides Create event, a six-row Mini Month, and independently collapsible **My calendars** and **Other calendars** groups.
- Visibility filters are local presentation state and do not mutate records. Browser-session context retains the active view, anchor date and visible Calendars through navigation, Event preview, create/edit/delete, More options and Calendar Settings. Return targets are restricted to validated Calendar-local URLs.
- Quick create is a non-modal, draggable panel that may dock into the Calendar sidebar. It contains essential scheduling fields, direct save and **More options**; More options carries entered values to the full form. An unsaved Event appears only as a client-side provisional projection. Description progressively expands while persisting to the canonical `notes` field.
- Local and external Calendar rows reorder only inside their ownership group through accessible drag interaction. Settings is not a second ordering surface. Local Calendar creation accepts only name and colour; trusted defaults supply timezone, duration, ordering and kind. Editing owns full applicable configuration.
- The supported Calendar baseline is desktop, including the constrained 800 × 600 Phase 2 view. Phone/mobile workflows are excluded.

### Temporal semantics, recurrence and lifecycle

- Timed Events require bounded positive start/end intervals. Precise instants persist in UTC with an originating IANA timezone; `Australia/Brisbane` is the platform default. All-day Events use calendar dates. User-facing all-day ranges are inclusive; stored/calculated intervals are start-inclusive and end-exclusive.
- Initial Events record planned time only. Actual start/end tracking and point-in-time timed Events are not delivered. Approximate dates retain a closest known date plus an approximate marker.
- Recurrence supports deterministic daily, weekly, monthly and yearly rules; positive intervals; selected and ordinal weekdays; and bounded date/count endings. Missing month days shift backward to the month's last valid day, including 29 February to 28 February in non-leap years.
- Generated occurrences are traceable projections, not duplicate Events. This-occurrence changes use exceptions; this-and-following changes use a traceable series split; all-occurrences changes update the series. Recurrence definition changes create new future occurrence identities.
- Cancellation, archival, Recycle Bin deletion/restoration and permanent deletion are distinct. Cancellation remains visible history; archival hides an Event from ordinary Calendar projection; Recycle Bin deletion is recoverable; permanent deletion is confirmed and recovery-protected. Restoring a deleted Event preserves its cancellation/archive state.
- A Person birthday owns one linked canonical yearly all-day Event in the protected Birthdays Calendar. Name/date changes update the same Event; Person deletion/restoration archives/restores it. Ordinary Events cannot be placed in that Calendar.

### One temporal-occurrence route

A canonical record owns its date. Eligible Event schedules and record-derived dates adapt into stable **temporal occurrences**, which shared Calendar, reminder, delivery and reconciliation services consume. A projection does not become a canonical duplicate merely because it appears on a Calendar.

The delivered provider boundary covers canonical Events, protected Birthday Events, cached external Calendar occurrences and derived Document expiries. Materialising a new Event is appropriate only when the time record deliberately needs independent Event identity and lifecycle. Non-temporal attention such as approvals or system failure remains outside this pipeline.

### Reminders and Inbox

- A reminder is policy attached to a Calendar, supported external Calendar or specific source record/occurrence. It is behaviour, not a standalone domain entity. Calendar defaults and record overrides support inherited timings, custom timings, suppression and disable behaviour, with at most ten effective reminders.
- Logical occurrence and delivery identities are stable and database-enforced. Evaluation is timing-aware, repeat-safe and lifecycle-aware. One active/snoozed attention item exists for a source occurrence and reason; each configured timing can deliver once, and a later timing replaces older visible attention for that occurrence.
- Event attention resolves when its exact occurrence is opened, when the occurrence ends, or when its source is cancelled/recycled/changed. Document-expiry attention remains persistent after opening or passing the date. Snooze is a fixed accessible ten minutes while retaining the original due time.
- Inbox shows a chronological active queue with exact source actions, a semantic navigation count and a retained 500-item paged Archive/deep-history path. Routine successful work does not create Inbox noise.
- Reminder policy, Inbox item/action, audit event, Job Run and Automation Run remain separate records with separate identities.

### Local operational runtime and automation

- The application runs registered jobs serially while Project E is open. Schedules, per-job catch-up policy, expiring leases, checkpoints and append-only Job Runs live in SQLite. Startup recovery reactivates due snoozes and performs one coalesced reminder scan when needed; database identities prevent duplicate execution/delivery.
- Manual execution and failure rerun are auditable Job Runs and do not move the regular schedule. Failures remain visible in Job Run history. Persistent System Health and escalation are deferred.
- Automation rules select only application-registered trigger and action names. No database field or user input contains executable code. The sole delivered rule invokes due-reminder evaluation, records an Automation Run and uses ordinary validated services.
- Current automation is non-consequential: it cannot create, edit, archive or delete a canonical Event. Any future consequential action requires separately authorised product design and a user-review boundary.

### iCalendar and externally owned Calendars

- File import is preview-first and confirmation-gated. The bounded standard-library iCalendar 2.0 parser validates UTF-8, unfolding, escaping, structure, stable UIDs and supported all-day recurrence semantics before any write. Unsupported semantics that would be lost—such as alarms, attendees, organisers, attachments, recurrence exceptions or unsupported rule parts—block confirmation.
- Confirmation atomically creates canonical local Events in an explicitly selected existing Calendar or an explicitly requested new Calendar, together with recurrence, source identity, provenance, history and audit. Stable UID/fingerprint identity makes unchanged repeat import a no-op and blocks an unreviewed changed-UID overwrite.
- Calendar export is an all-or-nothing ZIP of independently valid `.ics` members for explicitly selected local or cached external sources. It preserves supported recurrence and stable UIDs; unsupported semantics block the affected export rather than producing a partial or lossy archive. Calendar export is interoperability, not whole-platform backup.
- **Other calendars** are public-HTTPS, read-only iCalendar subscriptions. They are externally owned sources, not local Calendars or canonical Events. Configuration and a last-known-good cache are operational local state so Calendar rendering never waits on WAN access and transient failure does not erase known items.
- Adding a URL validates public destinations and redirects, credentials, size/time limits and content before a no-write preview; explicit confirmation stores configuration/cache. Query values are treated as potentially sensitive and omitted from routine logs/audit notes.
- Conditional refresh uses ETag/Last-Modified where available, validates a changed feed fully, then atomically swaps its cache. Failure retains the last-known-good items and exposes stale/error state without creating an Inbox item. External items remain read-only and gain no Relationships, record-level reminders, Recycle Bin lifecycle or Event history.
- External Calendar settings include name, colour, timezone, ordering, enabled state and Calendar-level Event reminder policy, but no default duration. Removing a source deletes only its configuration/cache. Whole-platform portability includes that operational state without claiming ownership.

### Audit, provenance and portability

Canonical changes use established service validation, audit, provenance and history. Logical deliveries and runtime attempts remain traceable without becoming canonical entities. Whole-platform export/import validates and preserves Phase 2 canonical and operational records; confirmed replacement follows the existing recovery boundary.

## Grouped delivery record

The former workspace contained a line-by-line plan plus 68 expansion entries. This grouped ledger preserves what shipped and where the detailed mechanics now live.

| Date / former entries | Complete delivery |
| --- | --- |
| Initial Phase 2A–2F | Temporal utilities; canonical Event/Calendar services and lifecycle; Relationships/Search/Timeline; Month/Week/Day projections; recurrence and exceptions; reminder policies and Inbox; scheduler/recovery; registry-bound automation; integrated data-quality, migration and portability coverage. The experimental Task and proposal work delivered in the same period was later retired. |
| 2026-07-25 · expansion 2–4 | Local IANA timezone picker; protected Birthdays Calendar; compact Calendar configuration and repeatable Calendar/Event reminder controls. |
| 2026-07-26 · expansion 1, 5–19 | Task UI deferral; consolidated Create event workflow; draggable/dockable quick create; provisional unsaved projection; progressive Description field; session context; recurrence picker and scope dialogs; view dropdown; Calendar-specific sidebar, Mini Month, visibility controls, bounded Month and scrollable Week/Day grids; shared Escape/focus-return fixes. |
| 2026-07-30 · expansion 20–34 | Calendar-only header/navigation, collapsible independently scrolling sidebar, viewport density and live-time marker; dedicated context-preserving Calendar Settings shell; local Calendar settings navigation and minimal creation. Year and Schedule views remained unimplemented follow-ups. |
| 2026-07-30 · expansion 35–45 | Bounded preview-first iCalendar import; explicit destination choice; supported all-day recurrence mapping; loss diagnostics; stable UID identity and atomic apply; selectable all-or-nothing ZIP export; focused route/service/migration/smoke coverage; minimal local Calendar creation. Per-Event export remained deferred. |
| 2026-07-30 · expansion 46–59 | Public-HTTPS read-only Other calendars; safe preview/confirmation; last-known-good cache and conditional refresh; settings/lifecycle; import/export/portability distinction; accessible within-group ordering; view-specific date and ISO-week headings; delivery validation; ownership-grouped settings and Calendar-level external-source reminders. |
| 2026-08-01 · expansion 60 | Data-safe Task retirement through forward migration; current Task services, pages, schema, relationships, reminder contexts and proposals removed. |
| 2026-08-01 · expansion 61–64 | Runtime modules compartmentalised behind stable facades; styles split into an ordered manifest; local fictional README gallery added; shared temporal-occurrence architecture adopted. |
| 2026-08-01 · expansion 65–66 | Inbox/reminder flow consolidated onto temporal occurrences with long-lead Birthday correction, one-active-item migration, exact Event opening/end resolution, persistent Document expiry and direct context-preserving external-Calendar editing. |
| 2026-08-01–03 · expansion 67–68 | Closeout gate, Task-free contract reconciliation, repeatable integrated walkthrough, representative visual/keyboard review, accepted-debt record and owner-authorised milestone closure. |

## Completion evidence and decision

`tests/test_phase_2_closeout.py` reruns the central fictional workflow with disposable databases:

```text
Project + People + Location
→ related recurring Event with one occurrence exception
→ protected Birthday recurrence
→ Calendar reminder default plus Event override
→ one deduplicated local Inbox delivery
→ startup recovery and registered automation
→ separate Job Run, Automation Run, Inbox/action and audit identities
→ distinct cancellation, archival, recycle/restore and permanent deletion
→ validated whole-platform export/import round trip
```

The 2026-08-01 evidence revision passed 287 tests, compile checks, focused migration/runtime tests and the integrated walkthrough. The 2026-08-03 status alignment again passed 287 tests, compilation, diff checks and artifact inspection. The detailed results and reviewed revision remain in [Phase 2 Closure Review](reviews/phase_2_exit_review.md).

Representative agent-driven desktop review covered Calendar Month/Week/Day, Calendar Settings, Inbox, Scheduled Jobs and Deterministic Automation at 800 × 600, 1440 × 900 and 1920 × 1080 in both supported colour schemes. The accepted low-severity constrained-Calendar Search accessible-name limitation remains in the technical-debt register.

The owner accepted:

- closure as a representative development milestone while ordinary maintenance continues;
- the delivered Calendar/Event, reminder/Inbox and local runtime experience;
- the live technical-debt register as non-blocking;
- deferral of System Health, future work management, mobile workflows, external notification channels, AI and autonomous effects;
- final Phase 2 closure on 2026-08-03.

Publishing or merging the `dev` history remained a separate repository action and was not implied by milestone closure.

## Explicit exclusions and unresolved choices

Phase 2 did not deliver or authorise:

- AI/agent/chat workflows, autonomous external effects or automatic canonical Event mutation;
- user-authored executable automation, visual workflow canvases or executable code stored in SQLite;
- external workers, queues, service managers or launch/termination control;
- email, SMS, push, operating-system notifications, authenticated Calendar accounts/APIs, CalDAV, two-way sync or external write-back;
- Persistent System Health, issue escalation or approval infrastructure;
- any current Task/to-do/work-management capability;
- replacement of the Relationship model or Project ownership of related records;
- converting every dated record or projection into an Event;
- actual Event start/end tracking or unbounded point-in-time timed Events;
- phone/mobile workflows;
- Agenda/Schedule or Year Calendar views, direct Week-slot creation, drag-reschedule or Event resizing;
- per-Event iCalendar export or lossy interchange of unsupported semantics;
- destructive automatic Inbox retention or repeated unchanged-condition/success notifications;
- unspecified scheduled maintenance beyond registered reminder delivery and external-Calendar refresh.

Future work management requires a fresh authorised design. Additional occurrence providers should join the shared pipeline rather than add domain-specific scanners. New scheduled maintenance needs an explicit source, trigger, identity and catch-up contract. Consequential automation requires a separately authorised review design. These are future choices, not incomplete Phase 2 commitments.
