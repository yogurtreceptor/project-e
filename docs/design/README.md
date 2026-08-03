# Design documentation

This directory translates the [Experience Philosophy](../experience_philosophy.md) into implementation-facing UI standards. It governs presentation and interaction; SQLite and the domain documents govern canonical information.

## Authority

Resolve conflicts in this order and record material conflicts instead of silently choosing:

1. `docs/experience_philosophy.md`.
2. Product and domain authorities: `PROJECT_GOAL.md`, phase specifications, architecture decisions, ontology and glossary.
3. The focused design standards below.
4. `docs/ui_principles.md` for delivered workflow details.
5. Current UI implementation as evidence, not automatic authority.
6. The explicitly authorised implementation task.

Current work requires its own prompt. Completed plans, prototypes and open verification items do not authorise redesign.

## Document map

| Document | Responsibility |
| --- | --- |
| [Design system](design_system.md) | Tokens, visual roles, component states, density, responsiveness, icons and accessibility. |
| [Application shell and navigation](application_shell_and_navigation.md) | Persistent frame, sidebar, breadcrumbs, Browse/Go/Search, context and widths. |
| [Entity pages and forms](entity_pages_and_forms.md) | Shared record grammar, domain composition, separate editing, validation and consequential actions. |
| [Data presentation patterns](data_presentation_patterns.md) | Tables, panels, lists, filters, timelines, relationships, maps, graphs, status and provenance. |
| [Operational attention and review](operational_attention_and_review.md) | Inbox, reminders, jobs, review semantics, severity, messages and noise control. |
| [Page and view catalogue](page_and_view_catalogue.md) | Route purposes, shared renderers, current patterns, exceptions and intended direction. |

Keep entity pages and forms together because they share domain definitions, field order, view/edit boundaries and validation. Keep operational attention separate: notifications, persistent issues, approvals, audit events and job runs have different semantics and must not collapse into generic cards or badges.

Terms used in these documents:

- **Current:** verified repository behaviour.
- **Standard:** approved guidance for implementation.
- **Candidate:** a recommendation still requiring evidence or owner choice.
- **Deferred:** intentionally outside current work.
- **Exception:** a justified domain-specific departure.

## Established foundation

The design catch-up completed on 2026-07-12. Its implementation sequence was: semantic tokens and icons; shared components; desktop shell and navigation; deterministic Super Key; shared entity frame and form safeguards; distinct Person, Document and Project compositions; collections and specialist views; incremental route-family conversion; and integrated verification. The build history and Git commits retain the detailed delivery chronology.

The resulting durable conventions are:

- Project E is a page-first desktop interface with a persistent, session-collapsible left sidebar. Home is a restrained starting point.
- Browse, deterministic Go through the Super Key, and global Search are distinct intentions. Ordinary routes remain visibly reachable; Super Key aliases do not perform consequential actions.
- Entity Overviews are read-only by default. Complete-page edit forms are separate. Entity types share grammar and components but retain domain-specific composition.
- Domain, operational and administrative information remain distinct. Provenance appears beside ordinary facts only when its delivered semantics justify it.
- Semantic tokens implement system-selected dark and light themes. The palette uses black/white neutrals and one `#66ccff` accent primitive. A manual theme switch remains deferred.
- Text labels are the default. Familiar icon-only controls require an accessible name, tooltip and usable target. Local SVG icons use a 24px view box with rounded strokes.
- Tables and ordinary collections use balanced density. Compact density is reserved for administrative or demonstrated high-volume needs.
- Transient messages, actionable notifications, persistent issues, audit events and job runs are not interchangeable. Reminders are behaviour attached to source records, not a navigation domain.
- Configuration is added only after demonstrated need. Mobile-specific workflows, arbitrary dashboards, workspaces, third-party UI frameworks, decorative animation and AI review interfaces remain deferred.

## Remaining verification

Repository tests and isolated running-app smoke checks cover both themes; shell, representative entity pages and forms; tables; Calendar; Map; Family Tree; local SVG serving; focus contracts; and colour-token rules. The remaining external evidence is human Windows inspection at 1440 × 900 and 1920 × 1080 in both system themes, including:

- visual density, typography, clipping and long values;
- keyboard operation and focus return for sidebar, Super Key, Views and overflow menus, forms and confirmation dialogs;
- assistive-technology behaviour for taxonomy, reference and optional-detail controls;
- contrast and non-text meaning across component and status states.

Realistic data volume should decide any future pagination or compact-density rule. Real map/graph categories should decide their exact colours. Provenance presentation should be designed with the provenance workflow. These are deferred decisions, not missing permission to improvise.

When a verified finding changes a durable rule, update the responsible focused standard and the page catalogue where applicable. Record unresolved actionable defects in the technical-debt register; do not recreate a second readiness register.
