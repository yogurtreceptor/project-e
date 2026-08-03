# Project E Experience Philosophy

Status: Durable experience principles. Read this for why the interface should feel and behave as it does; use the [focused design standards](design/README.md) for implementation rules.

## Product character

Project E is professional local-first information software for repeated use. It should reward learning with speed, precision and confidence without making ordinary workflows obscure. The interface is restrained, information-led and opinionated by default; configuration is introduced only after real use demonstrates competing valid needs.

The product should feel alive because useful work is visible, not because it demands attention. It avoids engagement tricks, decorative noise and novelty controls.

## Core principles

- **One source, many views.** Canonical records appear through Overview, Search, Timeline, Map, Calendar, graphs and operational views without becoming duplicate truth.
- **Progressive disclosure.** Show the information needed for the current decision; keep specialised, administrative and rarely used detail readily reachable.
- **Page-first orientation.** A dedicated, human-readable page remains the basic unit even if future workspaces compose several views.
- **Domain-specific composition.** Shared grammar creates consistency, but People, Documents, Projects and other domains foreground different facts.
- **Deliberate interaction.** Viewing and editing are separate. Consequential changes expose their object, effect, reversibility and recovery before confirmation.
- **Balanced density.** Ordinary pages are neither sparse nor crowded. Specialist and administrative views may become denser when their task benefits.
- **Evolution over replacement.** New capabilities should extend stable records, routes and views rather than introduce a rival product model.

## Information hierarchy

Keep three layers distinct:

1. **Domain information** describes real objects and Relationships and is visible by default.
2. **Operational information** supports a current action or judgement, such as reminder attention or a failed Job Run.
3. **Administrative information** explains storage, audit and maintenance and normally belongs in System Tools or an Audit view.

Provenance is shown near a fact when its source changes interpretation or trust. Routine IDs, timestamps and storage metadata do not belong on ordinary Overviews merely because they exist.

## Navigation and entity experience

Navigation preserves three intentions:

- **Browse** exposes ordinary destinations visibly.
- **Go** uses the deterministic Super Key for a known destination.
- **Search** retrieves matching canonical information and may return many results.

These intentions may share internal retrieval code but must not collapse into an ambiguous command box. Navigation inside a specialised view preserves context when that matches the user's intent.

An entity Overview answers: “What is this record, what matters now, and where can I go next?” Expansive Relationships, Family Tree, Timeline, Documents, Map and Audit representations use focused views. Home is a restrained platform starting point with useful shortcuts, favourites, recent records and limited situational awareness—not a resume screen or configurable canvas.

## Attention and control

Request attention only when the user can protect information, make a useful decision or understand a meaningful outcome. Routine success belongs in history. Actionable notifications, persistent issues, review proposals, audit events and execution runs retain distinct language and lifecycles.

Low-risk deterministic work may complete within its documented contract. A proposed consequential mutation shows evidence and consequences and uses the same validation, provenance, audit and recovery boundaries as direct human editing. The interface never disguises uncertain or derived output as a confirmed canonical fact.

## Visual and accessibility character

The visual language is modern, quiet and durable: Roboto/system sans-serif typography, flat surfaces, clean borders, restrained cool colour and the `#66ccff` accent primitive. Hierarchy comes primarily from spacing, typography and grouping. Text is the default interface language; familiar icons are compact alternatives, not puzzles.

System-selected light and dark themes use the same semantic roles. Status never relies on colour alone. Keyboard access, visible focus, semantic structure, readable error recovery and textual alternatives for maps/graphs are part of the product contract, not a later polish pass. Motion is minimal and used only when it clarifies state or orientation.

## Current non-goals

Project E is not currently an infinitely configurable dashboard, free-form workspace manager, icon-first consumer application, mobile product, decorative animation showcase or AI/chat interface. These boundaries prevent premature complexity; changing them requires demonstrated need and explicit authorisation.

## Decision test

When an interface choice is unclear, ask:

1. Does it help the user understand or act on information?
2. Does it preserve domain, operational and administrative boundaries?
3. Does it reward learning while keeping ordinary routes visible?
4. Is the added capability necessary, or merely added configuration?
5. Does it extend the canonical page/view model rather than compete with it?
6. Is the result clearer, safer and more coherent rather than merely more noticeable?
