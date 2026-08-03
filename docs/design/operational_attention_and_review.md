# Operational Attention and Review

Status: Current Inbox, reminder, execution-history and review UI contract. Persistent System Health and general approval infrastructure are deferred product concepts, not current records.

## Semantic separation

| Concept | Meaning | Current surface |
| --- | --- | --- |
| Reminder policy | When a traceable occurrence should attract attention. | Source/Calendar settings. |
| Inbox item | Durable actionable attention for a due condition. | Inbox active queue and Archive. |
| Audit event | Historical fact about a platform mutation or disposition. | System Audit. |
| Job/Automation Run | One execution attempt/outcome. | Respective System Tools histories. |
| Review proposal | A non-canonical consequential change awaiting decision. | Focused review workflow, such as inference. |
| Persistent issue | One future current system/configuration condition. | Not implemented. |

These records may link but never collapse into one generic notification table, badge or activity stream.

## Reminders and Inbox

A reminder is behaviour attached to an Event, Calendar, external Calendar or supported occurrence source. It is not an entity or navigation domain:

```text
source fact → temporal occurrence → reminder policy/override → Inbox delivery
```

The source owns its date. Dismissal and snooze change attention state, not the source fact. A lifecycle or material schedule/policy change reconciles future and active attention while retaining history.

The current Inbox is a chronological active reminder queue with a semantic navigation count and separate Archive/deep history. One source occurrence/reason has at most one active or snoozed item; a newly due timing replaces older visible attention while delivery/action history remains. There is no manual evaluation control or separate Upcoming projection.

- Event-like items offer exact-occurrence **Open event**, **Dismiss** and accessible **Snooze 10 minutes**. Opening or occurrence end resolves current attention.
- Document-expiry items offer **Open document**, **Dismiss** and **Snooze 10 minutes**. Opening or passing the date does not itself resolve the condition.
- Counts include only their named visible state and disappear at zero.
- Routine successful Jobs and Automations remain in execution history, not Inbox.

## Attention and noise

Request attention only when the user can take useful action now or understand a material change. Every item names why attention is needed, its source, relevant due/delivery time, current state and one primary action. Severity appears only when it changes ordering or response and never relies on colour alone.

Before creating attention, ask:

1. Is it actionable or materially changed?
2. Is an item already active for the same logical condition?
3. Would execution/audit history communicate it better?
4. Are source, consequence and next action clear?

Repeated unchanged conditions, routine success, marketing prompts and novelty messages do not belong in Inbox.

## Review workflows

A proposed consequential change is not canonical until confirmed. A review presents:

1. affected record/process and reason;
2. source/evidence;
3. current and proposed state;
4. consequences, dependencies, reversibility and recovery;
5. clear confirm plus reject/defer/cancel as applicable;
6. relevant history behind disclosure.

Confirmation uses normal validation, provenance, audit and recovery. Rejection records disposition when needed to prevent unchanged resurfacing. Snooze changes review timing, not proposal content.

Family inference is the current specialist pattern: show one suggestion with people, rule, evidence chain and Confirm/Reject; archive completed batches; allow Undo; and keep confirmed Relationships ordinary and editable. One-at-a-time review is not automatically appropriate for simple or low-risk homogeneous decisions.

## Messages and warnings

Transient success/information/warning/error messages explain the immediate interaction and do not replace durable attention. Routine success may fade only when the result remains evident; errors persist with recovery guidance. Messages are announced without stealing focus or replaying indefinitely after refresh.

Persistent warnings appear at the narrowest useful field, record, subsystem or platform scope. Optional WAN failure stays local to the affected map/service rather than making the whole platform appear unhealthy. A future persistent-issue model would deduplicate one current condition and expose meaningful transitions; it must not be improvised through repeated Inbox items.

## Accessibility and trust

- Counts and badges have exact accessible scope.
- Review evidence, consequence and actions follow logical reading and focus order.
- Focus moves after an explicit Open/Review action, never because background work finished.
- Relative times expose full timestamps.
- Approval never occurs through an unlabeled icon or ambiguous gesture.
- Live regions announce relevant local changes rather than entire queue refreshes.
