# Project E Experience Philosophy

> A working philosophy for how people should experience, navigate and understand the platform.

Status: Working standard. This document defines experience-level principles. Concrete tokens, dimensions and component specifications belong in the [design system](design/design_system.md).

This repository edition transcribes the supplied **Project E Experience Philosophy** so that future work can cite a version-controlled authority. The philosophy explains why the interface should feel and behave as it does. The documents in [`docs/design/`](design/README.md) explain how those principles are to be applied consistently.

## 1. Purpose

Project E is a local-first personal information and operational platform. Its interface must do more than present records: it must help a person understand information, move through connected contexts, review work performed by the platform, and make deliberate decisions.

This document defines how that experience should feel and behave. It guides information architecture, navigation, entity pages, operational dashboards, visual language and the staged evolution of the interface. It is intentionally broader than a visual style guide and intentionally less specific than a component specification.

## 2. Core experience principles

### Professional operational software

Project E should feel closer to professional GIS, CRM, engineering and administrative software than to a consumer app. It may require some learning, but that learning should be rewarded with speed, precision and confidence.

### Efficient once learned

The interface should support both visible navigation for ordinary use and faster learned paths for frequent use. Experienced users should be able to move quickly without sacrificing clarity for new or occasional users.

### Opinionated by default

Layouts, workflows and priorities should be deliberately designed rather than exposed as settings. Configuration should be introduced only after real use demonstrates that multiple valid patterns exist.

### Progressive disclosure

Complexity should appear when it becomes relevant. Overview pages should remain understandable, while specialised views, audit information, data-quality detail and operational controls remain readily accessible without overwhelming the default experience.

### Adaptive density

The default density should be balanced: neither sparse nor crowded. Collapsible navigation, specialised subviews and compact modes should allow the interface to become denser when the task requires it.

### Evolution over replacement

The page-based interface built now should remain valid when future workspaces, workflows and multi-entity views are added. Later capability should compose existing pages and views rather than invalidate them.

## 3. Information philosophy

The database contains one canonical representation of information. The interface should present that information through multiple useful views without creating competing versions of the truth.

### Views over duplication

A person, organisation, document or project exists once. Overview, timeline, map, relationship graph, family tree, document list and audit history are different renderings of the same underlying entity and its relationships. New interface capability should usually be framed as a new view over existing information rather than a separate feature silo.

### Three information layers

Domain information is visible by default. Operational information appears when it supports action or judgement. Administrative information normally belongs in Audit or Developer views rather than the everyday interface.

### Provenance is not merely administration

Sources and evidence can affect how information should be interpreted. Provenance should therefore be available close to the information it supports, even when deeper audit details remain hidden.

## 4. Navigation philosophy

Project E should keep three user intentions distinct: browsing the platform, going directly somewhere known, and searching the information base.

### Persistent platform frame

A persistent header and left sidebar frame the application. The Project E wordmark or logo appears at the top-left and aligns with the sidebar. When the sidebar collapses, the full identity reduces naturally to the E mark. The sidebar supports nesting, expanded text labels and compact icon presentation.

### The Super Key

The Super Key is a persistent quick-navigation field positioned beneath the Project E identity. It is not a natural-language assistant and not a complex query language. It accepts short codes, concise terms and one-step destinations, including a concise specialised-view term in the current entity context. Its value comes from learned speed and predictability.

### Context preservation

When navigation occurs inside a specialised view, the view should persist where that preserves the user's mental context. Selecting another person from John Smith's family tree should open that person's family-tree rendering, not unexpectedly return to a generic overview.

## 5. Entity experience

### Page-first architecture

The current interface is page-focused. Opening an entity presents a dedicated page for that entity. Future workspaces may embed these pages or specialised views, but the page remains the fundamental human-readable unit.

### Overview plus specialised views

Each entity has a concise Overview containing its identity and the most important everyday information. Complex or expansive representations belong in specialised views reached through a labelled secondary control, such as Relationships, Family Tree, Timeline, Documents, Map, Audit History or future AI Review views.

### View and edit are separate activities

Entity pages are read-only by default. Editing is an explicit action that opens a dedicated form or edit page. The viewing experience is optimised for understanding; the editing experience is optimised for complete, deliberate data entry and validation.

### Domain-specific layouts

Page layouts are highly opinionated and specific to the entity type. A Person should prioritise identity, contact and relationships; a Document should prioritise preview, classification and provenance; a Project should prioritise status, milestones and related work. Consistency should come from shared patterns, not from forcing every domain into an identical layout.

### Administrative lenses

Audit, data-quality, AI-review and developer concerns may be exposed as specialised modes or views. The default page should not continuously display internal metadata simply because it exists.

## 6. Home experience

The home page is a restrained jumping-off point for Project E. It is broad rather than entity-focused and should quickly direct the user to the information or tool they need.

The home page may include universal search, favourites, recent or changed entities and quick actions. Once Inbox exists, it may show a link and small notification count/ticker. These are curated sections, not a fully customisable canvas at the current stage.

### Not a resume screen

The home page should not primarily reopen the last location. Favourites, recent changes, custom lists and direct navigation already support resumption. Home exists to restore broad situational awareness.

### Opinionated dashboard

The dashboard layout is hard-coded while Project E has a single user and an evolving product model. Customisation should be added only after evidence shows that multiple layouts or priorities are genuinely needed.

## 7. Operational philosophy

Project E is expected to perform meaningful work while the user is away. Imports, integrity checks, inference, summarisation, scheduling, monitoring and future AI-assisted processes should produce visible outcomes for review.

### Alive, not chaotic

The platform may be busy because useful work is occurring. The interface should surface that activity in a structured way so the user sees the fruits of background work without being subjected to noise, engagement tricks or arbitrary interruption.

### Actionable attention

Attention should be requested only when the user can make a useful decision, protect information or improve the platform. Pending approvals, failed workflows, expiring documents, inferred duplicates and completed briefings are valid. Marketing prompts, review requests and novelty notifications are not.

### Human approval for high-value work

Background systems may complete low-risk work and prepare higher-value actions for review. The interface should make approvals, evidence and consequences understandable before the user commits a consequential change.

## 8. Visual language

### Overall character

The visual language is modern, timeless, restrained and professional. It should feel like capable software intended for long-term use rather than a marketing-led product optimised for first impressions.

### Colour

The core palette is cool and cohesive, led by the `#66ccff` base blue accent while most surfaces and text remain black/white neutrals. Colours should generally be muted rather than highly saturated. Semantic status colours are defined separately from the brand palette so warnings, approvals and failures remain clear.

### Typography

Roboto is the default typeface. It is familiar, neutral and highly legible across headings, forms, labels, tables and dense operational views. Typography should support hierarchy without becoming decorative.

### Components

Components use flat surfaces, subtle rounded corners, clean borders and restrained visual effects. Hierarchy should rely primarily on spacing, typography, grouping and selective colour rather than heavy shadows or ornamental treatment.

### Text and icons

Text is the primary interface language. Icons act as compact alternatives where space is constrained, such as a collapsed sidebar or dense toolbar. The user should not be forced to memorise ambiguous icons when a clear label can fit.

### Brand identity

Project E should be recognisable. The E mark and Project E wordmark frame the experience, especially in the persistent platform shell, but branding must not compete with the information being used.

### Motion

Animation is not required in the initial interface. Responsiveness and clarity take priority. Motion may be introduced later when it explains a state change or materially improves orientation, but should never delay interaction merely for polish.

## 9. Current constraints and non-goals

At the current stage, Project E is deliberately not trying to become:

- a consumer app optimised for instant familiarity;
- a flashy startup interface driven by trends or decoration;
- an infinitely customisable dashboard or low-code page builder;
- a workspace system in which every panel can be freely docked;
- an icon-first interface that requires memorisation;
- a system that exposes administrative metadata everywhere;
- a single universal layout imposed on every domain.

These are deliberate scope boundaries, not permanent prohibitions. They prevent premature complexity while the platform's real workflows are still being learned.

## 10. Evolution strategy

Each stage should extend the previous one. Page layouts, navigation semantics and entity views should remain coherent rather than being replaced by a different product model.

## 11. Open questions

The following decisions are intentionally deferred to the design system or later experience work:

- exact colour tokens, contrast rules and semantic status palette;
- exact light and dark theme tokens and a future optional theme-switching interaction;
- spacing scale, border radii, component heights and typography sizes;
- detailed rules for domain-specific iconography within the local SVG set;
- precise entity header composition and placement of sources or data-quality indicators;
- remaining Super Key discoverability and shortcut conventions;
- the threshold at which workspaces or user configuration become justified;
- notification, queue and approval interaction patterns for background work.

## 12. Decision test

When a new interface decision is unclear, evaluate it against the following questions:

1. Does it help the user understand or act on information?
2. Does it preserve a clear distinction between domain, operational and administrative concerns?
3. Does it reward learning without making ordinary use obscure?
4. Does it add necessary capability, or merely add configuration?
5. Can it evolve into a future workspace without invalidating the page-based experience?
6. Does it make Project E feel more capable and coherent rather than more decorative or noisy?
