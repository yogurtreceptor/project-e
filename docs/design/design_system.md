# Design System

Status: Working foundation. This document defines reusable visual and component rules. It does not define page-specific workflow or make the current stylesheet authoritative.

## Purpose and evidence

The [Experience Philosophy](../experience_philosophy.md) calls for restrained professional software, adaptive density, Roboto, flat surfaces, clean borders, muted cool colour and text-first labelling. The current stylesheet already demonstrates useful role-based custom properties, flat panels, modest radii and consistent form controls. It also contains one-off colours, mixed units, duplicated declarations, an unmatched closing brace, an undefined `--ink` reference and no complete focus, disabled, loading or dark-mode model. The role structure is worth formalising; the exact prototype values and accumulated CSS are not.

## Token policy

- Components consume semantic tokens, not literal colours or page-specific numbers.
- Primitive values may support the semantic layer, but implementation code should use roles such as `--color-surface-panel` or `--color-text-muted`.
- Token names describe purpose, not appearance. `--color-status-danger` is valid; `--red-600` is not sufficient at the component boundary.
- A new one-off value needs either a documented exception or promotion into the scale after repeated use.
- Tokens do not become user settings merely because they exist.

## Foundation scales

These scales are the initial implementation baseline. A representative shell plus Person, Document, Project, table and family-tree prototype must validate them before they are treated as stable.

### Typography

Roboto is the default interface family, with a local system sans-serif fallback. Monospace is reserved for identifiers, commands, paths and machine values where fixed-width comparison helps.

| Role | Size / line height | Weight | Use |
| --- | --- | --- | --- |
| Page title | 32px / 1.2 | 600 | One primary heading per page |
| Entity title | 30px / 1.2 | 600 | Entity identity within the standard header |
| Section title | 20px / 1.3 | 600 | Major page or panel section |
| Subsection title | 16px / 1.35 | 600 | Nested group, table section or workflow step |
| Body | 15px / 1.5 | 400 | Default reading and control text |
| Compact body | 14px / 1.4 | 400 | Dense tables, lists and secondary tool areas |
| Label | 13px / 1.35 | 600 | Form labels, definition terms and column headings |
| Metadata | 12px / 1.35 | 500 | Timestamps, provenance summaries and compact status text |

Use sentence case. Uppercase may be used only for short eyebrows or compact data headers where letter spacing and contrast remain legible. Do not reduce type to fit a crowded component before trying wrapping, width adjustment or a more appropriate specialised view.

### Spacing

The base scale is `4, 8, 12, 16, 20, 24, 32, 40, 48, 64px`.

- 4–8px: inside compact controls, icon/text gaps and tightly related metadata.
- 12–16px: ordinary control padding and related-item gaps.
- 20–24px: panel padding and separation between component groups.
- 32–40px: major page regions.
- 48–64px: rare page-level breathing room, not routine card padding.

Prefer whitespace and grouping over extra rules or nested panels. Dense views may step down by one spacing token but must not create an unrelated second scale.

### Dimensions

| Role | Initial value | Notes |
| --- | --- | --- |
| Compact control height | 32px | Dense toolbars and icon-only controls with accessible name |
| Default control height | 40px | Forms, filters and ordinary actions |
| Comfortable control height | 44px | Primary touch-relevant or constrained-width actions |
| Expanded sidebar | Candidate 240px | Validate against full navigation labels |
| Collapsed sidebar | Candidate 56px | Validate icon targets and E mark |
| Default readable content | 1120px maximum | Domain pages may choose a narrower reading measure |
| Wide visual content | Available viewport | Maps, graphs and dense tables may use a wider page variant |

Do not encode a single global `main` width for all page types. Page layout selects a documented readable, standard or wide content variant.

### Borders, radii and elevation

- Default border: 1px using the neutral border role.
- Strong separator: 1px using the stronger border role; use sparingly.
- Radius scale: 4px for compact elements, 6px for controls, 8px for panels, 12px for exceptional grouped regions, and a pill radius only for genuine badges/chips.
- Default surfaces are flat. Use no shadow for ordinary panels.
- Floating menus, combobox lists and blocking overlays may use one restrained elevation token plus a border.
- Hover movement such as translating a card is not a default affordance; border, colour or underline changes are preferred.

## Colour roles

The palette uses restrained light blue for its primary accent, while most surfaces and text remain black/white neutrals. Exact values must be contrast-tested. The next implementation must define at least these semantic roles:

| Group | Required roles |
| --- | --- |
| Canvas and surfaces | canvas, panel, inset, selected, overlay |
| Text | primary, secondary, disabled, inverse, link |
| Borders | subtle, default, strong, focus |
| Brand/action | primary, primary-hover, primary-active, primary-subtle |
| Status | info, success, warning, danger, and a subtle surface/text/border combination for each |
| Graph/map | categorical series from the Project E palette, distinct from status roles |

Brand colour must not carry status meaning by itself. Status must remain understandable through text and, where useful, shape or icon. Never use colour as the only indication of required fields, validation, selection, relationship type or graph state.

Current yellow warning and red error treatments are useful semantic precedents; their contrast still requires systematic verification. Application-owned map and graph layers use the same muted palette, with labels, legends and non-colour distinctions; external basemap assets are exempt.

## Component-state contract

Every interactive component must define the states it supports rather than inheriting accidental browser or global styles:

| State | Required treatment |
| --- | --- |
| Rest | Clear control boundary or conventional link affordance |
| Hover | Non-essential enhancement; never the only way to discover an action |
| Focus-visible | High-contrast outline not removed by border or background changes |
| Active/pressed | Immediate feedback without delaying the action |
| Selected/current | Persistent visual and semantic state, including `aria-current` where appropriate |
| Disabled | Visibly unavailable, programmatically disabled and accompanied by reason when non-obvious |
| Read-only | Understandable as data, not merely a disabled input |
| Loading/busy | Preserve layout, identify the affected region and prevent duplicate consequential submission |
| Empty | Explain what is absent and offer the most relevant next action when one exists |
| Invalid | Field-level association plus page/form summary for multi-field submission |
| Warning | Non-blocking risk or review need; explain consequence and available choice |
| Error | Failed or blocked operation; retain user-entered data where safe and explain recovery |
| Success | Confirm completion when redirect or resulting state is not self-evident |

Native browser confirmation dialogs are prototype behaviour, not the standard for consequential flows. Use dedicated confirmation pages or accessible modal dialogs only when the user can review the object, consequence, dependencies and recovery boundary.

## Core component rules

### Buttons and links

- One visually primary action per local decision region.
- Secondary actions use a quieter outlined or text treatment.
- Destructive actions use danger styling only at the point of consequence, not for ordinary navigation to a review page.
- A control that navigates is a link; a control that changes state is a button.
- Icon-only buttons require an accessible name, tooltip on hover/focus and a familiar symbol.

### Panels and cards

- A panel groups related information; it is not the default wrapper for every paragraph.
- Cards are selectable or navigable records/choices. Static information groups are panels.
- Nested bordered panels should be avoided unless the inner boundary carries a distinct state or workflow.

### Form controls

- Labels remain visible; placeholders provide examples, not labels.
- Help text explains format, consequence or non-obvious scope. Do not repeat the label.
- Control height, radius, padding and focus treatment are shared across input types.
- Required status must be conveyed in text and markup. Optional fields are managed by the form's progressive-disclosure rules, not a forest of “optional” suffixes.

### Badges and status indicators

- Use a badge only for compact, scannable categorical state.
- Badge text is plain and specific: `Pending review`, `Archived`, `3 failures`.
- Do not use pill styling for ordinary metadata or every taxonomy value.

## Density and responsive behaviour

Project E has a balanced default density and task-specific compact variants. Compact mode is a component or view decision, not a global user setting at this stage.

- At wide widths, the shell persists and content uses the suitable readable, standard or wide measure.
- At medium widths, the sidebar may collapse, secondary entity actions may move into an overflow menu, and side columns may stack.
- At constrained widths, the page must preserve identity, primary action, navigation escape and current context. Tables, maps and graphs may scroll within labelled containers rather than becoming unreadable card stacks.
- Do not hide domain information solely because width is constrained; change arrangement before reducing content.
- Breakpoints follow content failure, not popular device dimensions. The current 720px and 920px media queries are audit evidence, not permanent tokens.

## Icons

Text is the default interface language. Icons are appropriate for the collapsed sidebar, familiar toolbar actions, status reinforcement, map/graph legends and compact overflow controls.

- The same concept uses one icon throughout the product.
- Domain icons must remain distinguishable at collapsed-sidebar size.
- Decorative icons are hidden from assistive technology.
- Meaningful icons have accessible names or adjacent text.
- Emoji and miscellaneous Unicode glyphs are not a substitute for a coherent icon set.
- Maintain a coherent local SVG icon set. New icons follow documented dimensions, accessible-name and consistency rules; do not add a broad icon-library dependency.

## Accessibility baseline

- Meet WCAG 2.2 AA for ordinary text, large text, controls and meaningful non-text graphics.
- Preserve keyboard access and a logical focus order across navigation, forms, menus, maps and review flows.
- Use semantic landmarks, one page-level `h1`, ordered headings, explicit labels and accessible names.
- Focus must remain visible against every surface.
- Target sizes should be at least 24 by 24 CSS pixels, with 40–44px preferred for ordinary controls.
- Error summaries link to fields where practical; asynchronous status uses appropriate live-region semantics without announcing routine noise.
- Tables identify headers and preserve meaningful reading order. Graph and map views require a textual alternative or list of represented records.
- Respect reduced-motion preferences even though motion is currently minimal.

The current taxonomy combobox includes promising ARIA roles and keyboard scripting, and address lookup exposes a status region. These are established patterns worth retaining, but they require keyboard and assistive-technology verification before being declared conformant.

## Light and dark mode policy

Both light and dark themes are required in the design foundation. Dark is the preferred presentation when the operating system indicates dark; light is the supported companion theme. An explicit user theme switch is deferred. Components consume shared semantic tokens and must not ship with private theme overrides. Both themes require a complete contrast and visual QA pass across shell, forms, tables, maps, graphs and status states.

## Acceptance checks for design-system implementation

- No component depends on undefined tokens or unexplained literal colours.
- Typography, spacing, control dimensions, borders and radii use the documented scales or a recorded exception.
- All applicable interaction states are implemented and keyboard-visible.
- The same semantic status means the same thing across tables, pages, review queues and messages.
- A representative Person, Document, Project, table, form, map and family tree remain readable at wide, medium and constrained widths.
- The implementation has no broad framework or component-library dependency unless a separate decision justifies it.
