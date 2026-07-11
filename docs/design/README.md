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
| [Design system](design_system.md) | Visual roles, tokens, states, density, responsiveness, icons and accessibility | Working foundation; palette direction, local SVG icons and system-selected theme policy are decided; exact metrics remain draft decisions |
| [Application shell and navigation](application_shell_and_navigation.md) | Persistent frame, sidebar, breadcrumbs, Browse/Go/Search, context preservation and constrained widths | Working standard; Super Key placement, entity-view access and narrow-screen mechanics are decided |
| [Entity pages and forms](entity_pages_and_forms.md) | Shared entity-page grammar, domain-specific composition, separate edit flows and deliberate data entry | Working standard; domain page compositions need implementation prototypes |
| [Data presentation patterns](data_presentation_patterns.md) | Tables, panels, lists, filters, timelines, relationships, maps, graphs, status and provenance | Working pattern catalogue; density and complex-view testing remain open |
| [Operational attention and review](operational_attention_and_review.md) | Background work, approvals, inbox items, persistent issues, messages, severity and noise control | Target standard aligned to planned Phase 2; not a claim of delivered behaviour |
| [Page and view catalogue](page_and_view_catalogue.md) | Current routes, purposes, shared renderers, recurring patterns, inconsistencies and intended direction | Audited baseline for the current post-prototype UI |
| [Implementation readiness](implementation_readiness.md) | Remaining product-owner questions, prototype evidence and ordered catch-up implementation sequence | Active register until the foundation is implemented and verified |
| [Design catch-up implementation plan](design_catchup_plan.md) | Authorised beginning-to-end, step-sized implementation work plan | Primary hand-off document for design catch-up work |

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

- The visual implementation of both light and dark themes. Dark is the preferred default based on the operating-system preference; the eventual manual theme switch remains deferred.
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

## Catch-up implementation readiness

The [implementation-readiness register](implementation_readiness.md) is the single place to collect remaining decisions and prototype evidence needed to close the gap between the current UI prototype and the documented design direction. It separates product-owner answers from questions that must be settled by visual, contrast and keyboard testing. Do not treat unanswered register items as permission to invent a competing design during implementation.

For implementation work, use the [design catch-up plan](design_catchup_plan.md) after reading `AGENTS.md`. It authorises the ordered catch-up steps and gives their scope, acceptance checks, commit boundaries and stop conditions.

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
9. Follow the operating-system theme when it is known; otherwise start in dark mode. Both themes must be implemented through shared semantic tokens, never piecemeal overrides.
10. Text labels are the default; icons can replace text only in constrained, familiar, labelled contexts.
11. Transient messages, actionable notifications, persistent issues, audit events and job runs are not interchangeable.
12. Reminders are behaviour attached to source records or policies, never a standalone entity navigation domain.
13. Configuration is added only after demonstrated need.

## Product-owner decisions still required

| ID | Question | Why it matters | Recommended default until decided |
| --- | --- | --- | --- |
| D-07 | When provenance becomes a delivered capability, which source indicators should appear beside ordinary facts? | The product should not add presentation rules ahead of the feature's semantics and workflows. | Keep provenance out of routine presentation for now; define it with the provenance feature. |

## Resolved design decisions

- **D-02 — Palette direction:** use `#66ccff` once as the base accent primitive, with predominantly black/white neutral surfaces and text. Semantic roles derive from it and still require contrast testing.
- **D-03 — Theme policy:** implement both themes through semantic tokens. Follow the operating-system preference when known; otherwise default to dark. Defer an explicit user switch until later.
- **D-04 — Icons:** maintain a coherent local SVG set instead of adding an icon-library dependency. Use a 24px view box, 20px ordinary rendering, 24px collapsed-sidebar rendering and rounded stroke endings.
- **D-05 — Super Key:** place it beneath the Project E identity at the left of the shell. Unique short terms navigate directly: within an entity, `tree` opens that record's Family Tree; outside an entity, aliases such as `map` and `bin` open global destinations. It is not global full-text Search.
- **D-06 — Entity views:** make the Overview the direct base-data view. Reach specialised representations, such as Family Tree, Timeline and Map, through a labelled secondary **Views** control rather than persistent tabs or a local rail. The control may be keyboard-operated.
- **D-08 — Viewport scope:** Stage 1 is desktop-only. Design and verify the ordinary experience at 1440 × 900 and 1920 × 1080; no narrower-width continuity commitment exists yet.
- **D-09 — Home:** use Home as a restrained jumping-off point, not a content-heavy command centre. When Inbox exists, show a link and a small count/ticker for notifications rather than embedding the inbox on Home.
- **Sidebar state:** start each session with the desktop sidebar expanded. Users may collapse it for the current session only; do not persist that preference between sessions.
- **Density:** limit compact density to administrative/high-volume views, with an explicit exception for data views where comparison benefits from it.
- **Page composition:** use a single-column default. Add a secondary column only when a specialised view genuinely needs it; revisit this convention as usage matures.
- **Map and graph palette:** use colours drawn from the Project E palette for application-owned layers and relationship categories, paired with labels, legends and non-colour distinctions. External basemap assets are exempt.
- **Keyboard focus:** use a consistent visible 2px outer focus ring for keyboard navigation. It must remain perceptible on selected, invalid and dark-theme controls and is not a persistent mouse-hover treatment.

The D-01 identity conflict is closed by the Experience Philosophy: the shell is Project E, with the E mark available for compact presentation. The remaining questions are not permission to implement customisation. A product-owner decision should become a concise update to the responsible document, not a new settings screen.

## Maintenance rule

When interface behaviour changes, update the page catalogue and the one responsible standard. Do not repeat an unchanged rule in several documents. If implementation intentionally departs from a standard, record the exception, rationale and review trigger in the responsible document. Resolved implementation work belongs in the build history; unresolved engineering defects belong in the technical-debt register.
