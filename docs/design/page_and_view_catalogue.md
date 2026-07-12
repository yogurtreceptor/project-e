# Page and View Catalogue

Status: Audited baseline of the current post-prototype interface. Routes and behaviour were inspected in `app/web.py`, `app/view_pages/`, `app/static/`, entity definitions, UI-oriented tests and current repository documentation on 2026-07-11. No repository screenshots are present; `README.md` explicitly defers them. A Windows visual smoke connection was unavailable for this WSL workspace, so visual findings are grounded in rendered HTML structure and CSS rather than captured pages.

This catalogue bridges the Experience Philosophy, design standards and later implementation tasks. It is descriptive about current behaviour and normative only where it points to a responsible standard.

## Shared implementation structure

- `app/view_pages/layout.py` renders the single application shell.
- `app/view_pages/entities.py` renders all six entity indexes, detail pages and entity forms through shared definitions.
- `app/view_pages/forms.py` renders shared fields, progressive disclosure, taxonomy/reference controls and address lookup behaviour.
- Focused modules render Dashboard, Relationships, Timeline, Search, Map, Taxonomies, Data Quality, Audit, Recycle Bin, portability and merge flows.
- `app/static/styles.css` remains the global application stylesheet and imports `app/static/foundation.css` as the single incremental design-foundation entry point. `taxonomy.js` supplies the reusable taxonomy-combobox interaction. Several other behaviours are emitted as inline scripts by page renderers.
- The stable public facade remains `app/views.py`.

This module split is maintainable and worth preserving. Design work should improve renderers and route composition behind the facade rather than require a framework migration.

### Foundation smoke checklist

- Load Home and one entity detail page and confirm the existing stylesheet plus `/static/foundation.css` both return CSS successfully.
- Confirm the horizontal shell, forms, tables, Map and Family Tree retain their existing composition while the foundation entry is still intentionally visual-neutral.
- Check the browser console/network panel for missing local static assets.
- Run the focused foundation tests to catch a missing import, malformed shared CSS block or the previously undefined Family Tree text token.

## Current route catalogue

### Shell and broad navigation

| Route | Current purpose and principal actions | Shared implementation | Current assessment / intended direction |
| --- | --- | --- | --- |
| `/` | Dashboard; Search, Browse/Create each entity domain, Browse Relationships, open recent entities and favourites | `dashboard_page()` | Useful launch/discovery patterns, but “Operation Eddy” branding and domain-count emphasis conflict with the Project E command-centre philosophy. Retain curated launch/discovery; add attention/upcoming summaries only with delivered capability. |
| Every page | Persistent Project E header, labelled Search destination and session-collapsible Browse sidebar | `layout()` | Shared shell now exposes all current routes through Information, Connections and views, and System Tools groups; Super Key Go provides deterministic exact-alias navigation and an explicit Search fallback. |
| Unknown route | Generic not-found response | `not_found_page()` | Needs designed missing/recycled distinctions where known and a route back to useful context. |

### Entity domains

The following route family exists for People, Organisations, Locations, Projects, Documents and Assets using slugs `/people`, `/organisations`, `/locations`, `/projects`, `/documents` and `/assets`.

| Route pattern | Current purpose and principal actions | Shared implementation | Current assessment / intended direction |
| --- | --- | --- | --- |
| `/{domain}` | Browse/filter by text and favourites; Create; Edit/Delete per row | `entity_list_page()` | Established index/filter pattern. Domain columns are too generic; Notes is used for every non-Person domain. Move destructive actions out of default rows and define domain-specific scan fields. |
| `/{domain}/new` | Complete-page create form; Save/Save anyway; Cancel | `entity_form_page()` + definition-driven fields | Shared form foundation includes one-column layout, linked summary/field validation, retained values and a consistent dirty-form discard warning. Create Cancel returns to the domain index. |
| `/{domain}/{id}` | Read-only profile with identity/actions, Overview, Geography, all relationship groups, Related Entities, Notes/Journal, Documents, Timeline, Change History and Metadata | `entity_detail_page()` | Shared breadcrumbs, identity/action hierarchy, grouped Views, quiet warnings and icon-only relationship addition are established. Person, Document and Project now use distinct concise compositions and omit duplicate related cards and routine admin metadata; Organisation, Location and Asset remain on the transitional shared composition. |
| `/{domain}/{id}/edit` | Complete-page edit form | Same as create | Correct separation; Cancel returns to the canonical record and dirty navigation requires deliberate discard. |
| `/{domain}/{id}/favourite` | Toggle favourite and return to entity | `favourite_form()` | Useful low-risk direct action; status should be accessible and not dominate header. |
| `/{domain}/{id}/delete` | Soft delete after native confirm and return to index | Inline form in index/header | Recoverable lifecycle uses the shared confirmation modal; entity headers expose Delete directly without permanent danger styling before confirmation. |
| `/{domain}/{id}/merge` | Select duplicate, preview field/relationship effects, confirm merge | `merge_select_page()`, `merge_preview_page()` | Strong review-before-consequence pattern; needs standard breadcrumbs and responsive table treatment. |

### Domain-specific entity routes and content

| Domain / route | Current specialisation | Assessment / intended direction |
| --- | --- | --- |
| Person detail | DOB in index; chronological Journal replaces Notes; relationship labels may be sex-aware | Journal and DOB index are useful deliberate exceptions. Person Overview should prioritise identity/contact/key relationships; move full timeline/audit/admin output to specialised views. |
| `/people/{id}/journal/{entry}/edit` | Dedicated journal edit form | Good view/edit separation. Add contextual breadcrumb and consistent unsaved-change behaviour. |
| Person journal POST actions | Add, archive and permanently delete from detail page | Archive hierarchy is deliberate, but hard delete lacks a consistent confirmation/recovery presentation. |
| Organisation | Classification taxonomy and repeatable aliases | Preserve taxonomy/full-path and aliases; use classification and contact/location in index/Overview instead of Notes. |
| Location create/edit | Optional network address lookup plus manual address/coordinate/source fields | Strong local-first fallback and progressive disclosure. Add explicit loading/failure styling and clarify formatted versus component address presentation. |
| Document detail | Uploaded-file download and metadata; linked-document section omitted | Preserve Document as entity. Prioritise preview/download, purpose, identifier, dates, issuer/creator relationships and provenance; move storage metadata to Audit/technical detail. |
| `/documents/{id}/download` | Direct local file download | Not a page. Keep as canonical Document action with clear unavailable-file error. |
| Asset | Direct coordinates can produce Geography; value displays `$` | Needs clear location-versus-coordinate meaning and valuation semantics. Index should show type/status. |
| Project | Status and several structured dates feed Overview/Timeline | Overview should foreground status, dates and future operational projections rather than generic shared sections. |

### Relationships and graph views

| Route | Current purpose and principal actions | Shared implementation | Current assessment / intended direction |
| --- | --- | --- | --- |
| `/relationships` | Browse all relationships, integrity warnings, Create, open detail/edit/delete, inference queue and family tree | `relationship_list_page()` | Useful global browse/audit view. Needs filters, deliberate warning severity and less prominent direct Delete. |
| `/relationships/new` | Existing/new connected entity workflow, perspective-specific relationship selection, dates/notes, Save/Cancel | `relationship_form_page()` | One of the strongest established workflows. Context return, pair-aware labels and linked summary/field validation are established; unsaved-change handling remains. |
| `/relationships/{id}` | Relationship identity, endpoints, status, dates, notes and inference history | `relationship_detail_page()` | Valid first-class relationship page. Administrative inference evidence should remain progressive/specialised unless it changes interpretation. |
| `/relationships/{id}/edit` | Dedicated relationship edit page | Shared relationship form | Correct separate edit experience and contextual return query. |
| Relationship delete POST | Soft deletes and returns to context or list | Inline forms | Recoverable but lacks confirmation consistency and explicit language. |
| `/relationships/family-tree` | Largest complete family component as deterministic server-rendered SVG plus legend | `family_tree_page()` | Established specialist view. Add person-local route/context preservation, textual alternative, responsive navigation and token cleanup; do not alter canonical graph data. |
| `/relationships/inferences` | One pending suggestion at a time, evidence chain, Confirm/Reject, completed history and Undo | `inference_review_page()` | Strong approval/review precedent. Preserve separation from canonical relationships and extend shared attention semantics rather than turning it into generic notifications. |

### Search, timeline and map

| Route | Current purpose and principal actions | Shared implementation | Current assessment / intended direction |
| --- | --- | --- | --- |
| `/search` | Global text/relationship search; type, favourites and one structured filter; open entity/relationship results | `search_page()` | Canonical Search view is established. Differentiate from Super Key, preserve query/filter state, add result counts and filter-specific value controls. |
| `/timeline` | Universal derived real-world chronology; filters by type/date/direct related Person, Organisation or Project | `universal_timeline_page()` | Strong derived-view semantics and origin links. Retain separation from Audit; refine density and empty-state explanation. |
| `/map` | Leaflet map with entity-derived layer toggles, focused entity query, marker popups and textual marker list | `map_page()` | Strong view-over-canonical-data model and text list. Remote script/tile failure has no designed page state; constrained width and context-preserving entity navigation need standards. |
| `/geocoding/search` | JSON address lookup used by Location form | Not a page | Optional provider boundary is correct. UI must retain manual entry during loading/failure. |

### System Tools

| Route | Current purpose and principal actions | Shared implementation | Current assessment / intended direction |
| --- | --- | --- | --- |
| `/system-tools` | Hub cards for Search, Data Quality, Taxonomies, Recycle Bin, Audit and Import/Export | `system_tools_page()` | Useful nested-navigation hub. Current cards use decorative hover motion contrary to minimal-motion direction; retain labelled descriptions without translation. |
| `/data-quality` | Table of severity, category, explanation, records, status and finding actions | `data_quality_page()` | Correct explainable-tool direction. Needs links to affected records, empty state, shared severity vocabulary and filter/scale plan. |
| `/taxonomies` | Manage Organisation/Relationship hierarchies; filter, show archived, create and archive | `taxonomies_page()` | Strong specialised administrative view with useful hierarchy controls. Needs breadcrumb/local tool nav, explicit validation placement and constrained-width QA. |
| `/recycle-bin` | List deleted entities/relationships, Restore, open entity permanent-delete confirmation | `recycle_bin_page()` | Correct lifecycle separation. Restore and permanent delete need clearer distinct action hierarchy; current table combines record kinds with partially different actions. |
| `/recycle-bin/{id}/permanent-delete` | Dependency review, irreversible confirmation and recovery explanation | `permanent_delete_confirmation_page()` | Established consequential-flow standard worth reusing. |
| `/system-tools/audit` | Filterable operational events by action and record kind | `system_audit_page()` | Correct administrative lens. Move entity-local audit detail here/specialised views instead of default Overview. Needs scalable filtering and compact-table design. |
| `/system-tools/portability` | Export direct download; upload import bundle for validation | `portability_page()` | Clear separation of read-only export and consequential import. Its existing notice now consumes the shared semantic success treatment. |
| `/system-tools/portability/preview` | Verified counts and consequences before confirmed import | `import_preview_page()` | Strong review precedent; add breadcrumb and consistent confirmation layout. |

## Recurring pattern audit

### Application shell

**Established:** one stable frame, active top-level section, global reach to every domain and compact Search.

**Do not formalise:** horizontal all-destination header, Operation Eddy identity, one responsive stack for every width and no nested navigation.

**Established:** 240px expanded and 56px collapsed desktop sidebar candidates, session-only state, labelled global Search, and the local SVG set. Narrow-screen mechanics remain non-committal because Stage 1 is desktop-only; Super Key uses exact `map` and `bin` aliases plus Person-context `tree`.

### Persistent header and sidebar

**Established:** header has global scope and should remain route-independent.

**Established:** persistent left Browse sidebar, expanded/icon states, shallow labelled hierarchy, `aria-current`, active-parent treatment, accessible collapse state and Project E identity.

### Domain indexes

**Established:** page heading, create action, simple filter, empty panel and tabular identity links.

**Do not formalise:** Notes as generic second column, row-level Delete and identical columns across domains.

### Entity overviews and specialised views

**Established:** dedicated canonical pages, read-only default, identity header, definition-driven structured fields, geography where relevant and related canonical links.

**Do not formalise:** all-domain identical long profile, six empty relationship groups, duplicated Related Entities, narrow sidebar full of Timeline/Change History/Metadata and prominent administrative actions.

**Missing:** entity-local specialised routes for Relationships, Timeline, Documents, Map/Family Tree and Audit; person-centred family-tree context; concise domain compositions.

### Forms

**Established:** dedicated pages, shared definition-driven fields, Add details, compound coordinates, manual fallback, taxonomy/reference controls, duplicate review and server validation.

**Do not formalise:** generic Cancel destination and absence of dirty-form warning. Linked summary/field validation and reversible soft-delete confirmation are now shared foundations.

### Tables, lists and filters

**Established:** semantic tables, compact link lists, simple URL-backed filters and clear Apply/Clear actions.

**Do not formalise:** one density/style for every table, generic empty wording where filters may be active, and action columns dominated by lifecycle mutation.

### Search

**Established:** canonical Search page, relationship-context matches, structured filter registry and globally reachable entry.

**Do not formalise:** treating the header Search as the Super Key or using one generic value input for unrelated structured filters.

### Timelines

**Established:** real-world and operational history are semantically separate; Universal Timeline items link to canonical origins.

**Do not formalise:** always-visible mini timeline/audit lists on Overview when they obscure domain information.

### Maps

**Established:** derived markers, layer visibility, marker-to-entity links, focused query and textual record list.

**Do not formalise:** blank map region when optional remote assets fail or fixed 620px height without task/viewport validation.

### Relationships and family tree

**Established:** perspective-aware relationship workflow, first-class relationship pages, deterministic graph layout, connector legend and visual selection that does not alter geometry.

**Do not formalise:** every empty connected-domain group on each profile, missing context-preserving graph navigation and graph-only presentation without equivalent textual relationships.

### Dashboard

**Established:** curated domain launch actions, favourites and recent records.

**Do not formalise:** record totals as the dominant operational story or Home as a resumption-first screen.

### System tools

**Established:** dedicated hub, clear separation from everyday domain navigation, specialised management/review pages and two-step consequential flows.

**Do not formalise:** inconsistent breadcrumbs/back links, one-off message styles and uncoordinated severity/status vocabulary.

### Modals and confirmation flows

No custom modal/dialog component exists. Native `confirm()` is used for soft delete and taxonomy archive; dedicated pages are used for merge, import preview and permanent delete.

**Direction:** dedicated pages are the standard for complex or irreversible consequences. A later accessible modal may handle concise recoverable changes, but only with consistent object/consequence language, focus management and keyboard behaviour.

### Empty, loading, validation and error states

**Established:** `.empty`, `.errors` and `.warnings` presentations; address lookup has status text; many pages name no-content conditions.

**Gaps:** filtered-empty and dataset-empty are not always distinct; Data Quality does not yet consume the shared empty state; remote map failure is silent; not-found is generic. Shared loading/busy, notice and field-associated validation foundations now exist for incremental adoption.

## Stylesheet audit

### Useful foundations

- Light canvas/panel separation, semantic root roles for background/text/muted/border/accent/danger.
- Flat panels, 6–8px control/panel radii, restrained borders and modest spacing.
- Shared control, table, warning, error and responsive rules.
- Specialist styles for taxonomy, relationship workflows, timeline, map and family tree remain locally named.

### Remaining inconsistencies and defects

- The foundation supplies complete shared roles, but literal colours remain in transitional page/component rules pending their numbered conversions.
- Some status and graph renderers still consume independent one-offs rather than the available semantic roles.
- Duplicate declarations exist (`color` in `.readonly-field span`, `z-index` in taxonomy empty state).
- Units mix `px` and `rem`; the documented token scale is available but not yet consumed by every rule.
- `font-weight: 750` and other one-off weights lack a type-scale contract.
- Selected/current state adoption remains incomplete in legacy page-specific components; shared disabled, busy/loading and success/notice foundations are implemented.
- System Tool cards translate upward on hover despite the philosophy's minimal-motion direction.
- Breakpoints at 720px and 920px are accumulated implementation values rather than content-tested tokens.
- One `main` maximum width serves ordinary pages and wide map/graph/table tasks.

The foundation now resolves the Roboto mismatch, missing dark/light theme model, undefined Family Tree token, shared focus treatment and reduced-motion base. Remaining items are addressed by the relevant component, specialist-view and route-family steps rather than expanded opportunistically here.

## Cross-document conflicts found

| Conflict | Evidence | Recommended direction |
| --- | --- | --- |
| Project E philosophy vs Operation Eddy UI identity | Experience Philosophy and repository naming; `layout.py`/Dashboard titles | Use Project E/E mark throughout the shell; the governing philosophy closes this choice. |
| Persistent header/sidebar vs horizontal header | Philosophy; current `layout.py` | Implement shell/sidebar foundation while preserving route reachability. |
| Domain-specific pages vs generic shared profile | Philosophy; `entity_detail_page()`; architecture's inherited shared sections | Keep shared grammar/facade, replace uniform composition with domain-specific render strategies. Update architecture when implemented. |
| Administrative lens vs default Metadata/Change History | Philosophy; current entity sidebar; `ui_principles.md` lists Metadata | Move full admin content to specialised Audit; keep only interpretively relevant provenance/warnings near facts. |
| Home jumping-off point vs record-count/resumption dashboard | Philosophy; `dashboard_page()` | Retain launch/favourite/recent as secondary discovery. Once Inbox exists, provide a restrained Inbox link and small notification count/ticker rather than embedding attention content on Home. |
| Browse/Go/Search separation vs Search-only shell | Philosophy; current header/home/search page | Preserve Search and design distinct Super Key Go control. |
| Minimal motion vs hover translation | Philosophy; `.system-tool-card:hover` | Use border/colour feedback unless motion materially aids comprehension. |

## Decisions safe to carry into implementation

- Preserve stable route/facade and definition-driven architecture.
- Preserve separate view/edit pages, Add details, manual fallback and review-before-consequence patterns.
- Replace shell branding/navigation through one coherent branch, not scattered feature edits.
- Introduce semantic visual roles before component-by-component recolouring.
- Build domain-specific compositions over shared components and canonical records.
- Remove routine administrative metadata from default Overviews when specialised Audit views are introduced.
- Keep maps, timelines and graphs as traceable views over canonical records.
- Treat inference, duplicate, merge, import and delete flows as evidence for a shared review grammar.

## Open questions

The remaining product-owner question D-07 is maintained in the [design documentation index](README.md#product-owner-decisions-still-required); resolved decisions are recorded there too. D-01 is closed by the Experience Philosophy. Page-specific follow-ups that do not require product direction should become scoped implementation tasks after those choices, not additional design documents.

## Catalogue maintenance

Update this file whenever a route family, page purpose, shared renderer or intended specialised view changes. Do not record every small CSS change. Once an inconsistency is fixed, update its assessment and record the completed work in `docs/build_log.md`; remove any corresponding technical-debt item.
