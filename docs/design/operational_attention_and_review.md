# Operational Attention and Review

Status: Target standard for increasingly important operational workflows. Phase 1 supplies review precedents, but the inbox, persistent system-health surface, scheduler and general approval infrastructure described here are planned Phase 2 behaviour, not delivered features.

## Purpose and authority

Project E should show the useful results of background work without becoming noisy or interrupt-driven. This document applies the Experience Philosophy's “alive, not chaotic” and human-approval principles together with the accepted Phase 2 distinctions in ADR-013 through ADR-019. The Inbox and reminder foundation remain planned Phase 2 work; Persistent System Health and escalation are deferred until concrete condition producers and user actions are separately authorised.

The central rule is semantic separation:

```text
Reminder policy → may produce → actionable notification
Persistent issue → one durable current condition
Audit event → historical fact
Job run → execution attempt and result
Review item → proposed consequential decision
```

These may link to one another, but one generic notification table or badge must not flatten them into the same concept.

## Current precedents

Established Phase 1 patterns provide evidence for the target design:

- The inference queue presents one suggestion at a time with reason, evidence chain, Confirm, Reject and undoable history.
- Duplicate warnings retain user control through candidate links and explicit Save anyway.
- Import and merge provide previews before consequential apply.
- Data Quality shows explainable findings with disposition actions.
- Audit and real-world Timeline are kept separate.
- Recycle Bin and permanent delete distinguish reversible from irreversible consequences.

The delivered Phase 1 shell now has shared success, notice, warning and error presentation, including a passive save toast and quiet record warnings. It still has no system inbox, persistent-issue surface, cross-tool severity vocabulary or global attention placement. Those remaining capabilities belong to the Phase 2 attention foundation, not to scattered notification cards in current pages.

## Attention model

### Actionable notifications

An actionable notification tells the user that something happened or needs a decision. It persists until acknowledged, dismissed, snoozed, resolved or otherwise acted upon.

Examples:

- a due reminder;
- an overdue Task;
- an approval or import requiring review;
- a failed background job requiring intervention;
- an expiring Document requiring a decision;
- a one-off recovered item that became due while the app was unavailable.

Every item includes:

- plain-language title;
- why attention is needed;
- source record or process;
- original occurrence/due time and creation/delivery time where different;
- severity or priority only when it affects ordering or response;
- one primary action and restrained secondary actions;
- current state and relevant provenance.

### Persistent issues (future)

A persistent issue represents a future condition that remains true: invalid storage path, unavailable optional service, missing reference data, unhealthy recurring job or configuration problem. It is not part of the Phase 2C or Phase 2D implementation scope.

- Maintain one current issue per deduplication key.
- Update that issue as state, severity or evidence changes.
- Do not create a new inbox item every day merely because it remains unresolved.
- Create or update actionable attention only when first detected, materially worsened, newly actionable, escalated at a defined threshold or resolved in a way worth acknowledging.
- The System Health surface lists current issues and recent meaningful transitions.

### Review items and approvals

A review item presents a proposed consequential change that is not canonical until confirmed.

- Show current state, proposed state, source/evidence and consequence.
- State whether confirmation is reversible and what recovery or undo exists.
- Confirm applies through normal validation, provenance and audit boundaries.
- Reject records a reason or disposition when it prevents useless resurfacing.
- Defer/snooze changes attention timing, not the proposal's factual content.
- Batch review may show one decision at a time when evidence is complex; bulk approval is allowed only for demonstrably low-risk homogeneous items.

The inference queue is the strongest current example. Its “one suggestion at a time” pattern should not be applied automatically to simple acknowledgements or homogeneous low-risk lists.

### Background completions

Routine success should usually appear in recent activity or process history rather than the inbox. Promote a completion to attention only when the result is valuable now, needs acknowledgement, changed important information or provides a requested briefing.

Examples:

- Successful scheduled integrity scan with no findings: activity/history only.
- Import validation completed and awaiting confirmation: actionable review.
- Background export completed after an explicit user request: transient success plus accessible output link; optional history.
- Repeated job failure: persistent issue plus one appropriately escalated notification.

## Reminders are behaviour, not entities

A reminder is a policy attached to an Event, Task or derived occurrence, potentially governed by a global default and entity override. It must not appear as a standalone domain in the sidebar or page catalogue.

```text
source fact → occurrence → reminder policy → override → notification delivery
```

The interface places reminder controls with the relevant Event, Task or source-policy context. The system inbox may present the resulting attention item. Dismissal or snooze operates on delivery/attention state and does not silently change the underlying Event, Task or source fact.

## System inbox

The inbox is an operational queue, not a social-notification feed.

### Placement

- Reachable from a restrained global header indicator and the operational navigation group once implemented.
- Home may show a restrained Inbox link with a small count/ticker for all active, not-dismissed items; the Inbox remains the canonical attention destination. Dismissal, resolution and conversion to a task are deliberate state changes, not merely hiding the count.
- Entity pages may show related attention in context, but the canonical item remains in the inbox model.

### Organisation

- Default order combines urgency, due time and severity using a documented deterministic rule.
- Group by meaningful state such as Needs decision, Due/overdue, Failed, and Informational acknowledgement; do not create numerous arbitrary categories.
- Filters include state, source kind, severity and age only when useful.
- Counts include only items that meet the named state, for example `4 need review`.
- A resolved/acknowledged history is searchable but does not crowd the active queue.

### Item actions

Possible actions include Open source, Review, Approve, Reject, Resolve, Acknowledge, Dismiss, Snooze and Convert to Task. Each item exposes only actions valid for its semantics. “Mark all read” is not a substitute for resolution.

Snooze must retain the original due time and record the chosen next-attention time. Dismiss must not resolve a persistent issue or mutate a source fact.

## Severity and prioritisation

Use the smallest vocabulary that changes treatment:

| Level | Meaning | Typical treatment |
| --- | --- | --- |
| Critical | Immediate risk of data loss, security failure or blocked essential operation | Persistent prominent warning; top ordering; explicit action |
| High | Important action is overdue or a significant workflow is failing | Inbox and contextual warning |
| Medium | Timely review prevents degradation or improves important information | Normal inbox priority |
| Low | Useful non-urgent action or acknowledgement | Lower inbox order or activity summary |
| Informational | No action required | Activity/history, not active attention by default |

Severity is not a proxy for recency. Priority can also reflect due time and user consequence. Colour reinforces the label but never replaces it.

## Persistent warnings

- Show a persistent warning at the narrowest level that contains the problem: field, entity, subsystem or platform.
- Platform-wide banners are reserved for conditions affecting most work or data safety.
- A dismissed banner cannot hide an unresolved critical issue indefinitely; dismissal and issue resolution are separate states.
- Repeated rendering of the same issue in header, Home, entity page and System Health should use one source and coordinated presentation, not independent messages.
- Optional WAN map resources being unavailable should not make the whole platform appear unhealthy; local workflows remain available and the warning belongs with the map or optional-service health detail.

## Transient messages

Transient messages confirm immediate interaction outcomes or local failures. They do not replace durable attention.

### Types

- **Success:** action completed and the result is not otherwise obvious.
- **Information:** neutral local state change or guidance.
- **Warning:** action completed or can proceed, but there is a meaningful caution.
- **Error:** action failed or was blocked; explain recovery.

### Behaviour

- Message text names what happened and, for errors, what the user can do.
- Messages are announced accessibly without stealing focus for routine success.
- Error messages do not auto-dismiss.
- Success may auto-dismiss only after sufficient time and when a persistent resulting state is visible.
- Navigation redirects may carry one message, but a refresh must not replay it indefinitely.
- Message styling must use the shared semantic message pattern; route-specific notice classes are not a substitute for it.

## Avoiding system noise

Before requesting attention, ask:

1. Can the user take a useful action now?
2. Is the information new or materially changed?
3. Is there already an active item for the same condition?
4. Is this better represented in activity history or System Health?
5. Does the item identify source, consequence and next action?

Deduplication keys, suppression and escalation rules are product behaviour, not optional polish. Repeated unchanged issues, routine success, novelty messages, marketing prompts and requests to “review Project E” have no place in the inbox.

## Review workflow layout

A consequential review page uses this order:

1. Decision title and affected record/process.
2. Concise reason attention is needed.
3. Evidence or source chain.
4. Current versus proposed outcome where applicable.
5. Warnings, dependencies, reversibility and recovery.
6. Primary confirm/approve action and secondary reject/defer/cancel action.
7. Relevant history or provenance behind progressive disclosure.

Do not place approve/reject controls before the user can inspect evidence. Do not hide the consequence in generic help text.

## Home summaries

Once attention capability exists, Home answers “What should I know?” and “What should I do?” through curated sections:

- Needs attention now.
- Upcoming time-sensitive items.
- Recent meaningful background outcomes.
- Persistent system-health summary only when non-normal.

Favourites, recent entities and domain launch actions remain secondary. The dashboard is not configurable until real use demonstrates alternative valid priorities.

## Accessibility and trust

- Live regions announce only immediate relevant changes, not entire queue refreshes.
- Focus moves to review content after an explicit Open/Review action, not when background work finishes.
- Counts and badges have accessible names and exact scope.
- Review evidence, consequence and actions follow a logical reading/focus order.
- Time labels expose full timestamps where relative wording is used.
- Approval never occurs through an unlabeled icon or ambiguous swipe/gesture.

## Implementation acceptance checks

- Reminder policies remain attached behaviour and never become a standalone entity domain.
- Inbox items, persistent issues, audit events and job runs have separate records and UI language.
- One unchanged condition cannot generate repeated noise.
- Consequential reviews expose evidence, current/proposed state, consequence and recovery before confirmation.
- Routine success stays out of active attention.
- Transient errors remain until understood or dismissed and preserve a recovery path.
- Home attention summaries link to canonical filtered queues.
- All background-originated consequential mutations retain explicit user approval.
