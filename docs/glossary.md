# Glossary

Use this document for Project E terms whose meanings are easy to confuse. Canonical domain meaning belongs in [Ontology](ontology.md); current runtime and storage details belong in [Architecture](architecture.md) and [Database Design](database_design.md).

## Identity and lifecycle

| Term | Meaning |
| --- | --- |
| **Canonical record** | The single preferred record for one real-world object. Views and caches may project it but do not become competing truth. |
| **Entity** | A canonical Person, Organisation, Location, Project, Document, Asset or Event with stable shared identity and typed data. |
| **Relationship** | A first-class canonical assertion connecting two entities. Reverse navigation is derived from one stored direction. |
| **Relationship Type definition** | Taxonomy-backed endpoint, direction and perspective-label rules for a selectable Relationship Type. |
| **Archived** | Inactive within a record's normal domain; retained and not placed in the Recycle Bin. |
| **Deleted** | Soft-deleted, hidden from ordinary platform use and recoverable from the Recycle Bin. |
| **Recycle Bin** | The platform view for restoring deleted entities/Relationships or entering confirmed permanent entity deletion. |
| **Alias** | A normalized repeatable alternate entity name used by retrieval and duplicate review. |
| **Approximate date** | The closest known date plus an uncertainty marker—not a date range or partial date. |
| **Address assertion** | A purpose-specific physical, postal or delivery description attached to a Location, with current/preferred state, confidence and source snapshot. |
| **Geometry assertion** | A WGS84 point, line or area attached to a Location for a named role, with current/preferred state, confidence, optional supplied accuracy and source snapshot. |
| **Representative point** | The role-specific Point used for deterministic Location text/form and Map projection; it does not replace other geometry. |
| **Location containment** | A single-parent, cycle-safe `contains_location` Relationship between canonical Locations; inherited address display does not copy the parent's assertion. |

## Spatial and journey terms

| Term | Meaning |
| --- | --- |
| **Journey endpoint** | A deliberate canonical Location plus an explicit or unambiguous current route-anchor, entrance or representative Point; provider snapping is derived and does not move it. |
| **Mobility profile** | Durable user-owned, revisioned assumptions and applicability for one stable Walk, Cycle, Drive or Public transport mode; not a provider preset or learned route history. |
| **Routing policy** | Durable user-owned hard exclusion, soft avoidance, preference, added-cost or added-buffer configuration translated—and never silently weakened—by an adapter. |
| **Journey fingerprint** | SHA-256 identity over every semantic request, resolved endpoint, profile/policy revision and adapter/source dependency that affects result meaning. |
| **Journey cache** | Bounded clearable local performance storage reporting fresh, stale or miss; it is not personal route history or a Calendar materialisation source. |
| **Provider feature** | Replaceable installed or explicitly requested external place context identified by its provider; browsing it is non-mutating. |
| **Map-list membership** | Portable user-owned membership identified by list, provider and feature plus a user label; current provider facts are resolved separately and may be unavailable. |
| **Coverage recommendation** | A display-only comparison of one selected Map point with active reviewed core geometry and declared context bounds; it explains candidate scope, size, network and source evidence but cannot acquire or install a pack. |

## Classification and structured values

| Term | Meaning |
| --- | --- |
| **Controlled field** | A structured domain field with known allowed or suggested values; custom values exist only where explicitly permitted. |
| **Reference data** | Stable reusable flat catalogue values, such as languages or regions, linked instead of copied as text. |
| **Taxonomy** | A reusable local hierarchy of Type, optional Subtype and optional Specific subtype. A record selects one terminal path. |
| **Measurement / canonical unit** | A numeric fact stored in its category's standard unit while retaining the user's display unit. |
| **Structured data** | Named typed fields, references or Relationships used when validation, filtering, navigation or reuse matters. |
| **Notes** | Supporting free text; important categories or statuses should remain structured where practical. |

## Time and attention

| Term | Meaning |
| --- | --- |
| **Event** | A canonical real-world occurrence with one local Calendar, bounded timed or all-day schedule and ordinary Relationships. |
| **Calendar** | The sole local Event grouping/configuration record. It is not an independent Event store. |
| **Calendar Subscription** | A configured read-only public-HTTPS iCalendar source with operational settings and last-known-good cache; its items are not canonical Events. |
| **Calendar projection** | A time display derived from Events or other traceable occurrences; display does not grant Event identity. |
| **Temporal occurrence** | A stable logical instance adapted from a source fact for Calendar, reminder and Inbox processing. The source retains ownership of its date. |
| **Reminder** | Policy deciding when an occurrence should attract attention; it is behaviour, not an entity or delivered item. |
| **Inbox item / notification** | Durable actionable attention produced for a due condition, distinct from its source and reminder definition. |
| **Persistent issue** | A deferred concept for one durable current system/configuration condition. No current Persistent Issue or System Health record exists. |
| **IANA timezone** | A named regional timezone such as `Australia/Brisbane`; precise instants persist in UTC. |
| **iCalendar** | The `.ics` interchange format used for bounded preview-first Calendar import/export and read-only external sources. |

## Derived, operational and historical records

| Term | Meaning |
| --- | --- |
| **Derived projection** | Reproducible output such as a Timeline item, marker, recurring occurrence or data-quality finding; not independently edited truth. |
| **Timeline item** | A derived real-world chronological fact, separate from operational audit history. |
| **Audit event** | Append-only history of a platform mutation or finding disposition; not a canonical Event. |
| **Data-quality finding** | A deterministic recalculated warning; only user disposition/notes persist. |
| **Scheduled Job** | Registered local background work with schedule, recovery policy and run history; not a Calendar Event or arbitrary code. |
| **Job Run** | One execution attempt for a Scheduled Job. |
| **Automation Rule** | Registered deterministic trigger/action configuration containing no executable user code. |
| **Automation Run** | One idempotent execution of an Automation Rule for a stable trigger identity. |
| **Provenance** | Attributable origin information for a fact, record or derived proposal. |
| **Journal entry** | A timestamped observation linked to an entity; currently exposed for People only. |

## Review and assistance

| Term | Meaning |
| --- | --- |
| **Inference suggestion** | A non-canonical, reviewable candidate Relationship derived from existing evidence. |
| **Evidence fingerprint** | Stable identity for the evidence supporting an inference, used to suppress unchanged rejection and detect change. |
| **Inference-created Relationship** | An ordinary confirmed Relationship retaining its rule, evidence and source suggestion. |
| **Deterministic assistance** | Explainable rule-based help or maintenance that stays within documented validation and user-control boundaries. |
| **Artificial intelligence / agent capability** | A separately authorised future capability using model interpretation or agency. It is not Project E's foundation or current primary focus. |
| **Odysseus** | A possible future integration/fork target, not a current dependency or promise. |

## Navigation, project and repository terms

| Term | Meaning |
| --- | --- |
| **Local-first** | Core records and workflows remain useful without WAN access; optional network aids are replaceable. |
| **Super Key / Go** | Deterministic quick navigation to one known route, distinct from Browse, Search, chat and commands. |
| **Specialised view** | A focused representation such as Timeline, Map, Family Tree or Audit over existing canonical/operational sources. |
| **Architecture Decision Record (ADR)** | A retained decision explaining an important structural choice, rationale and consequence. |
| **Repository source of truth** | Current code and repository documentation, not prior chat handoffs. |
| **Task** | A retired experimental entity removed by migration `20260801_31_retire_task_subsystem`; future work management requires a new design. |

Phase 1 and Phase 2 are completed development milestones. Phase 3 Spatial Intelligence is in progress with N1–N5's canonical place, offline-first Map, provider-independent journey foundation, installed-region lifecycle, reviewed provider/list workflows and contextual coverage recommendations delivered, together with X1's Gold Coast prerequisite evidence; production journeys and later slices remain planned. Detailed boundaries belong in the phase documents and [Roadmap](../ROADMAP.md), not glossary definitions.
