# Design Implementation Readiness

Status: Decision and prototype register. This document turns the design direction into the remaining choices and evidence needed to catch up from the current prototype. It does not authorise an application redesign by itself.

## How to use this register

Questions marked **Owner answer** need product-owner direction because different answers produce materially different product behaviour or visual identity. Questions marked **Prototype evidence** are resolved by building and reviewing the named representative screens; do not delay the foundation branch by treating them as abstract debate.

Answers update the responsible design standard and are then removed from this register or marked resolved. A prototype finding that changes a durable rule is recorded in that responsible standard, not only here.

## Already decided

- Project E is desktop-first for the current stage and must be designed and verified at 1440 × 900 and 1920 × 1080.
- The shell uses Project E identity, a session-only collapsible sidebar and a Super Key beneath the identity.
- Browse, Go and Search remain distinct.
- Entity Overview is the immediate base-data view. Specialist representations are reached through a labelled, keyboard-operable **Views** control.
- Visual language is predominantly black/white neutrals with `#66ccff` as the single base accent value, flat surfaces and local SVG icons.
- Both dark and light themes use semantic tokens. Follow the operating-system preference when it is known; otherwise start in dark mode. Keyboard focus uses a persistent 2px outer ring during keyboard navigation.
- Home is a jumping-off point. When delivered, Inbox is linked with a small count/ticker rather than embedded there.

## Decisions recorded from the first readiness review

- Dark surfaces use charcoal neutrals. `#66ccff` is the one base accent primitive; semantic primary, hover, selected and focus roles must derive from it in one token definition, not repeat literal colours through renderers.
- The E mark may use an original, deliberately nerdy corporate/industrial letterform inspired by that general aesthetic. It must not copy the Mr. Robot or E Corp artwork.
- The local SVG system uses a 24px view box, with 20px default toolbar rendering and 24px collapsed-sidebar rendering. Use rounded stroke endings for a familiar, legible standard style.
- Search is a dedicated global destination outside entity pages, not an entity-level search field.
- Super Key uses unique aliases only: `map`, `bin`, and similar terms navigate directly with no multiple-match chooser. It may reach authorised future power/admin destinations, but not consequential actions or essential ordinary routes that lack visible navigation.
- The Views button groups representations by kind and includes relevant empty views with clear guidance.
- Document pages lead with preview/open/download. Small safe text/image content may render directly or open in a new tab; large or unsupported files use download.
- Project pages lead with status and milestones.
- Edit and Delete are directly visible entity actions; Merge is contextual/overflow work.
- Application-owned graph and map rendering follows the Project E palette. Exact category assignments wait for the first real layers/relationship categories.
- Inbox count shows all active, not-dismissed items. Dismissal, resolution and conversion to a task must update the item state deliberately.

## Immediate owner questions

These are the only questions worth answering before the first shell and entity-page prototypes. They are deliberately phrased in product terms rather than implementation jargon.

1. **Shortcut:** may we use the common `Ctrl+K` on Windows/Linux and `Cmd+K` on macOS to put the typing cursor in Super Key?
2. **Person page:** when you open a Person, what information should appear first underneath their name? For example: contact details, important relationships, key dates, recent journal notes, or something else. Pick roughly three to five groups.
3. **Warnings:** imagine a Person has a possible duplicate or a Document is close to expiry. Should the page show a noticeable short message directly under the name, or a quieter one-line status with a **Details** link?
4. **Long forms:** for a long edit page, should fields run in one easy-to-read vertical column, or should short related fields sit side by side? For example, Start date and Target date beside each other, with Notes still full width.
5. **After Save:** when someone presses Save changes and sees the updated record, should there also be a brief “Changes saved” message, or is the changed page enough?
6. **Before a risky action:** for something reversible but important, such as removing a relationship, should Project E show a small confirmation box over the current page, or take the user to a separate review page that explains the effect before they confirm?
7. **Long lists:** when People or Documents eventually has many rows, should the user move through numbered pages, press **Load more**, or scroll one long list? This can be answered later if realistic volumes are still unknown.
8. **Empty views:** if a Person has no relationships, should the empty Relationships view show a clear **Add relationship** button, or just a quieter text link?
9. **Messages:** if a save fails, should the error appear near the field that needs fixing, at the top of the page, or both? For example, a bad date needs a message by that date and a short summary at the top.
10. **Graph click:** when a user clicks someone in a family tree, should Project E open that person's Family Tree immediately, or first show a small information panel about them?

## Deliberately deferred questions

- Compact density outside administrative views is decided while implementing the first real high-volume data screen.
- Exact graph/map colours are decided with the first real application-owned layer categories.
- Provenance markers are decided when provenance is delivered as a feature.
- A user-facing theme switch is decided after both system-selected themes exist and have been tested.

## Prototype-evidence questions

29. Does the selected blue meet contrast requirements for text, focus, primary action and selected navigation in both themes?
30. Do Roboto and the proposed type scale remain readable in a dense table, long form, timeline and family tree at both target desktop sizes?
31. Does the 240px sidebar fit every initial label without routine truncation, and does its 56px mode retain clearly recognisable icons and usable targets?
32. Can keyboard-only users open, operate and exit the sidebar, Super Key chooser, Views menu, taxonomy control, overflow menus and destructive confirmation flow with reliable focus return?
33. Do the Person, Document and Project prototypes look appropriately domain-specific while sharing the same tokens, header grammar and form controls?
34. Are dark and light theme changes complete across controls, tables, maps, graphs, overlays, empty/loading/error states and status combinations?
35. Does the local SVG set remain visually coherent at sidebar and toolbar sizes, with accessible names and no ambiguous glyphs?
36. Does the selected table/navigation pattern remain usable with realistic record volumes and long values without hiding identity or priority information?

## Catch-up implementation sequence

1. Create semantic light/dark tokens and a minimal local SVG foundation; contrast-test them.
2. Build the desktop shell: identity, sidebar states, Search entry, Super Key container and keyboard-focus treatment.
3. Build shared controls and states: buttons, menus, form fields, feedback, panels, tables and empty/loading/error patterns.
4. Prototype Person, Document and Project Overview/Edit pages, including the **Views** control and action overflow.
5. Apply table, timeline, map and family-tree standards; verify text alternatives and context preservation.
6. Replace prototype CSS incrementally by route family, updating the page catalogue and evidence as each family reaches the standard.
7. Complete keyboard, contrast and desktop visual QA before declaring the design foundation stable.

## Implementation exit evidence

- Both themes pass contrast checks and use only semantic component tokens.
- The shell and representative entity pages are visually reviewed at 1440 × 900 and 1920 × 1080.
- The shared interaction-state contract is present for every implemented component.
- The first local SVG set is documented and used consistently.
- Keyboard navigation and focus return are manually verified for all shell and form controls.
- Remaining unanswered owner questions are explicitly deferred, not silently improvised in CSS.
