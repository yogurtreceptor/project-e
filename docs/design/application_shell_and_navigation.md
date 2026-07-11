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
│ Project E identity | Super Key (Go) | global actions/status │
├──────────────┬───────────────────────────────────────────────┤
│ Sidebar      │ page context / breadcrumbs                   │
│ Browse       │ entity or operational page                   │
│ nested views │                                               │
│ System Tools │                                               │
└──────────────┴───────────────────────────────────────────────┘
```

The shell has two persistent regions at desktop widths:

1. A header containing Project E identity, the Super Key and genuinely global actions or status.
2. A left sidebar containing browseable destinations and nested view groups.

Global Search is a clearly labelled destination/action, not silently relabelled as the Super Key. Its input may live in the header only if it remains visually and semantically distinct from Go; otherwise the header exposes a Search action that opens the search page.

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
- The expanded/collapsed choice may persist locally once implementation exists, but broader sidebar customisation is deferred.

## Header responsibilities

The header contains only persistent global capability:

- Project E identity and Home link.
- Super Key.
- Global Search entry if not continuously visible.
- A future concise attention indicator that opens the system inbox; it must not render an uncontrolled notification stream.
- A constrained-width navigation control when the sidebar is not persistent.

Entity create actions, filters, edit actions and page-specific tools belong in page or entity headers, not the global frame.

## Super Key: Go

The Super Key is a deterministic destination launcher.

### Responsibilities

- Accept short codes, route aliases, concise destination names and optionally exact or strongly matching entity names.
- Return destinations quickly and predictably.
- Prefer one-step navigation over displaying a research-style result page.
- Teach available codes through visible examples, recent destinations or a compact help affordance.
- Support keyboard invocation after shortcut decision D-05.

### Boundaries

- It is not natural-language chat.
- It does not answer questions, summarize records or execute consequential actions.
- It is not the advanced structured filter surface.
- It does not silently broaden a failed destination lookup into full-text search. Offer an explicit “Search for …” choice instead.
- It must not create a second source of route truth; destination aliases map to ordinary routes.

### Result behaviour

When one exact destination exists, Go may navigate directly. When several destinations match, show a compact keyboard-navigable chooser grouped by destination kind. Each row names its type and destination. Search remains a final explicit option.

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

Entity pages also have local text navigation for Overview and specialised views. The chosen pattern—tabs or compact local rail—requires prototype decision D-06. The labels and routes must be stable regardless of presentation.

## Context preservation

Navigation between equivalent specialised views should preserve the active view when that matches intent:

- Person A Family Tree → Person B opens Person B Family Tree.
- Entity A Timeline → related Entity B opens Entity B Timeline when the link represents timeline exploration.
- Map marker → entity may open the entity's Map view or Overview with preserved return-to-map context; the link label must make the result clear.

Context preservation is encoded in explicit route/link semantics, not only fragile referrer state. A missing specialised view falls back to Overview with a concise explanation rather than a dead end.

Ordinary relationship links from Overview continue to open the related entity's Overview unless the interaction began inside a specialised context.

## Home within the shell

Home is the operational command centre, not merely a collection of domain counts or a resume screen. The current domain create/browse cards are useful launch patterns, and favourites/recent are useful secondary discovery. As Phase 2 capability arrives, Home should prioritise actionable attention and near-term awareness ahead of record totals. Layout remains curated and opinionated; no dashboard builder is planned.

## Constrained-width behaviour

Mobile product support is deferred, but the shell must have a coherent constrained-width path:

- The sidebar becomes an off-canvas or temporary labelled navigation panel; it is never reduced to an unexplained row of icons.
- Project E identity, current page/entity identity, one primary action and a navigation escape remain visible.
- Super Key and Search may become separate labelled actions that open full-width controls.
- Breadcrumbs may collapse middle segments while keeping parent and current labels available.
- Page-local navigation becomes horizontally scrollable or a labelled menu without changing route semantics.
- Wide tables, maps and graphs scroll inside their own regions rather than forcing the whole page off-screen.

Breakpoints are chosen after content fails in representative pages. Candidate dimensions in the [design system](design_system.md) are not final before this test.

## Accessibility and keyboard contract

- Use semantic header, navigation, main and complementary landmarks.
- Provide a skip link to main content.
- Use `aria-current="page"` for the current destination and an appropriate state for expanded groups.
- Collapse, nested group, Super Key chooser and constrained-width menu states are keyboard operable and announced.
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
