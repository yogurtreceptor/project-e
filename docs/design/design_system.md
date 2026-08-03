# Design System

Status: Current visual and component contract. `app/static/foundation.css` is authoritative for exact tokens and global state policy; `app/static/styles.css` orders focused stylesheet modules. Local icons live under `app/static/icons/`.

## Visual foundation

Project E uses restrained professional styling: Roboto with system sans-serif fallback, flat surfaces, clean borders, balanced density, black/white neutrals and one `#66ccff` accent primitive. Components consume semantic roles rather than literal colours or private theme overrides.

Token names describe purpose (`surface`, `text`, `border`, `action`, `status`, `focus`), not appearance. Add a token only for a repeated role; one-off values need a documented component reason. Tokens are implementation primitives, not user settings.

## Scales

| Scale | Current contract |
| --- | --- |
| Typography | Page/entity titles about 30–32px; section 20px; subsection 16px; body 15px; compact body 14px; labels 13px; metadata 12px. Use sentence case. |
| Spacing | `4, 8, 12, 16, 20, 24, 32, 40, 48, 64px`; use the smaller steps inside controls and larger steps between page regions. |
| Controls | 32px compact, 40px ordinary and 44px comfortable. At least 24×24px target size; prefer 40–44px for ordinary controls. |
| Radii | 4px compact, 6px controls, 8px panels, 12px exceptional groups; pill radius only for genuine badges/chips. |
| Width | Choose readable, standard or wide layout by content. Maps, graphs and comparison tables may use the viewport. |

Ordinary surfaces use a one-pixel semantic border and no shadow. Menus, combobox lists and blocking overlays may use one restrained elevation plus a border. Prefer whitespace and headings over nested boxes.

## Colour and themes

Both system-selected light and dark themes are required; dark is the fallback when no preference is available. A manual theme switch is deferred. Components use shared semantic roles for canvas/surfaces, text, borders, actions, focus and status.

Status roles—information, success, warning and danger—remain distinct from brand and map/graph categories. Colour never carries selection, validation, required state, Relationship meaning or graph state alone. External basemap imagery is outside the application palette, but application overlays require labels, legends or other non-colour distinctions.

## Components and states

Every interactive component defines applicable rest, hover, focus-visible, active, selected/current, disabled, read-only, busy, invalid, warning, error and success states. Focus uses a visible shared treatment that survives dark, selected and invalid backgrounds. Busy states preserve layout and prevent duplicate consequential submission.

- One action is visually primary within a local decision region.
- Navigation uses links; state changes use buttons.
- Danger styling appears at the final consequential action, not ordinary navigation to review.
- Icon-only controls require a familiar symbol, accessible name and hover/focus tooltip.
- Panels group related content; cards represent navigable records, choices or review items.
- Labels remain visible. Placeholders are examples, not labels; help explains format or consequence.
- Badges are for compact categorical state or scoped counts, not ordinary metadata.
- Native confirmation dialogs are not the durable standard for consequential workflows. Use a review page or accessible modal that names the object, effect and recovery boundary.

## Density and width

Balanced density is the default. Compact variants are chosen per view when comparison or volume benefits; they are not a global preference. Reflow and regroup before hiding information. At constrained widths preserve identity, context, the primary action and a navigation escape. Wide tables, maps and graphs may scroll inside labelled keyboard-reachable regions rather than becoming unrelated cards.

Breakpoints follow content failure. Existing media queries are implementation evidence, not permanent product dimensions. The current product remains desktop-first; mobile-specific workflows require separate authorisation.

## Icons

Text is the default. Icons suit the collapsed sidebar, familiar actions, status reinforcement and map/graph legends. Use one icon per concept, hide decorative icons from assistive technology and keep domain icons distinguishable at small sizes. Local SVGs use a 24px view box and coherent rounded strokes; do not add a broad icon-library dependency without a separate decision.

## Accessibility contract

- Target WCAG 2.2 AA contrast for text, controls and meaningful graphics.
- Preserve semantic landmarks, one page `h1`, ordered headings, explicit labels and logical keyboard order.
- Keep focus visible and return it predictably after menus, dialogs and validation.
- Link error summaries to fields; retain entered values and explain recovery.
- Announce relevant asynchronous changes without broadcasting routine refreshes.
- Give tables headers and maps/graphs a textual alternative representing the same information.
- Respect reduced-motion preferences.

Exact CSS and rendered behaviour remain the verification source. Record unresolved accessibility defects in the technical-debt register rather than weakening this contract.
