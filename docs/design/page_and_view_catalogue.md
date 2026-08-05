# Page and View Catalogue

Status: Current route-family reference. Update it when a route family, page purpose or shared renderer changes; do not record small styling changes or completed design history here.

The stable rendering facade is `app/views.py`. `app/view_pages/` owns focused pages and `app/view_pages/layout.py` owns the shared Browse, Calendar and Calendar Settings shells. UI standards live in this directory's focused design documents.

## Primary destinations

| Route | Purpose | Main owner |
| --- | --- | --- |
| `/` | Restrained Home/start page with domain shortcuts, recent records and favourites. | `dashboard.py` |
| `/search` | Global canonical entity/Relationship search with type, favourite and structured filters. | `search.py` |
| `/timeline` | Universal real-world chronology derived from canonical records. | `timeline.py` |
| `/map` | Entity/Relationship-derived map with layer controls and textual alternative. | `map.py` |
| `/calendar` | Month, Week and Day projections; Event preview and Calendar-local creation. | `calendar.py` |
| `/inbox` | Active reminder attention plus retained Archive/deep history. | `inbox.py` |
| `/relationships` | Global Relationship browse/audit surface, inference review and Family Tree access. | `relationships.py` |
| `/system-tools` | Maintenance hub for Data Quality, Taxonomies, Recycle Bin, Audit, portability, Jobs and automation. | `system_tools.py` |

Browse, deterministic Go through the Super Key, and Search remain separate intentions. Ordinary routes must remain visibly navigable without knowing aliases.

## Canonical entity route family

People, Organisations, Locations, Projects, Documents and Assets share these routes:

| Pattern | Purpose |
| --- | --- |
| `/{domain}` | Filterable domain index with Create and Edit access. |
| `/{domain}/new` | Complete-page create form. |
| `/{domain}/{id}` | Read-only, domain-specific Overview in the shared entity frame. |
| `/{domain}/{id}/edit` | Complete-page edit form. |
| `/{domain}/{id}/favourite` | Low-risk favourite toggle and contextual return. |
| `/{domain}/{id}/delete` | Confirmed soft deletion to Recycle Bin. |
| `/{domain}/{id}/merge` | Same-type duplicate selection, preview and confirmed merge. |

Overviews share breadcrumbs, identity, direct Edit/Delete, grouped Views, restrained overflow actions, interpretation warnings, concise Relationships, linked Documents and real-world Timeline. Composition remains domain-specific:

- Person foregrounds contact facts, related Locations and Journal.
- Organisation foregrounds classification, aliases, contact and Location Relationships.
- Location foregrounds preferred/inherited address, representative point, assertion history and containment meaning.
- Project foregrounds status and lifecycle dates.
- Document foregrounds safe local file actions and document facts.
- Asset foregrounds identity, status, value and location meaning.

Routine IDs, storage metadata and full mutation history belong in Audit/technical views rather than Overview.

Person Journal edit/actions and Document download are deliberate domain-specific routes. They do not create parallel entity page models.

## Relationship routes

| Route | Purpose |
| --- | --- |
| `/relationships/new` | Existing- or new-entity workflow with pair-aware perspective labels. |
| `/relationships/{id}` | First-class Relationship detail, including dates and applicable inference origin. |
| `/relationships/{id}/edit` | Dedicated edit form with contextual return. |
| `/relationships/family-tree` | Deterministic SVG projection with legend and textual Relationship alternative. |
| `/relationships/inferences` | Review one deterministic suggestion at a time; Confirm, Reject and Undo history. |

Relationship mutation normally begins from a known entity page. The global browser is primarily a browse/audit surface. Graph and inference views remain projections over canonical Relationships.

## Calendar and attention routes

Human-created Events originate in Calendar workflows. Search and Relationship links may open the read-only `/events/{id}` projection; there is no generic Event index or competing generic create route.

Calendar Settings uses a stripped-back shell and preserves the originating Calendar context:

| Route family | Purpose |
| --- | --- |
| `/calendar/settings` | Settings navigation and local/external ownership groups. |
| `/calendar/settings/add` and Calendar-specific settings | Minimal local Calendar creation and full applicable editing/lifecycle. |
| `/calendar/settings/import` | Preview-first iCalendar file import into an existing or new local Calendar. |
| `/calendar/settings/export` | Selected, all-or-nothing Calendar ZIP export. |
| `/calendar/settings/from-url` | Preview and confirm a public-HTTPS read-only source. |
| `/calendar/settings/other-calendars/{id}` | Edit, refresh, enable/disable or remove one external source. |

`/inbox/count` is a read-only JSON projection for the semantic navigation badge. It creates no attention. Opening an Inbox Event target uses the exact occurrence; operational state transitions remain in the ordinary Inbox workflow.

## System Tools routes

| Route | Purpose |
| --- | --- |
| `/data-quality` | Deterministic findings and user disposition. |
| `/taxonomies` | Organisation and Relationship classification management. |
| `/recycle-bin` | Restore entities/Relationships or enter confirmed permanent deletion. |
| `/system-tools/audit` | Filtered append-only mutation history. |
| `/system-tools/portability` and import/export children | Whole-platform bundle creation, inspection and confirmed apply. |
| `/system-tools/scheduled-jobs` | Registered Job state, Runs, manual execution and controls. |
| `/system-tools/automation` | Registered deterministic rules and Automation Runs. |

Audit, Timeline, Inbox, Job Runs and Automation Runs have different meaning and remain separate destinations/projections.

## Shared experience contracts

- Create/edit forms are one readable column with a top error summary, linked field errors, retained values, progressive optional details and dirty-form protection.
- Tables and wide specialist views use labelled keyboard-scrollable regions and honest empty/no-match/error states.
- Consequential actions use review/confirmation appropriate to their reversibility. Merge and import include a preview; soft deletion is recoverable; permanent deletion is recovery-protected.
- Map and Family Tree retain textual alternatives. Optional map/address network failure never blocks canonical local records.
- Both system-selected themes use shared semantic tokens. Icon-only actions require accessible names and usable targets.
- The current product is desktop-first. Human visual/keyboard verification remains necessary at the supported desktop dimensions.

## Maintenance

When a route changes, update only its row or family description and the responsible focused design standard if a durable rule changed. Resolved implementation history belongs in `docs/build_log.md`; unresolved actionable defects belong in the technical-debt register; product direction belongs in the roadmap or active phase workspace.
