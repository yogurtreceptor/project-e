# Design Catch-up Implementation Plan

Status: Authorised implementation plan. An agent may implement this plan in order after reading `AGENTS.md`. This plan applies the existing design documentation; it does not authorise unrelated product features, schema changes, new dependencies, mobile support, user settings, workspaces or Phase 2 capabilities.

## Entry instruction for an implementation agent

Read, in this order:

1. `AGENTS.md`
2. This document
3. [Implementation readiness](implementation_readiness.md)
4. The design standard named by the current step
5. Relevant existing code, tests and current working-tree status

Preserve unrelated changes. Work on one numbered step at a time. Before each commit, run `python3 -m unittest discover -s tests` and `python3 -m compileall app run.py tests`, plus the step-specific checks. Update the page catalogue, responsible design standard and build log when a completed step changes their truth.

## Global implementation rules

- Use the existing standard-library Python/HTML/CSS/JavaScript architecture. Do not add a CSS framework, component library or icon dependency.
- Add no schema changes merely for visual consistency.
- Define `#66ccff` once as the base accent primitive. Components use semantic tokens, never repeated literal colours.
- Implement both themes using shared semantic tokens. Follow the operating-system preference; use dark if no preference is available. Dark surfaces are charcoal.
- Desktop is the current scope. Review at 1440 × 900 and 1920 × 1080; do not undertake mobile redesign work.
- Keep Browse, Super Key Go and Search distinct. Super Key uses `Ctrl+K`/`Cmd+K` and unique aliases only.
- Keep entity Overview as the direct base-data page. Specialist representations use a grouped, keyboard-operable **Views** menu.
- Do not decide deferred behaviour during unrelated work. The deferred items are provenance presentation, user theme switching, non-administrative compact density, long-list navigation, family-tree node-click behaviour, and exact graph/map category assignments.

## Completion order

### 1. Baseline audit and safe foundation seam

**Status:** Completed 2026-07-11 in `bc11cd6`. The shared CSS/layout boundary is recorded in the page catalogue; `styles.css` imports the visual-neutral `foundation.css` seam; the local server and focused tests cover the entry point; the undefined Family Tree text token was corrected; the full suite, compile check and running-app static smoke passed.

**Goal:** identify the current stylesheet/layout entry points and create a safe place for the new foundation without changing visible workflows yet.

**Implement:**

- Inspect `app/static/`, layout rendering and view-page renderers; record the current shared CSS and layout boundaries.
- Introduce a single design-foundation stylesheet/module entry point imported by the existing application stylesheet.
- Remove only clearly broken CSS discovered in the audited shared path, such as unmatched braces or undefined token use, when the correction is covered by a focused test or smoke check.
- Add a small visual-regression/smoke checklist to the implementation notes if the repository has no suitable existing location.

**Do not:** redesign routes, alter page composition, rename domain terms or change persistence.

**Done when:** the foundation can be applied incrementally, the existing application still renders, and no undefined token or malformed shared CSS remains in the path being changed.

### 2. Tokens, themes and global accessibility base

**Status:** Completed 2026-07-11. `foundation.css` now defines the primitive and semantic colour roles, typography, spacing, dimensions, radii and elevation; dark charcoal is the fallback and `prefers-color-scheme: light` supplies the companion theme. Roboto uses local/system fallbacks, shared keyboard focus uses a 2px outer ring, and reduced-motion preferences suppress non-essential transitions. Focused tests verify the single accent literal, token completeness, representative WCAG contrast pairs and global states; the full suite and compile check passed. Final whole-application visual QA at both target sizes remains part of Step 11 because no headless browser is installed in this workspace.

**Goal:** replace prototype colours and metrics with one semantic design system usable by every route.

**Implement:**

- Define primitive and semantic CSS custom properties for canvas, surfaces, text, borders, actions, statuses, graph/map series, typography, spacing, radii and elevation.
- Define `#66ccff` in one primitive token only; derive semantic primary, hover, active, selected and focus roles from it.
- Add charcoal dark tokens and companion light tokens selected by `prefers-color-scheme`; dark is the fallback when no preference is known.
- Apply Roboto with a local-first/system fallback strategy already compatible with the repository.
- Add the 2px keyboard-only focus ring, visible across normal, selected, invalid and both-theme controls.
- Add shared reduced-motion-safe transitions only where they communicate state; do not add decorative motion.

**Do not:** add a user theme toggle or private component theme overrides.

**Done when:** representative controls in both themes use semantic tokens only, meet contrast requirements, and keyboard focus is obvious.

### 3. Shared components and interaction states

**Status:** Completed 2026-07-11. Shared actions, controls, panels, badges, quiet warning rows with **Details**, notices and empty/loading/failure states consume semantic roles across both themes. Successful entity/relationship create and edit redirects show a passive fading **Changes saved** status without moving focus. Reversible entity soft deletion uses an accessible native dialog with object/consequence text, modal focus containment, Escape/cancel and invoker focus return; permanent delete, merge and import retain dedicated review pages. Entity and relationship validation summaries link to error-associated controls that remain visibly invalid, render adjacent error text and retain submitted values. Focused component tests, the 159-test suite, compile check and running-app asset/page smoke passed; final browser-based visual and keyboard QA remains consolidated in Step 11.

**Goal:** establish a small reusable set of components before converting complete pages.

**Implement:**

- Style primary, secondary, quiet/text and final-danger actions; preserve link-versus-button semantics.
- Standardise inputs, selects, textareas, labels, help text, disabled/read-only state and error treatment.
- Implement top-of-screen fading **Changes saved** toast without focus movement.
- Implement accessible confirmation modal for reversible important actions. It must show the object/consequence, trap focus appropriately and return focus to its invoker.
- Standardise panels, compact status badges, quiet warning status rows with **Details** links, empty states, loading state and failure state.
- Ensure validation has a top-of-page summary plus an error-associated invalid control that remains visibly invalid until corrected.

**Do not:** replace permanent-delete, merge or import review pages with a modal.

**Done when:** one focused test or smoke path verifies each component state, including keyboard focus, Escape/close behaviour and retained form values after validation failure.

### 4. Brand and local SVG assets

**Status:** Completed 2026-07-11. A bold tilted E mark and a coherent local 24px SVG set now cover shell identity, navigation groups, Search, Super Key, shared actions/status and the initial domains/views. The existing shell uses the Project E identity and matching navigation/action assets without pulling forward the Step 5 sidebar conversion. Meaningful icons support accessible names, adjacent-label icons are hidden as decorative, and focused tests verify asset consistency and safe local serving.

**Goal:** give the shell and shared controls a coherent, original visual identity.

**Implement:**

- Create an original E mark with a nerdy corporate/industrial feel; it must not copy Mr. Robot/E Corp artwork.
- Create the initial local SVG set: home, navigation groups, search, Super Key, add, edit, delete, overflow, close, warning/status and the initial domain/view icons needed by the shell.
- Use 24px SVG view boxes, 20px ordinary toolbar rendering, 24px collapsed-sidebar rendering and rounded stroke endings.
- Give every meaningful icon an accessible name; icon-only controls also receive a tooltip on hover/focus.

**Do not:** substitute emoji or add an external icon package.

**Done when:** the shell and core controls use the same asset style at ordinary and collapsed-sidebar sizes.

### 5. Desktop shell and Browse navigation

**Status:** Completed 2026-07-11. The horizontal prototype header is replaced by the persistent Project E shell: a 240px labelled Browse sidebar, a 56px icon state, session-only collapse persistence, semantic navigation groups, all existing System Tools destinations, a distinct global Search action, skip navigation, `aria-current` state and non-colour active/parent cues. The Super Key position is reserved without implementing Step 6 behaviour. Focused tests cover hierarchy, route reachability and shell accessibility; the full suite, compile check and running-app smoke passed. Final browser-driven visual review at both target sizes remains consolidated in Step 11.

**Goal:** replace the prototype horizontal header with the persistent Project E shell.

**Implement:**

- Build the Project E identity/Home link, with E mark in collapsed mode.
- Build the expanded 240px candidate sidebar, collapsed 56px candidate sidebar and session-only state persistence.
- Implement the documented Information, Connections and views, and System Tools hierarchy using existing routes only.
- Make current destination and expanded parent perceptible without colour alone; apply `aria-current` and accessible expanded/collapsed state.
- Make Search a dedicated global destination outside entity pages.
- Preserve every current route through Browse or intentional contextual links.

**Do not:** add speculative Phase 2 navigation destinations or persistent cross-session configuration.

**Done when:** keyboard-only navigation reaches all current routes, and the shell is visually usable at 1440 × 900 and 1920 × 1080.

### 6. Super Key Go

**Status:** Completed 2026-07-11. The reserved shell control now opens a keyboard-operable deterministic Go dialog from the sidebar or `Ctrl+K`/`Cmd+K`. A single client-side registry maps exact `map` and `bin` aliases to ordinary routes; `tree` is available only in Person context and opens the ordinary Family Tree route with that Person selected. Unknown terms expose an explicit canonical Search link, aliases are taught inline, and no fuzzy lookup, actions or second route source were introduced. Focused tests cover shell semantics, registry boundaries, contextual routing and safe local script serving; the full suite, compile check and running-app smoke passed. Final browser-based visual and keyboard QA remains consolidated in Step 11.

**Goal:** add deterministic direct navigation without turning it into Search or chat.

**Implement:**

- Place Super Key beneath Project E identity.
- Bind `Ctrl+K` on Windows/Linux and `Cmd+K` on macOS; do not override an assistive-technology or browser convention if testing shows a conflict.
- Create one registry of unique aliases mapped to ordinary routes/contextual views. Start with established aliases such as `map`, `bin` and entity-context `tree`.
- Navigate directly for an exact alias. For anything else, offer the explicit canonical Search destination; do not create a multiple-match chooser.
- Provide a compact visible help/example affordance so aliases do not require memorisation.

**Do not:** add natural-language parsing, entity full-text lookup, consequential actions or hidden essential routes.

**Done when:** keyboard focus, exact navigation, unknown-term handling and contextual `tree` navigation are covered by focused tests and a running-app smoke check.

### 7. Entity-page frame and forms

**Status:** Completed 2026-07-11. Entity pages now share breadcrumbs, identity grammar, direct Edit/Delete, grouped keyboard-native **Views**, and a restrained overflow containing favourite, Add relationship and Merge. Integrity findings use the quiet warning row with **Details**, and the relationship section exposes an accessible icon-only Add relationship action in empty and populated states. Edit Cancel returns to the canonical record; all entity forms use the established one-column, retained-value and linked-validation foundation plus a consistent dirty-form dialog with Keep editing/Discard changes and browser-navigation protection. Save toast and recoverable-delete confirmation remain integrated. Focused tests cover the frame, menu content, warnings, relationship action, form context and dirty states; the full suite, compile check and running-app smoke passed. Domain-specific Overview conversion remains correctly scoped to Step 8.

**Goal:** apply shared page grammar to read-only entity views and deliberate editing.

**Implement:**

- Build shared entity identity/header structure, breadcrumbs, direct **Edit** and **Delete**, contextual/overflow **Merge**, quiet warning row and grouped **Views** menu.
- Keep Overview as the direct base-data page; show relevant specialist views even when empty, with suitable guidance.
- Implement the one-column form layout, top error summary, error-associated invalid fields, preserved progressive disclosure and dirty-form warning.
- Apply the top save toast and confirmation modal to the relevant existing flows.
- Make Relationship views expose icon-only Add relationship whether empty or populated, with accessible name and tooltip.

**Do not:** force every entity type into one identical Overview or make broad domain/schema changes.

**Done when:** the shared frame works for one view/edit flow without breaking existing form submissions, Cancel context or confirmation behaviour.

### 8. Representative domain prototypes

**Goal:** prove the system supports genuinely different domain compositions before broad conversion.

**Implement:**

- **Person:** prioritise birthday, phone, email and locations. Derive displayed addresses from Location relationships and their relationship type; do not duplicate stored address truth.
- **Document:** lead with safe preview/open/download. Render or open safe small text/image files where supported; use download for large or unsupported files.
- **Project:** lead with status and milestones before secondary information.
- Apply shared headers, Views menu, actions, warnings, forms and both themes to each prototype.

**Do not:** implement future Task/Event/Inbox data models or invent new relationship semantics.

**Done when:** all three pages look domain-specific but share tokens, control states and page grammar; review them at both target desktop sizes.

### 9. Collections and specialist representations

**Goal:** bring reusable data views into the foundation without sacrificing their task-specific strengths.

**Implement:**

- Convert ordinary index tables, relationship lists, search results and filters to shared table/list/filter patterns.
- Use balanced density by default. Keep compact density to administrative/high-volume views unless a real data view demonstrably needs it.
- Update Timeline, Map and Family Tree to consume semantic tokens and shared states.
- Retain textual alternatives for maps and graphs, explicit remote-map failure guidance, labelled scroll containers and context-preserving links.
- Keep graph/map category colours semantic and provisional until real categories are selected.

**Do not:** decide long-list pagination/loading or family-tree node-click behaviour prematurely.

**Done when:** table, timeline, map and family-tree representative pages meet their design-standard acceptance checks in both themes.

### 10. Incremental route-family conversion

**Goal:** complete the visual catch-up safely rather than via a single high-risk rewrite.

**Implement:**

- Convert remaining route families one at a time, starting with high-use entity indexes and system tools.
- Remove replaced one-off prototype CSS as each route family moves to shared tokens/components.
- Update `page_and_view_catalogue.md` when an assessed inconsistency is resolved.
- Add regression tests for changed workflow behaviour; retain stable public facades.

**Do not:** leave duplicate styling systems indefinitely or convert unrelated workflow behaviour in the same task.

**Done when:** all active route families use the foundation or have a recorded, justified exception.

### 11. Verification and close-out

**Goal:** establish that the design foundation is genuinely delivered rather than only documented.

**Verify:**

- Run the full unit suite and compile check required by `AGENTS.md`.
- Run the application on a temporary port, exercise representative shell, Person, Document, Project, form, table, map and Family Tree workflows, then stop it.
- Review both themes at 1440 × 900 and 1920 × 1080.
- Manually verify keyboard access, visible focus and focus return for sidebar, Super Key, Views menu, overflow menu, forms and confirmation modal.
- Check contrast for text, controls, statuses, focus ring and meaningful non-text graphics.
- Audit for undefined tokens, literal component colours, unused prototype rules and inaccessible icon-only controls.

**Done when:** all implementation-readiness exit evidence is met, deferred items remain explicit, and documentation describes the delivered design accurately.

## Commit boundaries

Prefer one commit per numbered step. A step may be split only when the split preserves a working, testable application; do not combine unrelated steps simply to reduce commit count. Use concise commit subjects that name the delivered foundation capability.

## Stop and ask for direction only when

- a needed decision is explicitly deferred above and the work cannot proceed without choosing it;
- implementation would introduce a new dependency, schema change, mobile support, user setting, workspace, Phase 2 workflow or other out-of-scope capability;
- an existing workflow conflicts materially with the documented design and no safe incremental migration is evident.
