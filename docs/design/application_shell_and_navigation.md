# Application Shell and Navigation

Status: Current shell and navigation contract. Page-body composition belongs in the other focused design standards; exact routes belong in the [page catalogue](page_and_view_catalogue.md).

## Navigation intentions

Project E keeps three intentions distinct:

- **Browse:** visible navigation through domains and platform views.
- **Go:** deterministic Super Key aliases for a known destination.
- **Search:** retrieval across canonical records and Relationships, with filters and potentially many results.

They may share registry or query primitives, but labels and outcomes remain distinct. The Super Key never becomes chat, a query language or a consequential command surface; an unmatched term may offer an explicit Search action.

## Ordinary shell

The desktop shell provides a persistent Project E identity/Home link, Super Key, global Search access, collapsible Browse sidebar, page context and main content. Global controls stay in the shell; entity actions, filters and task-specific controls stay in page headers.

The expanded sidebar groups:

- Home;
- Information: People, Organisations, Locations, Projects, Documents and Assets;
- Calendar and Inbox;
- Connections and views: Relationships, Timeline and Map;
- System Tools: Search, Data Quality, Taxonomies, Recycle Bin, Audit, portability, Scheduled Jobs and automation.

Groups are orientation aids, not empty destinations. Every ordinary route remains visibly reachable without knowing a Super Key alias. Counts appear only when their scope is meaningful and actionable; record totals do not decorate every domain.

The collapsed state is a density control, not reduced capability. Destinations retain consistent icons, accessible names, tooltips and perceptible current state. The known nested-destination discoverability limitation remains tracked in the technical-debt register. Do not duplicate that defect as a competing standard here.

## Project identity and global controls

Expanded navigation shows the E mark with the **Project E** wordmark; collapsed navigation retains the E mark and accessible Home name. Branding frames the product without competing with page or entity identity.

The shell contains only persistent global capability. A future attention indicator requires separately authorised semantics; the current Inbox navigation badge is sufficient. Page creation, record mutation and filter controls are local rather than global.

Calendar Settings is a deliberate task-scoped shell variant. It replaces the ordinary frame with one Settings return control and focused settings navigation while preserving the originating Calendar view, date and visibility context. This exception does not redefine the ordinary shell.

## Super Key and Search

Every Super Key alias has one predictable route. Current global aliases include `map` and `bin`; Person context also supports `tree`. `Ctrl+K` or `Cmd+K` focuses Go without overriding browser or assistive-technology conventions. Aliases map to normal routes and cannot execute a mutation.

Search remains a stable page over canonical entity fields, notes and Relationship context. It preserves query/filter state, reports result count and distinguishes no records, no matches and failure. A compact header or Home entry opens the same canonical Search destination rather than creating another search model.

## Page and local navigation

Breadcrumbs express real hierarchy or return context, such as `People → Person → Edit` or `System Tools → Taxonomies`; flat top-level pages do not need ceremonial breadcrumbs.

Entity Overviews are the base view. A labelled **Views** control reaches applicable Relationships, Family Tree, Timeline, Documents, Map and Audit representations. Links inside a specialised view preserve that view when it matches the task—for example, Person A Family Tree to Person B Family Tree. Ordinary Overview Relationships continue to open the connected record's Overview.

Context is encoded in explicit safe routes/return parameters, not only referrer state. If a destination lacks an equivalent specialised view, fall back to Overview with a clear explanation.

## Home and constrained widths

Home is a curated starting point with domain actions, favourites and recent records. It is not a last-page resume screen or configurable dashboard.

At constrained widths preserve Project E identity, current page/entity identity, one primary action and a navigation escape. Navigation may use a labelled temporary panel; never replace it with unexplained icons. Wide tables, maps and graphs scroll inside labelled regions. This remains a desktop-first contract rather than mobile product authority.

## Accessibility

- Use semantic header, navigation, main and complementary landmarks plus a skip link.
- Mark current destinations and expanded groups programmatically as well as visually.
- Keep sidebar, Super Key, Search, Views, overflow menus and settings navigation keyboard-operable.
- Move and restore focus predictably when menus or dialogs open and close.
- Keep navigation order and labels stable between pages.
- Ensure shortcuts are discoverable and do not require memorisation for ordinary access.
