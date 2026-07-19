# Data Presentation Patterns

Status: Working standard. This document governs reusable ways of presenting canonical and derived information. Domain page composition belongs in [entity pages and forms](entity_pages_and_forms.md); attention semantics belong in [operational attention and review](operational_attention_and_review.md).

## General rule

Choose the representation that supports the reading task. Consistency means the same task uses the same pattern; it does not mean all information becomes a card, panel or table.

Every presentation identifies whether it shows:

- canonical domain data;
- a derived view traceable to canonical data;
- operational state requiring action; or
- administrative/audit information.

The interface must not make derived output look like an independently stored competing fact.

## Current pattern audit

The current UI has useful shared tables, definition lists, panels, compact linked-record lists, filters, timeline entries, relationship tables, an accessible SVG family-tree label/legend, map marker lists and consistent empty-message styling. These are foundations worth retaining.

The completed route conversion applies shared semantic tokens, differentiated table/list treatments and clearer domain compositions. It does not introduce speculative asynchronous loading states; current server-rendered workflows should continue to use explicit empty, filtered-empty and error states. Final browser-driven visual and assistive-technology review remains required before every presentation is declared fully verified.

## Tables

Use a table for repeated records with shared fields where column comparison or lookup matters.

### Structure

- Provide a descriptive heading or caption when surrounding context does not make purpose obvious.
- Use semantic headers and stable column order.
- First column is the record identity and usually links to the canonical page.
- Align dates, numbers, statuses and actions consistently by column type.
- Put row actions in a final compact column or overflow; do not let destructive actions dominate scanning.
- Use em dash for deliberately absent compact values only when it cannot be confused with loading or error. Prefer explanatory text in less dense contexts.

### Density and width

- Default tables use balanced row height and 14px compact body text.
- A compact variant is allowed for audit, taxonomy and high-volume operational views after usability testing. Other data views may use it only where comparison demonstrably benefits from higher density.
- On constrained widths, keep identity and priority columns visible. Permit internal horizontal scrolling with a visible focusable region and preserve headers.
- Do not automatically transform every table row into a card; comparison may be the reason the table exists.
- Sticky headers may be used for long data tables, not for small tables.

### Sorting and selection

- Sort only columns with meaningful stable order and show current direction in text/semantics.
- Default order is domain-specific and documented by the view.
- Bulk selection appears only with a real bulk workflow and clear consequence; it is not included speculatively.

### Empty and error behaviour

- No records: explain the empty domain and offer the relevant create action.
- No matches: retain filter controls, state that no items match and offer Clear.
- Failed retrieval: show an error and recovery action; do not show an ordinary empty state.

## Panels and cards

### Panels

A panel groups related static or interactive content within a page. Use it for a coherent section such as Overview, a filter region or Import preview. Avoid placing every section inside identical raised boxes when spacing and headings would communicate hierarchy more clearly.

### Cards

A card represents one navigable record, choice, suggestion or summary with a clear boundary. The whole card may be a link only when nested actions are absent and focus behaviour remains clear.

- Domain launch cards on current Home are a useful pattern, but their record counts should remain secondary.
- Search-result cards are suitable because results include identity, matching context and relationship evidence.
- Inference suggestion cards are suitable because each card is a discrete review decision.
- Static metadata should not become a card merely to create visual variety.

## Compact lists

Use compact lists for short sets where comparison across several fields is unnecessary: favourites, recent entities, linked Documents, map marker alternatives and review history summaries.

- Each row has a primary label and optional concise secondary information.
- The list identifies item type when records from several domains are mixed.
- Avoid repeating the same set already shown in a nearby table.
- More than a screenful of items needs filtering, paging or a dedicated view rather than an infinitely growing panel.

## Filters and views

Filters refine a collection without changing canonical data.

### Filter layout

- Keep common filters visible and place advanced filters behind a labelled disclosure only when demonstrated.
- Apply and Clear/Reset have stable placement.
- Preserve submitted values in controls and the URL where practical.
- Show active filter state and result count near the collection.
- Use domain language, not storage-field names.
- Date filters make inclusive/exclusive boundaries clear when ambiguity matters.

The current entity-index text filter plus favourites control and the Universal Timeline's structured filters are established simple patterns. Search's separate “structured filter” and value fields are functional but should evolve so the value control is specific to the selected filter rather than a generic “Month or year” input.

### Predefined and saved views

- A **predefined view** is product-owned, such as Expiring Documents or Active Projects. It can be added when it represents a demonstrated recurring question.
- A **saved view** stores a user's chosen filter/sort configuration. It is deferred until repeated use demonstrates need.
- Neither creates duplicate records or custom page schemas.
- Do not expose filter-builder configuration merely because the query engine can support it.

## Timelines

Timelines show chronological real-world information or, in a clearly separate administrative view, operational history.

- Real-world Timeline and Change/Audit History remain distinct.
- Each entry includes date/time at suitable precision, event kind, concise title and canonical origin link.
- Derived occurrences identify their source.
- Unknown or approximate dates are displayed honestly; do not manufacture precision.
- Filters remain simple until real use requires more.
- A timeline with no qualifying events explains what contributes events.

The current Universal Timeline's ordered entries and origin links are worth formalising. The current entity sidebar's small Timeline and Change History panels demonstrate the semantic separation but should become specialised views or concise summaries rather than always-visible full lists.

## Relationship presentation

Use three patterns for distinct tasks:

1. **Relationship summary** on Overview: a small domain-prioritised selection or grouped counts with links.
2. **Relationship list/table** for precise connection, role, status, dates and edit/review work.
3. **Graph/tree** for structural exploration.

Do not show all empty entity-type groups. Group by the relationship categories or connected domains meaningful to the current entity. Perspective-specific role labels remain plain-language link text. Relationship status and date uncertainty are separate fields, not encoded only through colour.

## Maps

Maps are derived views over entities and relationships, never a separate source of truth.

- Map layer controls change visibility only.
- Marker popups identify entity, mapped location and a clear destination link.
- A textual mapped-record list provides an accessible and offline-degraded alternative.
- When remote tiles or client assets fail, explain the failure without hiding canonical coordinates or records.
- Focused navigation from an entity should identify that entity without changing marker geometry or data.
- Projects and Documents remain absent as direct markers under current ontology.
- Wide map regions may use the page's wide layout variant and a constrained height that still leaves shell/navigation usable.

The map derives markers from canonical Locations and relationships, retains a mapped-record list, and exposes a visible failure status when the optional remote Leaflet client is unavailable; canonical records and coordinates remain usable.

## Graph and family-tree views

- Graphs visualise stored relationships; they do not infer or persist layout-only connections.
- Selection/highlighting cannot alter geometry unexpectedly.
- Connector styles have a legend and do not rely on colour alone.
- Nodes link to equivalent specialised entity views where context preservation applies.
- The visual has an accessible name and a textual record/relationship alternative.
- Horizontal or two-dimensional internal scrolling is acceptable for a large graph if the container is labelled and keyboard reachable.
- Contradictory or cyclic data is displayed with a clear warning and inspectable underlying relationships.

The deterministic Family Tree retains its established layout, selected-node styling and connector legend while using semantic graph roles. Its labelled keyboard-scrollable visual is paired with a textual relationship list, and contradictory/cyclic edges expose a warning.

## Status indicators

Status is concise domain or operational state, not decoration.

- Use plain text first and a badge when compact scanning benefits.
- Use semantic status roles rather than brand colours.
- Pair colour with wording and, where useful, icon or border treatment.
- Status vocabulary belongs to the domain model or operational standard; UI code must not invent synonyms per page.
- Counts state what they count: `3 pending reviews`, not an unexplained `3`.
- Archived, deleted, rejected, invalidated, disabled and unavailable remain distinct concepts.

## Provenance

Provenance answers “where did this fact or suggestion come from?”

- Place compact provenance beside the relevant fact when source changes interpretation.
- Use an origin label and optional source link; deeper event history belongs in Audit.
- User-entered, imported, inferred, lookup-assisted and system-derived origins must not be visually conflated.
- A generated or inferred item exposes evidence/reason before approval.
- File paths, internal fingerprints and storage implementation details are administrative unless directly needed for diagnosis.

## Data-quality warnings

- A warning is specific, explainable and connected to affected records.
- Severity reflects potential harm or decision urgency, not novelty.
- Non-blocking warnings say what can proceed and what review is recommended.
- Dismissal/disposition follows the data-quality model and does not mutate the underlying fact silently.
- Repeated identical findings are grouped or deduplicated.
- Overview shows only warnings relevant to interpreting or safely acting on that entity; the full finding set belongs in Data Quality.

## Operational summaries

Operational summaries aggregate work without masquerading as domain facts. Examples include pending reviews, recent background outcomes, failed jobs and import results.

- Show the time window and category.
- Link counts to the filtered source view.
- Separate successful background outcomes from attention-requiring failures.
- Do not create dashboard noise from routine success. A compact recent-activity summary is sufficient unless the outcome changes what the user should know or do.
- Use the semantics in [operational attention and review](operational_attention_and_review.md).

## Accessibility and verification

- Representations retain semantic reading order at all widths.
- Tables, maps and graphs have keyboard-reachable containers and text alternatives appropriate to their information.
- Filter labels and result updates are announced without excessive live-region noise.
- Status and warnings remain understandable in monochrome and high contrast.
- Long values wrap or truncate only with a way to reveal the full value.
- Loading does not cause avoidable layout movement or trap focus.

## Implementation acceptance checks

- Every collection uses a justified table, list or card pattern.
- Empty, no-match, loading and error states are visually and semantically distinct.
- Domain indexes expose useful structured fields rather than generic Notes.
- Real-world timeline and operational audit remain separate.
- Relationship summaries, lists and graphs have non-duplicative purposes.
- Map and graph views retain textual alternatives and explicit failure states.
- Status, provenance and warnings use shared roles and vocabulary.
