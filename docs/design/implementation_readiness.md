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
- Visual language is predominantly black/white neutrals with a restrained light-blue accent, flat surfaces and local SVG icons.
- Both dark and light themes use semantic tokens; keyboard focus uses a persistent 2px outer ring during keyboard navigation.
- Home is a jumping-off point. When delivered, Inbox is linked with a small count/ticker rather than embedded there.

## Owner-answer questions

### Theme and visual identity

1. **Theme selection:** when the operating system prefers light, should Project E still open dark by default, or follow the operating-system preference? The current wording contains both intentions and needs one rule.
2. **Accent colour:** which starting blue should be prototyped: a cool sky blue, a muted steel blue, or a deeper ink blue? A named visual reference or hex value is sufficient.
3. **Neutral character:** should dark mode use near-black charcoal surfaces, dark blue-grey surfaces, or black surfaces with subtle blue-grey panels?
4. **Brand identity:** should the E mark be a letterform only, or may it include a simple geometric device? Provide/approve a reference before the shell is treated as visually final.
5. **Icon style:** should local SVG icons be 20px or 24px by default, and use rounded or squared stroke endings? These choices must be consistent across the first icon set.

### Shell and navigation

6. **Sidebar width:** is the 240px expanded / 56px collapsed starting point acceptable for the shell prototype, or should a different width be tried first?
7. **Global Search entry:** should Search be a labelled header action that opens the canonical Search page, or a persistent separate search field in the header?
8. **Super Key scope outside an entity:** should a term such as `people`, `map` or `taxonomies` navigate directly, and should an entity-name match open its Overview? Confirm the allowed destination types.
9. **Super Key result choice:** when a term matches several destinations, should the chooser show a short list immediately or require a confirming Enter key before navigating?
10. **Super Key shortcut:** should the initial version have no shortcut until tested, or use a particular shortcut? Do not choose a browser- or assistive-technology-conflicting combination.
11. **Views control content:** should it show only views with meaningful data, or always show relevant views and give empty-state guidance when there is no qualifying data?
12. **Views menu organisation:** should the labelled **Views** button group representations by kind (for example Data, Visual and Administrative), or use one flat menu while the initial set is small?

### Entity pages and actions

13. **Person Overview:** which three to five groups are highest priority after identity—for example contact, important relationships, recent journal context, key dates and chosen identity details?
14. **Document Overview:** should preview/download be the dominant first region, or should document classification and key dates lead before the preview?
15. **Project Overview:** should immediate status/milestones lead, or should relationships/documents lead when they are more useful than schedule data?
16. **Header actions:** apart from Edit, which actions deserve direct visibility on an entity page (for example Favourite or Add relationship), and which must always remain in overflow?
17. **Warnings:** should interpretation-affecting data-quality warnings be shown as a compact inline callout under the header, or as a small status row with a Details link?

### Forms, collections and feedback

18. **Form layout:** should long desktop forms use a readable single column, or a two-column arrangement for short related fields such as dates and measurements?
19. **Save feedback:** after a successful save, should the page use only the resulting updated state, or also show a brief non-blocking confirmation message?
20. **Confirmation surfaces:** outside permanent delete, should ordinary consequential confirmations use a modal dialog or a dedicated review page? The design system permits either where the consequence is reviewable; choose the ordinary default.
21. **Table navigation:** should ordinary entity indexes paginate, use a Load more control, or use a fixed scrolling table region when record counts grow?
22. **Table density exception:** which non-administrative data views, if any, should start compact—for example Timeline, Relationships, Search results or none?
23. **Empty states:** should relevant empty views lead with an inline action button (for example “Add relationship”), or a text link to keep empty states quieter by default?
24. **Transient messages:** should success/error messages appear at the top of the content column, near the triggering control, or both according to scope?

### Maps, graphs and future operational work

25. **Graph/map categories:** which initial relationship or map-layer categories need distinct palette colours? Give the first real set rather than example transport layers if those are not planned.
26. **Graph detail:** should a selected graph node open a compact inspect panel first, or navigate immediately to the corresponding entity View as current context-preservation guidance allows?
27. **Provenance:** when provenance is implemented, which source states require an immediate visual marker: imported, inferred, lookup-assisted, user-entered, system-derived, or only selected states?
28. **Inbox signal:** when Inbox is delivered, should its Home/sidebar count show every unresolved item, only action-required items, or a separate count by severity?

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
