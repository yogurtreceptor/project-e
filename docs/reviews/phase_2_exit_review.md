# Phase 2 Candidate Closure Review

Reviewed 2026-08-01. Evidence revision: `e3b5c2922edc2537f4f14e3524d7908dbcb60f10`.

This is the candidate closure review for Phase 2. It records the integrated repository and agent-driven desktop evidence presented to the owner. Phase 2 remains active, PR #6 remains draft and the closure decision remains pending until the owner accepts the delivered experience and conditionally authorises the final status changes and merge.

## Delivered boundary

The reviewed product is Task-free. It delivers canonical Events and Calendars; relationships to People, Organisations, Locations, Projects, Documents and Assets; recurrence and occurrence exceptions; Calendar and Event reminder policy; durable local Inbox deliveries and actions; serial in-process scheduling; registered deterministic automation; audit and provenance; Event lifecycle controls; and whole-platform portability.

The sole current registered automation invokes the reminder-delivery service. Rules are selected from an application registry, contain no database- or user-authored executable code and cannot create, edit, archive or delete a canonical Event. Persistent System Health and any future consequential automation, including its review or approval infrastructure, require separate authorisation.

## Integrated walkthrough

`tests/test_phase_2_closeout.py` reruns the walkthrough with temporary databases, a temporary export bundle and fictional records only. It removes those temporary artifacts after the test.

| Evidence | Result |
| --- | --- |
| Integrated identities | One Event was related through the normal Relationship system to one Project, two People and one Location. |
| Temporal behaviour | Weekly recurrence produced an occurrence with an explicit exception; a Birthday Event retained yearly recurrence. Existing focused Document-expiry coverage remains in the repository suite. |
| Reminder precedence | A one-hour Calendar default and a 30-minute Event override were combined; the override delivered and suppressed the applicable default. |
| Recovery and automation | Repeated startup recovery returned one delivery and then no further delivery. One scheduled Job Run invoked one registered Automation Run. |
| Identity separation | Job Run, Automation Run, Inbox item, Inbox action and audit event remained separate records with their own identities and references. |
| Safety boundary | The canonical Event row and its entity-audit count were unchanged by automation; the registry and persisted rule schema exposed no executable-code field. |
| Lifecycle distinction | Separate fictional Events demonstrated cancellation, archival, Recycle Bin restoration and permanent deletion without conflating those states. |
| Portability | The integrated source database exported and validated, then imported into another empty database with representative identities, relationships and operational history preserved. |

## Automated verification

The evidence revision passed focused automation, scheduler, System Tools, migration and closeout-walkthrough tests. It also passed the complete repository suite of **287 tests**, `python3 -m compileall app run.py tests` and `git diff --check` on 2026-08-01.

Final verification must be rerun after the approved status edits. The final review will record that revision and result before merge.

## Desktop visual and keyboard review

The application ran against an isolated fictional database on a temporary local port. Agent-driven browser inspection covered 48 route, viewport and colour-scheme combinations: Calendar Month, Week and Day; Calendar Settings hub and General Calendar Settings form; Inbox; Scheduled Jobs; and Deterministic Automation at 800 × 600, 1440 × 900 and 1920 × 1080 in light and dark schemes. Screenshots and the machine-readable inspection report were kept outside the repository.

| Check | Result |
| --- | --- |
| HTTP and rendering | Pass: all 48 combinations rendered successfully; no failing HTTP status was observed. |
| Clipping and overlap | Pass: no page-level horizontal overflow was observed; inspected constrained and ordinary layouts had no blocking overlap. |
| Calendar scrolling | Pass: Week and Day grids retained independent horizontal and vertical scrolling at the constrained baseline. |
| Keyboard focus | Pass with accepted limitation: representative tab sequences retained visible focus and logical progression; short pages cycled after their final control. |
| Accessible activation | Pass: keyboard activation opened Create Event and Add Calendar and navigated to the Inbox Archive. |
| Return context | Pass: Calendar Settings preserved the originating Month date and selected-Calendar query context. |
| Status and history | Pass: Inbox, Scheduled Jobs and Deterministic Automation states and histories remained readable across the inspected baselines and schemes. |

One new low-severity limitation was identified: at exactly 800 × 600, the Calendar header's global Search link loses its accessible name because its visible text is hidden and its icon is decorative. Wider desktop layouts retain the visible label. The limitation is recorded in `docs/reviews/technical_debt_register.md` and is accepted as non-blocking for this closeout; it does not make Calendar content or search activation unreachable.

## Accepted debt and exclusions

The owner accepted the complete current technical-debt register as non-blocking on 2026-08-01, including collapsed-sidebar discoverability, visually noisy high-frequency runtime history and the constrained-Calendar Search accessible-name defect discovered during this review. These items remain ordinary maintenance work and do not represent hidden Phase 2 features.

Persistent System Health, future work management, phone/mobile workflows, external notification channels, AI, autonomous external side effects, arbitrary executable automation and automatic canonical Event mutation remain excluded. Phase 3 remains undefined and is not a prerequisite for closure.

## Owner decisions and candidate conclusion

- **Milestone meaning — accepted 2026-08-01.** Phase 2 may close as a completed development milestone while ordinary maintenance and residual defects continue without reopening it.
- **Delivered experience — pending.** The owner must review this evidence and confirm that the current Calendar/Event, reminder/Inbox and local runtime experience has enough practical polish to leave in place.
- **Accepted debt — accepted 2026-08-01.** The current debt register is non-blocking for closure.
- **Deferred boundary — accepted 2026-08-01.** The exclusions above remain outside Phase 2.
- **Final closure — pending.** The owner must conditionally authorise marking Phase 2 complete and merging PR #6 if final verification passes and the tested revision matches the PR head.

The repository evidence supports Phase 2 closure, but this candidate review does not itself close the phase. No completion status, ready-for-review state or merge gate may change until the two pending owner decisions are recorded.
