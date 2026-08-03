# Design Documentation

These files turn the [Experience Philosophy](../experience_philosophy.md) into current implementation-facing UI contracts. They govern presentation and interaction; product meaning, persistence and future scope belong in their respective domain documents.

## Reading order

Read only the standard that owns the changed surface:

| Document | Responsibility |
| --- | --- |
| [Design system](design_system.md) | Tokens, visual roles, components, themes, density, icons and accessibility. |
| [Application shell and navigation](application_shell_and_navigation.md) | Persistent frame, Browse/Go/Search, breadcrumbs and context preservation. |
| [Entity pages and forms](entity_pages_and_forms.md) | Record Overviews, domain composition, data entry, validation and consequential actions. |
| [Data presentation patterns](data_presentation_patterns.md) | Tables, lists, cards, filters, timelines, Relationships, maps, graphs and states. |
| [Operational attention and review](operational_attention_and_review.md) | Inbox, reminders, execution history, review semantics, messages and noise control. |
| [Page and view catalogue](page_and_view_catalogue.md) | Current route families and page purposes. |

Resolve conflicts in this order: Experience Philosophy; product/domain authorities; the responsible focused standard; current implementation evidence; the explicitly authorised task. Plans and deferred ideas do not override delivered contracts or authorise redesign.

## Shared foundation

- Project E is page-first and desktop-first, with a persistent collapsible sidebar.
- Browse, deterministic Super Key Go and Search remain separate intentions.
- Entity Overviews are read-only and domain-specific; editing uses complete pages.
- Domain, operational and administrative information remain distinct.
- Semantic tokens supply system-selected light/dark themes; text labels are preferred.
- Compact density is reserved for demonstrated specialist or administrative needs.
- Transient messages, Inbox attention, audit history and execution history are not interchangeable.
- Mobile workflows, arbitrary workspaces/dashboards, decorative animation and AI review interfaces remain separately authorised.

## Maintenance

Keep only current durable rules here. Completed audits and delivery evidence belong in Git history or the concise build log; unresolved defects belong in the technical-debt register; future product choices belong in the roadmap or active phase workspace. Update the page catalogue only when route purpose or shared composition changes.
