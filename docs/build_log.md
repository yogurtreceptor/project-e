# Build History

Historical summary only. Current behaviour is defined by the implemented code and reference documents; phase plans and the roadmap define authorised boundaries and direction but do not themselves authorise implementation; the technical-debt register contains unresolved work.

## 2026-08-01

### Runtime architecture compartmentalisation

- Split server configuration, top-level routing, HTTP transport support and Event-form parsing into focused modules while preserving the existing local web surface.
- Centralised stable product defaults, isolated route-test servers without mutable global handler state, separated entity lifecycle orchestration from persistence and removed cyclic service imports through a focused Inbox repository.

### Experimental Task subsystem retirement

- Verified that the local runtime database contained no canonical Task records or Task-linked operational data, then removed the dormant Task services, pages, routes, relationships, reminders, automation proposals and legacy skipped tests.
- Added a forward retirement migration that removes Task schema artifacts while preserving historical migration IDs and refusing to proceed when Task data exists.
- Reframed future work management as a fresh product-design decision rather than a compatibility obligation.

### Documentation consistency audit

- Reconciled phase status wording and replaced stale prototype shell, branding and scheduler descriptions with the implemented Project E contracts.
- Reclassified the completed design catch-up plan as historical evidence rather than current implementation authority.

## 2026-07-30

### Calendar interchange, subscriptions and date context

- Added preview-first, repeat-safe all-day iCalendar import into an existing or explicitly new local Calendar, plus selectable all-or-nothing ZIP export with one ordinary iCalendar member per local or cached external source.
- Added safe public-HTTPS Calendar subscriptions as independently ordered, read-only Other calendars with conditional refresh and a last-known-good non-canonical cache.
- Split Calendar Settings navigation into **Settings for my calendars** for local ownership and **Settings for other calendars** for individually managed URL Calendars, removing the generic visible Subscriptions collection.
- Added applicable Other-calendar editing for name, colour, timezone and Calendar-level notifications while retaining read-only source items and omitting local-only default Event duration.
- Reduced Calendar creation to name and colour, moved ordering to accessible drag-only sidebar interaction, and added view-specific date headings plus ISO week context and the Month week-number rail.
- Updated portability validation to recognise the required active default separately for each Calendar kind.

### Calendar settings workspace

- Activated the Calendar settings cog and added a stripped-back, context-preserving settings shell with a narrower navigation sidebar.
- Moved existing local Calendar creation, editing, notification defaults and lifecycle controls into the settings workspace, with rapid colour-and-name switching between active Calendars and retained access to archived Calendars.
- Added the General and calendar-discovery placeholders and the navigation destinations subsequently activated for From URL, Import and Export.

### Calendar shell and live-time refinement

- Moved Today, previous/next and the anchor date into the main Calendar column of the Project E header; grouped view selection immediately left of the settings affordance beside Search.
- Replaced the Calendar management toolbar link with collapsible My calendars and Other calendars groups plus one Other-calendars creation control; disclosure arrows sit at the right of each heading and the Calendar sidebar scrolls independently.
- Removed the remaining inset between the Calendar projection and its header/sidebar boundaries.
- Made Month consume its fixed Calendar viewport without page-level vertical scrolling while retaining independently scrollable 24-hour Week and Day grids.
- Added a timezone-aware current-time dot and red line to the present day in Day and Week, updating once per minute without changing Event records.

## 2026-07-26

### Calendar consolidation and viewport density

- Added the Event-focused Calendar sidebar structure: Create event, Mini Month, My calendars and a visual-only Other calendars section reserved for later supplied, imported or derived sources.
- Moved Calendar visibility selection into My calendars, removed the duplicate toolbar Event-create action, and kept Calendar management as the secondary toolbar destination.
- Bounded Month-day rendering to three Event entries with a context-preserving `+ N more` Day link; Week and Day now keep their complete time grids in a height-bounded scroll region with sticky orientation and an initial 07:00 viewport.
- Added shared Escape/focus-return handling for native action menus and corrected dirty-form cancellation to restore its invoking link.
- Corrected My calendars checkbox/name alignment and removed the unused derived-and-related-dates Calendar panel to preserve projection space.
- Made Calendar visibility toggles immediate without reload and added per-Calendar vertical-ellipsis edit links.

### Calendar mini month picker

Added the Calendar sidebar's first local control: a compact, six-week Monday-first month picker with ISO weeks, adjacent-month dates, distinct current/selected states and keyboard navigation. Its month browsing is independent of the main Calendar view; selecting a day navigates the main Calendar. Create Event now sits immediately above it.

### Calendar sidebar reservation

The Calendar projection now retains an empty left sidebar as a dedicated future Calendar workspace; standard Browse navigation continues unchanged everywhere else, and Calendar quick-create can still dock into the reserved region.

### Calendar view dropdown

Replaced the separate Month, Week and Day controls with an active-view dropdown that preserves Calendar context when changing projections.

### Task work-management deferral

Retained Task storage, migrations, services and validation for a future user-led to-do redesign, while removing Task routes and navigation plus Task search, Calendar, Project, Inbox-reminder and automation integration so Phase 2 can focus on Events.

### Phase 3 note collection

Moved the tentative local-first journey-planning proof slice out of Phase 2 closeout requirements and into a new informal Phase 3 notes document for future assertions and open questions.

### Event recurrence picker

Added the requested preset recurrence button menu to the full Event create and edit forms, including daily, calendar-aware weekly/monthly, annual and weekday rules. Added the Custom recurrence editor with interval/frequency, weekday patterns, date-derived monthly choices including last weekday where applicable, and Never/on-date/after-occurrence endings. Editing or deleting an individual recurring occurrence now asks its scope only when Save or Delete is pressed, using a selectable scope list with Cancel and OK. Quick create remains intentionally compact.

### Calendar session context

The active Calendar Month/Week/Day context is now retained in browser session state for navigation and is preserved through Event preview edit, save, cancel and delete flows without adding a stored user preference.

### Calendar context preservation

Calendar creation now retains the current Month, Week or Day view, anchor date and visible-Calendar filter after Event creation and through the More options handoff.

### Calendar quick-create refinement

- Replaced modal quick-create dialogs with non-modal, draggable Event and Task panels that can dock into the sidebar without obscuring the Calendar.
- Added provisional Calendar rendering for the unsaved Event schedule and replaced Event/Task Notes form controls with progressive, autosizing Description fields while retaining canonical notes storage.

### Calendar quick creation

- Added in-calendar Event and Task quick-create popups with close controls, direct save actions and a More options handoff that preserves entered values in the existing complete forms.
- Kept Event and Task creation local and canonical: quick save uses the existing services and returns to Calendar with a confirmation.

### Calendar creation menu

Replaced the Calendar page's separate Add Event and Add Task buttons with one native Create menu that links to the existing Event and Task creation forms.

## 2026-07-25

### Birthdays Calendar and calendar-level defaults

- Added the protected built-in Birthdays Calendar and migration-safe Person-to-Event links. A Person birthday now owns one canonical yearly all-day Event, synchronised through edits and Person archive/restore lifecycle.
- Moved birthday reminder defaults from the Inbox/global-derived context into Birthdays Calendar settings, preserving existing configured timing values during migration.
- Prevented ordinary Event creation and direct mutation of Person-synchronised birthday Events, while keeping Birthdays visible and configurable as a Calendar.

### Phase 2 timezone selector and workspace expansion

- Moved Calendar Event-notification defaults onto the Calendar edit form. Replaced every comma-separated reminder entry form with repeatable integer-and-unit controls, including client-side add/remove rows and server-side ten-notification limits for Calendar defaults and effective Event reminders. Removed Calendar/Event policy-state pickers so empty Event-specific rows inherit the linked Calendar; registered the row-control script with the local static handler.
- Refined Calendar management with compact circular colour controls and Calendar-level local Event-notification controls.
- Replaced free-text timezone entry in Calendar, Event, Task deadline and Task-session forms with a shared local searchable, scrollable IANA selector, including current UTC-offset and country search labels.
- Preserved stored IANA identifiers and UTC instants; the selector derives its local labels from the installed timezone database without a network or schema dependency.
- Renamed the Phase 2 plan to `phase_2_workspace.md` and established it as the living Phase 2 refinement record until Phase 3 is defined.
- Recorded deferred, versioned browser caching for growing local static assets; current local SVG, CSS and script requests remain intentionally simple.
- Refined the timezone control into a collapsed combobox so its `Australia/Brisbane` default is visible without showing choices or search guidance until the field is opened or edited.

### Phase 2E/2F deterministic automation and closeout

- Added a migration-safe, registry-only trigger-condition-action layer with durable idempotent Automation Runs, audit/provenance and System Tools rule controls.
- The built-in reminder scan now delivers due reminders and identifies overdue Tasks; an opt-in Document-expiry action creates approval-gated Task proposals. Approval calls the normal Task service and rejection is retained.
- Added non-Event Calendar projections for Task temporal facts, birthdays, Document expiries and Project targets, plus operational data-quality checks.
- Completed Phase 2 integration verification for scheduler recovery, automation approvals, recurrence/temporal behaviour, portability and local workflows. Persistent System Health and escalation remain deferred.

### Phase 2D local scheduler foundation

- Added SQLite-backed registered scheduled jobs, Job Runs, transactionally claimed leases and durable startup/clean-shutdown checkpoints through a replaceable in-process runtime boundary.
- Registered the single initial `reminder-delivery` job on a one-minute coalesced schedule. Application startup reactivates next-open snoozes and performs one serial due scan, preserving the Phase 2C reminder catch-up and deduplication rules.
- Added System Tools visibility and controls for job state, recent runs, manual execution, failed-run rerun and enable/disable. Manual executions are independently auditable and do not shift the normal schedule.

### Agent guidance refresh

- Updated repository guidance for the completed Phase 1 and active Phase 2 context, including the explicitly authorised local deterministic scheduling and automation boundary.
- Added concise run, verification and code-routing guidance while preserving the existing repository-first, documentation, privacy and confirmation rules.
- Aligned the contributor workflow with the current phase documentation and added explicit routing to the Phase 2 plan and security policy.

### Documentation consolidation

- Standardised current documentation on Phase terminology and renamed the delivered Information Platform reference to `phase_1_spec.md`.
- Made the Phase 2 plan the detailed status authority; aligned product, architecture, ontology and design documentation with completed Phases 2A–2C and the next Phase 2D runtime work.
- Reclassified completed design/form plans as historical records, corrected Phase 2 subphase numbering, and restored reverse-chronological build-history order.

### Phase 2C closeout

- Closed Phase 2C with durable local reminder delivery, Inbox actions/history, contextual policies, recurring scopes, lifecycle suppression, retention tiers and fixed catch-up rules; scheduling and startup recovery remain Phase 2D.

## 2026-07-23

### Phase 2B closeout

- Added read-only Project overview projections for related upcoming Events and open Tasks through the standard Relationship graph.
- Closed Phase 2B work management; Projects remain coordination hubs rather than owners of Event or Task records.

### Phase 2B Task temporal values

- Added optional all-day and timed/timezone-aware Task deadlines plus repeatable all-day or bounded timed planned sessions through the shared temporal contract.
- Added Calendar Task deadline/session projections with neutral Task treatment; completion permanently removes future sessions while preserving past session history.

### Phase 2C reminder and Inbox foundation

- Added forward-only SQLite storage for reminder policies, record/occurrence overrides and durable local Inbox deliveries with database-enforced delivery identity.
- Implemented deterministic manual evaluation for Event, Task-deadline, birthday and Document-expiry reminders, including Brisbane all-day anchors, February-29 birthday handling, default timings, task-overdue delivery and Inbox acknowledge/dismiss/snooze actions.
- Added the Inbox navigation surface; scheduler-driven delivery and startup recovery remain deferred to Phase 2D.
- Extended manual evaluation to materialise current derived recurring Event occurrences and forthcoming birthday lead times; Event and Task record pages now expose default/custom/disabled reminder settings with additive and suppressive timings.
- Added local Calendar, Task-list and global derived-source reminder-default controls, including explicit restoration to inherited defaults.
- Recorded timing tokens on future Inbox deliveries so a policy edit resolves only superseded pending reminders; disabling a reminder resolves all of its pending attention.
- Connected recurring Event reminder settings to the existing this-occurrence, prospective-series and whole-series scopes, including source-delivery resolution when an occurrence moves to a successor series.
- Added a non-materialising Upcoming reminder preview, urgency-led active Inbox ordering, and the specified 500-item paged Archive with a separate deep-history view.
- Added append-only Inbox delivery-transition history for local delivery, user attention actions, source lifecycle resolution, policy reconciliation and recurring-series changes.
- Exposed each archived Inbox item's delivery-transition history for local inspection.
- Completed reminder lifecycle suppression for recycled Events and changed recurring Event occurrences.

## 2026-07-20

### Phase 2B Task foundation

- Added canonical Task and Task-list storage through a forward-only migration, including the seeded default Tasks list, active-list assignment checks, completion timestamps and independent archive state.
- Added dedicated Task/List services, normal audit/provenance and Recycle Bin/Search integration, plus pair-aware standard Relationships to every current peer entity.
- Added Calendar-originated undated Task capture and a dedicated Tasks view for organising, moving, completing, reopening and archiving work; Task deadlines, sessions and Calendar/Project projections remain the next Phase 2B milestone.

## 2026-07-19

### Phase 2A closeout

- Added Calendar management for creating, editing, ordering, selecting the default, archiving, restoring and safely deleting Calendars through the existing audited services.
- Added occurrence-aware Event editing and deletion scopes: this occurrence persists an override or cancellation exception, this-and-following creates or truncates a traceable series boundary, and all occurrences retains canonical Event mutation.
- Recorded recurrence definition, exception and series operations in Event history, audit and provenance; Phase 2A functional requirements are complete.

### Calendar management services

- Added validated Calendar listing, retrieval, creation, rename/configuration, ordering, active-default selection, archive/unarchive and empty-only deletion services with audit, provenance and append-only Calendar history.
- Defined archive safety: Events retain their archived-Calendar assignment, archived Calendars cannot receive new assignments, and no automatic or bulk Event reassignment occurs.
- Added a forward-only Calendar-history migration plus fresh and upgrade schema coverage.

### Timed Calendar grids

- Replaced the Week projection's timed-event list columns with an hourly time grid, with weekday/date headers and a labelled time axis.
- Added the matching Day projection; timed Event intervals display as duration blocks and overnight intervals continue in each affected display day.

### Event recurrence foundation

- Added migration-safe Event series definitions, deterministic derived occurrences and versioned cancellation exceptions without duplicating canonical Event records.
- Added daily, weekly, monthly and yearly recurrence generation with bounded end dates and documented month-end backward shifting, plus initial recurrence controls in Event editing.
- Added selected/ordinal weekday controls and traceable successor-series split operations; occurrence-specific edit/delete controls remain for the separate Event-editor redesign.

### Dedicated Calendar Event forms

- Moved Event creation and editing out of the Calendar projection into dedicated routes; the Calendar now supplies a compact add control and Event previews remain the entry point for edit/delete.
- The Event form now presents either inclusive all-day dates or timed start/end datetimes, avoiding duplicate temporal inputs.

### Week and Month Calendar projections

- Added Monday-first Week and Month projections derived directly from canonical Event intervals, including all-day spans, timed timezone conversion, Calendar-derived colour and cancelled treatment.
- Added non-mutating Calendar visibility filters and compact Event previews that route editing to the Calendar workflow and deletion through the standard confirmed Recycle Bin lifecycle.
- Kept recurrence, direct grid interactions and Day/agenda views deferred.

### Calendar-originated Event creation and editing

- Added the Calendar navigation workflow for human-created Events, with Calendar defaults, all-day and timed scheduling, timezone and optional notes.
- Routed Event detail edits and schedule changes through the existing semantic Event services, and linked relationship work to the shared post-creation/edit workflow.
- Kept Calendar projections, compact previews and recurrence deferred; the initial Calendar currently provides the creation/editing panel and current-Event list.

### Event search and related-record projections

- Added Events to global Search through the existing canonical-record and relationship-context query path, including the Event type filter, without adding search-index or projection storage.
- Added a read-only Event projection reachable from Search and normal related-record links; it exposes Calendar-derived colour, temporal/lifecycle details, relationships and existing change history while retaining the deferred Calendar-originated create/edit boundary.
- Completed the Phase 2A Event integration checkpoint: a related Event can now be found, opened from a peer record and inspected with its history.

### Event relationship integration

- Added pair-aware standard Relationship definitions for Events and every current canonical peer type, including other Events.
- Kept Event links in the shared relationship lifecycle, preserving normal validation, audit, provenance, soft deletion and restoration instead of introducing Event-specific foreign keys.
- Verified one Event can connect to multiple existing peer records while remaining outside the deferred Calendar/Event UI and generic Event creation paths.

### Calendar-only Event model correction

- Corrected the Phase 2 model so every canonical Event belongs to exactly one Calendar and Calendars alone provide Event grouping, colour, defaults, ordering, archive state and filtering.
- Added a forward-only migration that preserves existing Event identities, Calendar links, temporal values and lifecycle state while removing the superseded category-bearing development schema.
- Added dedicated cancellation, reinstatement and rescheduling operations; retained archive state independently from Recycle Bin deletion and verified restoration preserves archive and cancellation.
- Kept reminder storage deferred while recording the broad future precedence of occurrence, Event, Calendar and global policies.

### Phase 2A canonical Event lifecycle

- Added Event as a stable canonical entity type with migration-safe typed storage. Its initial category-bearing grouping was superseded by the Calendar-only correction above.
- Implemented validated timed and all-day creation, editing, cancellation state, archive/unarchive, default resolution, audit, provenance and entity history through a dedicated Event service.
- Kept Event creation out of generic entity routes so the next UI milestone can implement the approved Calendar-originated workflow.
- Extended portable-database validation and System Audit vocabulary for the new Event contract and archive lifecycle.

### Phase 2A temporal foundation

- Began authorised Phase 2 implementation with shared, standard-library temporal normalization for IANA timezones, UTC instants, bounded timed intervals and end-exclusive all-day intervals.
- Added the initial migration-safe temporal reference storage; its extra category layer was superseded by the Calendar-only correction above.
- Covered UTC conversion, invalid/ambiguous daylight-saving times, interval validation, fresh schema creation and existing-database adoption with focused tests.
- Kept canonical Events, Calendar projections, recurrence and reminder precedence for later Phase 2A milestones.

### Phase 2 plan consolidation

- Restructured the canonical Phase 2 plan around Phases 2A–2F, consolidating approved behaviour, architecture, sequencing, completion criteria and exclusions without starting implementation.
- Aligned supporting Calendar and reminder terminology: Calendars are local Event configuration records, while calendar views remain derived projections.

## 2026-07-12

### Phase 2 operational-planning decisions

- Aligned the architecture and design-document status language with the completed desktop shell, theme foundation and representative domain-page conversion; preserved the remaining external human visual and assistive-technology QA as an open verification item.

- Recorded the initial user-centred Event, Calendar, Task, reminder, Inbox, System Health and local archive decisions in the canonical Phase 2 plan.
- Kept Phase 2 implementation unstarted: this session defines authorised future design direction, not delivered product behaviour.

### Design-system route conversion and verification

Completed the authorised design catch-up across the implemented Phase 1 interface.

- Delivered a shared entity frame: breadcrumbs, clear identity and action hierarchy, grouped Views, restrained overflow actions, quiet integrity warnings, and accessible icon-only relationship creation.
- Added deliberate form safeguards: entity edit Cancel returns to the canonical record, dirty entity/relationship/journal forms warn before discard, validation summaries link to invalid described controls, and successful saves show a non-disruptive **Changes saved** toast.
- Built domain-specific Person, Document and Project Overviews. Person addresses derive from Location relationships; Document pages lead with safe open/download actions; Project pages foreground status and milestones.
- Converted indexes, Search, Timeline, Map, Family Tree, relationship workflows and System Tools to shared collection, state, confirmation and semantic-token patterns. Map failure guidance and Family Tree keyboard/text alternatives are included.
- Completed locally executable verification: 182 tests, compilation, temporary-server smoke workflows with fictional data, contrast/token/icon/confirmation audits, and focused structural keyboard checks passed.
- Reconciled the repository documentation: restored chronological build history, aligned design audits with delivered shared feedback and domain compositions, and made known keyboard/sidebar gaps explicit rather than implying acceptance.

Human visual and interactive keyboard review at both target resolutions and themes remains outstanding. The known dirty-form, Views/overflow and collapsed-sidebar accessibility follow-ups are recorded in the technical-debt register.

## 2026-07-11

### Shared design foundation, shell and navigation

- Established the semantic design-token foundation in `foundation.css`: dark fallback with system-selected light theme, one `#66ccff` accent primitive, local/system Roboto fallback, keyboard focus treatment and reduced-motion protection.
- Added shared actions, controls, panels, badges, notices, busy/empty/loading/failure states, linked validation and accessible recoverable-delete confirmation.
- Created the Project E tilted E mark and local 24px SVG icon set, with safe local serving and accessible decorative/meaningful-icon conventions.
- Replaced the prototype header with the persistent desktop shell: Browse sidebar, session-only collapsed state, Search, skip navigation and current-route hierarchy. Added deterministic Super Key Go aliases (`map`, `bin`, and Person-context `tree`) with an explicit Search fallback.
- Recorded the experience philosophy, design-system standards, page catalogue and authorised implementation plan that guided this work.

## 2026-07-05

### Portability, recovery and Phase 1 closure

- Added versioned, checksummed export bundles containing a consistent SQLite snapshot and referenced documents; staged import preview/confirmation; clean-target protection; and recovery backups for import, merge and permanent deletion.
- Added the deliberate command-line recovery workflow, including preview and confirmed replacement modes.
- Preserved and repointed recycled relationships during merge, with previews that distinguish active and recycled effects.
- Closed Phase 1 as a development milestone after representative verification and recorded the planned Phase 2 temporal and deterministic-automation architecture, including the `Australia/Brisbane` platform timezone and a separable in-process scheduler.
- Added contributor, security and copyright documentation.

## 2026-07-04

### Taxonomies, discovery and domain refinement

- Replaced legacy gendered family relationship records through a dry-run-first, backup-protected converter with direction-safe neutral mappings.
- Added a reusable local three-level taxonomy framework and migrated Organisation classification and Relationship types to it, including hierarchy search, direction metadata and audit history.
- Consolidated Search, Data Quality, Taxonomies and Recycle Bin under System Tools while retaining global Search access.
- Cleaned up domain semantics: Documents use relational issuer/creator facts and MIME-backed format; Assets no longer duplicate Document types; Projects gained target dates/timeline events; Organisations gained repeatable aliases.
- Expanded definition-driven progressive disclosure and added targeted typed fields, duplicate matching and timeline/search participation.

## 2026-06-28

### Integrity, provenance and platform services

- Added schema migration tracking, structured-value validation, duplicate detection and preview-first entity merging with edit history.
- Added relationship integrity auditing, exact-duplicate prevention, structured discovery filters, robust Document ownership/cleanup and definition-driven inline entity creation.
- Delivered deterministic, explainable family-relationship inference as reviewable suggestions with provenance, suppression, archived batches and undo.
- Added registry-driven audit/provenance, advanced search, data quality and the Universal Timeline; restored separate entity change history and backfilled legacy audit history.
- Added soft deletion for every entity type, a Recycle Bin, dependency-aware permanent deletion, reference data/unit normalisation, multi-value People reference fields and People journals.

## 2026-06-27

### Maintainable module boundaries

Refactored without changing public contracts: page rendering moved to `app/view_pages/`; persistence was split into schema and repository modules behind `app/db.py`; relationship metadata moved to a grouped catalogue; and document/relationship workflows moved out of the HTTP handler. Added boundary-focused regression coverage.

## 2026-06-22

### Structured forms and relationship workflows

Standardised entity forms and controlled values. Redesigned relationship creation around a named current entity and connected entity, pair-aware canonical relationship types, perspective-correct labels, safe inline creation and date certainty. Added reusable Family Tree graph extraction and deterministic layered SVG layout.

## 2026-06-21

### Initial local information platform

Established the standard-library Python/SQLite application with reusable CRUD definitions, first-class relationships, entity profiles, discovery, favourites, recent records and geography. Added Projects, Documents and Assets through the shared architecture, local Document uploads, and optional Leaflet/OpenStreetMap/Nominatim map support. Early attachment and organisation-address concepts were superseded by first-class Documents and Location relationships.
