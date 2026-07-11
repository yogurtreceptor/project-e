# Design Documentation

This directory is the implementation-facing design layer for Project E. It translates the [Experience Philosophy](../experience_philosophy.md) into reusable rules without replacing that philosophy or turning current prototype behaviour into authority by default.

## Authority and document roles

When guidance appears to conflict, use this order and record the conflict rather than silently choosing whichever implementation is easiest:

1. [`experience_philosophy.md`](../experience_philosophy.md) — why the interface should feel and behave as it does.
2. Current product and domain authorities — `PROJECT_GOAL.md`, the Stage 1 specification, the Phase 2 plan, architecture decisions, ontology and glossary.
3. Documents in this directory — how experience principles are applied consistently.
4. [`ui_principles.md`](../ui_principles.md) — delivered workflow details and current interaction conventions.
5. Current UI implementation — evidence of working patterns, not automatic design authority.
6. Implementation tasks — scoped changes that apply these standards.

The embedded SQLite database remains the source of canonical information. Design documents govern presentation and interaction, not domain persistence.

## Smallest coherent document set

| Document | Purpose | Initial maturity |
| --- | --- | --- |
| [Design system](design_system.md) | Visual roles, tokens, states, density, responsiveness, icons and accessibility | Working foundation; exact palette and component metrics remain draft decisions |
| [Application shell and navigation](application_shell_and_navigation.md) | Persistent frame, sidebar, breadcrumbs, Browse/Go/Search, context preservation and constrained widths | Working standard; Super Key syntax and narrow-screen mechanics remain open |
| [Entity pages and forms](entity_pages_and_forms.md) | Shared entity-page grammar, domain-specific composition, separate edit flows and deliberate data entry | Working standard; domain page compositions need implementation prototypes |
| [Data presentation patterns](data_presentation_patterns.md) | Tables, panels, lists, filters, timelines, relationships, maps, graphs, status and provenance | Working pattern catalogue; density and complex-view testing remain open |
| [Operational attention and review](operational_attention_and_review.md) | Background work, approvals, inbox items, persistent issues, messages, severity and noise control | Target standard aligned to planned Phase 2; not a claim of delivered behaviour |
| [Page and view catalogue](page_and_view_catalogue.md) | Current routes, purposes, shared renderers, recurring patterns, inconsistencies and intended direction | Audited baseline for the current post-prototype UI |

Entity-page and form standards intentionally share one document. Both depend on the same domain definition, field order, view/edit boundary, context-return behaviour and validation model; splitting them now would duplicate rules. They may split later only if either section becomes difficult to navigate.

Operational attention remains separate from ordinary data presentation because notifications, persistent issues, approvals, audit events and job runs have distinct semantics in the accepted Phase 2 architecture. Treating them as generic badges or cards would lose those boundaries.

## Terms used by these documents

- **Current:** behaviour verified in the repository now.
- **Standard:** a design decision approved by the Experience Philosophy or established product rules and suitable for future implementation.
- **Candidate:** a reasoned recommendation requiring validation or product-owner choice before it becomes a standard.
- **Deferred:** intentionally outside the next design or implementation pass.
- **Exception:** a domain-specific departure that is documented and justified rather than accidental.

Every normative rule should be traceable to the Experience Philosophy, a repository authority, an observed inconsistency, an accessibility or maintainability requirement, or an authorised near-term workflow. The evidence notes in each document make that traceability explicit.

## Documentation roadmap

### Document now

- Experience authority and document hierarchy.
- Semantic token roles, component-state vocabulary and accessibility baseline.
- The target Project E shell and distinction between Browse, Go and Search.
- Shared entity-page grammar without imposing one domain-neutral layout.
- View/edit separation, progressive disclosure, validation and consequential-action patterns.
- Reusable table, list, filter, timeline, map, graph, status and provenance patterns.
- Phase 2 attention semantics, especially the distinction between reminders, notifications, persistent issues, audit events and job runs.
- A route-level inventory and classification of current patterns.

### Audit or prototype before fixing exact values

- Measure representative dense and sparse pages at wide, medium and constrained widths before fixing sidebar widths, content widths, compact row heights or breakpoints.
- Test Roboto across real forms, tables, timelines and family trees before fixing the complete type scale.
- Build one shell prototype before fixing the expanded and icon-only dimensions, icon set and Super Key shortcut.
- Prototype Person, Document and Project pages as three deliberately different compositions before formalising a full entity-header component.
- Check colour candidates against WCAG contrast in every interaction state before adopting a palette.
- Run keyboard and assistive-technology checks on taxonomy, reference and optional-detail controls before treating their current behaviour as complete.

### Intentionally deferred

- Dark mode implementation; the policy decision remains open, and light mode is the only current implementation.
- User-configurable dashboards, arbitrary navigation layout and user-defined density scales.
- Dockable workspaces or a workspace manager.
- Mobile-specific product workflows; constrained-width continuity is documented so mobile can be added later without invalidating page architecture.
- A third-party CSS framework, component library or frontend migration.
- Animation used only for polish.
- AI review interfaces and autonomous workflow controls.

### Dependencies

```text
Experience Philosophy
    → design-system roles and accessibility baseline
    → shell/navigation prototype
    → entity-page prototypes and data-presentation density
    → implementation branches

Phase 2 attention semantics
    → operational attention patterns
    → inbox/health/review prototypes
    → Phase 2 implementation branches
```

The page catalogue can be updated independently whenever routes or shared renderers change. Exact component measurements should follow the shell and representative domain prototypes, not precede them.

## Formalised decisions

These decisions are sufficiently grounded to guide implementation now:

1. The Experience Philosophy remains the experience-level authority; this directory is subordinate implementation guidance.
2. The current UI is an audited prototype, not the design system.
3. The persistent shell identifies the product as **Project E**, using the E mark in its collapsed state. The current unexplained **Operation Eddy** label is not a second product identity to preserve.
4. Project E uses a page-first shell with a persistent header and collapsible nested left sidebar.
5. Browse, Go through the Super Key, and global Search are separate intentions and controls.
6. Entity pages share grammar and components but use domain-specific composition.
7. Entity overview pages are read-only by default; complete-page edit forms are separate.
8. Domain, operational and administrative information are separate layers. Provenance may appear near a fact when it changes interpretation.
9. Light mode is the current baseline. Dark mode must not be implemented piecemeal.
10. Text labels are the default; icons can replace text only in constrained, familiar, labelled contexts.
11. Transient messages, actionable notifications, persistent issues, audit events and job runs are not interchangeable.
12. Reminders are behaviour attached to source records or policies, never a standalone entity navigation domain.
13. Configuration is added only after demonstrated need.

## Product-owner decisions still required

| ID | Question | Why it matters | Recommended default until decided |
| --- | --- | --- | --- |
| D-02 | Which exact cool palette should define brand roles? | Current teal values are coherent but do not cover the philosophy's blue/purple/green direction or all semantic states. | Retain current light neutrals during prototypes; do not canonise the teal hex values. |
| D-03 | Is dark mode a launch requirement, a later first-class mode, or unsupported until demonstrated need? | The answer affects token validation and component QA. | Light-only for the next implementation branch, with semantic token names that do not prevent later dark mode. |
| D-04 | Which icon library, if any, is acceptable? | Icon-only sidebar mode needs a consistent, accessible set without adding an unnecessary dependency. | Prototype with a small local SVG set only after dependency and licence review. |
| D-05 | What invocation and minimal syntax should the Super Key use? | It determines discoverability, keyboard conflict risk and route naming. | Visible field plus a documented shortcut; destinations only, no natural language or query grammar. |
| D-06 | Should specialised entity views use tabs, a local sub-navigation rail, or a context menu at desktop widths? | This controls context preservation and information density. | Prototype a compact text sub-navigation directly below the entity header. |
| D-07 | Which source/provenance indicators belong beside ordinary facts? | Provenance affects interpretation, but broad metadata exposure conflicts with progressive disclosure. | Show only source/evidence that affects trust or meaning; link to a specialised Audit view for the rest. |
| D-08 | What is the minimum supported constrained width before the experience may become horizontally scrollable? | Tables, graphs and maps cannot all collapse in the same way. | Preserve core page tasks at 720px; permit deliberate internal scrolling for tables, maps and graphs. |
| D-09 | Should the home command centre initially prioritise attention, upcoming time, or recent change once Phase 2 begins? | The current home is predominantly domain launch cards and resumption lists. | Put actionable attention first once it exists; keep favourites/recent as secondary discovery. |

The D-01 identity conflict is closed by the Experience Philosophy: the shell is Project E, with the E mark available for compact presentation. The remaining questions are not permission to implement customisation. A product-owner decision should become a concise update to the responsible document, not a new settings screen.

## Maintenance rule

When interface behaviour changes, update the page catalogue and the one responsible standard. Do not repeat an unchanged rule in several documents. If implementation intentionally departs from a standard, record the exception, rationale and review trigger in the responsible document. Resolved implementation work belongs in the build history; unresolved engineering defects belong in the technical-debt register.
