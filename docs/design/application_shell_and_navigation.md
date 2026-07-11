# Application Shell and Navigation

Status: Working standard. This document governs the persistent frame and navigation semantics. It does not specify page-body composition.

## Experience contract

The shell should make Project E feel like stable operational software: always oriented, efficient once learned, text-first and restrained. It must keep three intentions distinct:

- **Browse:** explore known domains and platform views through visible navigation.
- **Go:** use the Super Key to jump to a known destination with short, predictable input.
- **Search:** retrieve matching information from canonical records and relationships.

Combining these intentions into one ambiguous field would conflict with the Experience Philosophy. They may share retrieval primitives internally, but their labels, scope and result behaviour remain distinct.

## Current implementation audit

The current `layout()` renderer provides a stable header, domain links, global views, a System Tools entry, active-item styling and a header search form. This is a useful established frame and should be evolved without breaking route continuity.

The following are prototype limitations rather than standards:

- The shell identifies the product as **Operation Eddy**, while the repository and governing philosophy identify it as **Project E**.
- Navigation is one long horizontal row; there is no persistent left sidebar, nesting or icon-only state.
- The compact header field is global Search, not a distinct Super Key.
- Search is also presented on Home, but the two entry points are not differentiated by intent.
- Child System Tools pages rely on an active top-level link and “Back to System Tools”; there are no breadcrumbs or local tool navigation.
- The responsive fallback wraps or stacks the entire header. It does not define constrained-width hierarchy, overflow or context preservation.
- Active navigation uses visual class styling but no documented `aria-current` contract.

These conflicts should be addressed through a shell-specific implementation branch rather than piecemeal edits in unrelated feature work.

## Target shell anatomy

```text
┌──────────────────────────────────────────────────────────────┐
│ Project E identity              | global actions/status │
│ Super Key (Go)                  |                       │
├──────────────┬───────────────────────────────────────────────┤
│ Sidebar      │ page context / breadcrumbs                   │
│ Browse       │ entity or operational page                   │
│ nested views │                                               │
│ System Tools │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

The shell has two persistent regions at desktop widths:

1. A header containing Project E identity with the Super Key immediately beneath it at the left, plus genuinely global actions or status.
2. A left sidebar containing browseable destinations and nested view groups.

Global Search is a clearly labelled global destination outside entity pages, not silently relabelled as the Super Key. It opens the canonical Search page rather than occupying an entity-level field.

## Project E identity

- Expanded state shows the E mark plus **Project E** wordmark at top-left.
- Collapsed state shows the E mark with accessible name “Project E — Home”.
- Identity links to Home.
- Branding does not occupy content-page headings or compete with entity identity.
- “Operation Eddy” should not remain as a second unexplained product name. The Experience Philosophy establishes Project E and the E mark as the shell identity.

## Sidebar information architecture

The expanded sidebar uses text labels and nesting. The initial hierarchy is:

```text
Home
Information
  People
  Organisations
  Locations
  Projects
  Documents
  Assets
Connections and views
  Relationships
  Timeline
  Map
System Tools
  Search
  Data Quality
  Taxonomies
  Recycle Bin
  Audit
  Import and Export
```

Group labels are orientation aids, not destinations unless they have a real hub page. System Tools already has a useful hub and may remain both a group and a destination. Phase 2 may add Calendar, Tasks, Inbox and System Health only when those capabilities are authorised and delivered; roadmap entries do not populate current navigation in advance.

### Expanded state

- Text labels are always visible.
- Current destination and expanded parent are indicated independently.
- Nesting depth is shallow and deliberate; avoid an explorer-style tree for ordinary product navigation.
- Counts appear only when actionable or useful, such as pending review items. Record totals do not belong beside every domain by default.

### Icon-only state

- Collapse is a density control, not removal of navigation.
- Every destination retains a consistent icon, accessible name and tooltip on hover/focus.
- The current destination remains visible without relying on colour alone.
- Nested destinations open through a labelled flyout or temporary expanded panel; they must not become unlabelled icon puzzles.
- Each session starts expanded. The expanded/collapsed choice may persist for the current session only; broader sidebar customisation and cross-session persistence are deferred.

## Header responsibilities

The header contains only persistent global capability:

- Project E identity and Home link.
- Super Key beneath Project E identity.
- Global Search destination/action.
- A future concise attention indicator that opens the system inbox; it must not render an uncontrolled notification stream.
- A constrained-width navigation control when the sidebar is not persistent.

Entity create actions, filters, edit actions and page-specific tools belong in page or entity headers, not the global frame.

## Super Key: Go

The Super Key is a deterministic destination launcher.

### Responsibilities

- Within an entity context, accept a few characters or a concise word naming a relevant specialised view, such as `tree` for the current Person's Family Tree. Outside an entity, accept unique short route aliases such as `map` and `bin` that navigate directly to their global destinations.
- Return destinations quickly and predictably.
- Prefer one-step navigation over displaying a research-style result page.
- Teach available codes through visible examples or a compact help affordance.
- Authorised future power/admin destinations may be reached by unique aliases, but consequential actions and essential ordinary routes remain visibly navigable.
- Use `Ctrl+K` on Windows/Linux and `Cmd+K` on macOS to focus Super Key.

### Boundaries

- It is not natural-language chat.
- It does not answer questions, summarize records or execute consequential actions.
- It is not the advanced structured filter surface.
- It does not silently broaden a failed destination lookup into full-text search. Offer an explicit “Search for …” choice instead.
- It must not create a second source of route truth; destination aliases map to ordinary routes.

### Result behaviour

Every Super Key term has one unique destination. It navigates directly; it does not use a multiple-match chooser. The initial global registry contains `map` and `bin`; Person record routes additionally expose contextual `tree`, which opens the ordinary Family Tree route with that Person selected. Search remains a final explicit option when no destination term applies.

## Global Search

Search retrieves information and may return many results. It keeps the current repository behaviour worth preserving:

- canonical entity-field and notes matching;
- relationship-context matching;
- entity-type, favourites and structured filters;
- results linking to canonical entity or relationship pages.

Search needs a stable page with query persistence, result count, clear filter state and empty/error guidance. The header or Home may offer a compact entry point, but submitting it opens the same canonical Search view. Search remains under System Tools for browse navigation while still being globally reachable.

## Breadcrumbs and local navigation

Breadcrumbs are used when they clarify hierarchy or return context:

- System Tools → Taxonomies.
- People → Ada Lovelace → Edit.
- People → Ada Lovelace → Family Tree.
- Recycle Bin → Ada Lovelace → Permanent delete.

Do not add a redundant breadcrumb to flat Home or top-level index pages. Breadcrumbs show information hierarchy, not browser history.

Entity Overviews remain the direct, concise base-data view. A labelled secondary **Views** control reaches specialised representations such as Relationships, Family Tree, Timeline, Documents, Map and Audit; tabs and a local rail are not the default. The control may be keyboard-operated. Labels and routes remain stable regardless of presentation.

## Context preservation

Navigation between equivalent specialised views should preserve the active view when that matches intent:

- Person A Family Tree → Person B opens Person B Family Tree.
- Entity A Timeline → related Entity B opens Entity B Timeline when the link represents timeline exploration.
- Map marker → entity may open the entity's Map view or Overview with preserved return-to-map context; the link label must make the result clear.

Context preservation is encoded in explicit route/link semantics, not only fragile referrer state. A missing specialised view falls back to Overview with a concise explanation rather than a dead end.

Ordinary relationship links from Overview continue to open the related entity's Overview unless the interaction began inside a specialised context.

## Home within the shell

Home is a restrained jumping-off point, not a content-heavy command centre or resume screen. The current domain create/browse cards, favourites and recent records are useful discovery patterns. When Inbox exists, Home may show a link and a small count/ticker for active, not-dismissed items but does not embed the attention queue. Layout remains curated and opinionated; no dashboard builder is planned.

## Constrained-width behaviour

Stage 1 is desktop-only. The ordinary shell must be designed and verified at 1440 × 900 and 1920 × 1080. A future constrained-width path may use the following direction without constituting a current support commitment:

- The sidebar becomes an off-canvas or temporary labelled navigation panel; it is never reduced to an unexplained row of icons.
- Project E identity, current page/entity identity, one primary action and a navigation escape remain visible.
- Super Key and Search may become separate labelled actions that open full-width controls.
- Breadcrumbs may collapse middle segments while keeping parent and current labels available.
- Page-local navigation becomes horizontally scrollable or a labelled menu without changing route semantics.
- Wide tables, maps and graphs scroll inside their own regions rather than forcing the whole page off-screen.

Any later breakpoints are chosen after content fails in representative pages. Candidate dimensions in the [design system](design_system.md) are not final before that test.

## Accessibility and keyboard contract

- Use semantic header, navigation, main and complementary landmarks.
- Provide a skip link to main content.
- Use `aria-current="page"` for the current destination and an appropriate state for expanded groups.
- Collapse, nested group, Super Key, Views and constrained-width menu states are keyboard operable and announced.
- Focus moves predictably when a menu or chooser opens and returns to the invoker when it closes.
- Navigation order is stable between pages.
- Keyboard shortcuts do not override browser or assistive-technology conventions and are discoverable without memorisation.

## Implementation acceptance checks

- Every current route remains reachable through Browse or an intentional contextual link.
- Browse, Go and Search have distinct labels, scope and result behaviour.
- Project E identity works in expanded and collapsed states.
- The current page and parent section are perceptible without colour alone.
- System Tools child pages have consistent hierarchy and return navigation.
- A representative entity specialised-view link preserves context.
- The shell remains usable at wide, medium and constrained widths with keyboard-only navigation.
- No custom navigation layout, workspace manager or speculative Phase 2 destination is introduced.
