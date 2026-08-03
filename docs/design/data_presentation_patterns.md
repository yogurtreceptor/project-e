# Data Presentation Patterns

Status: Current contract for presenting canonical, derived, operational and administrative information. Domain composition belongs in [entity pages and forms](entity_pages_and_forms.md); attention semantics in [operational attention and review](operational_attention_and_review.md).

## Choose by task

| Pattern | Use when |
| --- | --- |
| Table | Repeated records share fields and column comparison or lookup matters. |
| Compact list | A short set needs identity plus limited secondary context. |
| Card | One navigable record, choice, suggestion or summary needs a discrete boundary. |
| Panel | Related static or interactive content needs grouping within a page. |
| Timeline | Chronological facts need their source and precision understood. |
| Graph/map | Spatial or structural relationships are materially clearer visually and retain a text equivalent. |

Consistency means the same task uses the same pattern—not that every record becomes a card. Every view makes clear whether it shows canonical facts, a traceable projection, actionable operational state or administrative history.

## Collections and filters

Tables use semantic headers, stable domain-specific column order and identity in the first column. Dates, numbers, status and actions align consistently. Ordinary density is balanced; compact density is reserved for demonstrated comparison/volume needs. On constrained widths, retain identity/priority columns and use a labelled keyboard-scrollable region rather than automatically converting rows to cards.

Lists and cards do not repeat a nearby table. More than a screenful needs a dedicated view, filter or paging rather than an indefinitely growing panel. Panels use headings/spacing before nested borders.

Filters never mutate canonical data. Keep common controls visible, preserve values in the URL where practical, show active state and result count, and distinguish:

- no records, with an appropriate create action;
- no matches, with Clear filters;
- retrieval failure, with a recovery path.

Sorting and bulk selection appear only where stable meaning and a real workflow justify them. Predefined views answer demonstrated recurring questions; user-saved filter configurations remain deferred until needed.

## Derived and specialist views

Real-world Timeline and operational Audit remain separate. Timeline entries use honest precision, concise identity, type and a canonical origin link; derived occurrences identify their source.

Relationships use three non-duplicative forms:

1. concise domain-prioritised Overview summary;
2. detailed list/table for roles, status, dates and mutation;
3. graph/tree for structural exploration.

Maps derive markers from canonical entities and Relationships. Layer controls change visibility only; failures in optional map resources do not hide canonical coordinates or records. Marker popups link to canonical pages, and a textual mapped-record list provides equivalent access.

Graphs visualise stored Relationships without persisting layout-only connections. Legends and labels do not rely on colour. Selection cannot change geometry unexpectedly; contradictory/cyclic data remains visible with inspectable source Relationships. Large visuals may scroll inside a labelled region.

## Status, provenance and warnings

- Status uses plain specific text first and a badge only when compact scanning benefits.
- Counts say what they count; archived, deleted, rejected, invalidated, disabled and unavailable remain distinct.
- Provenance appears beside a fact when origin affects meaning; deeper history stays in Audit.
- Warnings are specific, explain risk and next action, and are deduplicated. Overview shows only warnings relevant to understanding or safely acting on that record.
- Operational summaries state their time window/category and link to the filtered source. Routine success does not become dashboard noise.

## Accessibility and state

Semantic reading order survives width changes. Headers, labels and focus remain visible. Maps, graphs and scroll regions are keyboard reachable and have text alternatives. Status remains understandable without colour. Long values wrap or expose their full content. Loading preserves orientation, announces meaningful change without excessive live-region noise and never traps focus.
