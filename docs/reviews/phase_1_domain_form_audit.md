# Phase 1 Domain Form Audit

Date: 2026-07-05

## Scope and conclusion

This audit compares the active entity definitions, validation, shared form renderer, typed and external storage, taxonomy and reference stores, relationship catalogue, journal, timeline, and current documentation. It proposes no new domain and makes no application change.

The existing `FieldDefinition.optional` mechanism is a presentation rule: a known, definition-driven field is hidden behind **Add field** until populated. It is not a user-defined schema facility. That is a good Phase 1 boundary. Extend that mechanism across domains before designing dynamic custom fields. Continue to choose storage by semantics: typed scalar columns for stable domain facts, reference data for shared catalogues, taxonomy for managed hierarchies, relationships for links to canonical entities, and journal entries for dated observations.

The smallest useful next iteration is to make currently nullable secondary fields add-on-demand in Organisation, Location, Project, Document, and Asset forms. This reduces form weight without changing storage or migrations. A subsequent small iteration can add only the clearest missing facts: Organisation aliases, Project target/completion date, Document identifier/expiry date, and Asset manufacturer/model. These should remain definition-driven rather than becoming arbitrary per-record fields.

## Current platform behaviour

- Every entity has a canonical `display_name`, shared free-text `notes`, timestamps, favourite/deletion state, and type-specific data. Summary is a legacy compatibility/search field and is not editable.
- Only Person given name, non-Person entity name, and Organisation classification are explicitly required by validation. Defaults populate Person sex (`Unknown`), Project status (`Active`), and Asset status (`Owned`), but blank non-taxonomy fields otherwise validate.
- All editable definition fields appear on create/edit forms. Fields marked `optional=True` appear through **Add field** and remain visible when populated. At present, only selected Person fields use this presentation.
- Structured storage already has four useful modes: scalar typed columns, Organisation taxonomy paths, reusable reference-data links, and measurements. Relationships separately model connections between canonical entities.
- Entity dates for birth, project start, document date, and asset acquisition feed the Universal Timeline. Relationship start/end dates also feed it. Journal infrastructure is generic in storage but its routes currently support People only.

“Normal optional” below means an ordinary always-visible form field that may be blank. “Reusable optional-field definition” means an existing-style `FieldDefinition(optional=True)`, not an end-user-created field definition.

## Domain audit

### People

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Given name | typed text | visible; required | core required free text |
| Middle name, family name | typed text | visible; optional | normal optional free text |
| Sex | controlled typed text | visible; optional in validation, default `Unknown` | small controlled value |
| Birthday | validated ISO date text | visible; optional | structured date; timeline source |
| Email, phone | typed text | visible; optional | free text/contact facts |
| Alias, nickname | typed text | add-on-demand; optional | reusable optional-field definitions |
| Height, weight | shared measurement rows | add-on-demand; optional | structured measurements |
| Languages, nationalities, ethnicities | shared reference links | add-on-demand; optional, multi-value | reference-data-backed |
| Notes | shared entity text | visible; optional | free text; legacy supporting context |

The Person implementation demonstrates the intended extensibility well. Email and phone are pragmatic direct fields, though richer or multiple contact methods would eventually justify a separate reusable contact model rather than more columns. Do not broaden that model in the next iteration. Timestamped observations correctly belong in the journal, not new “last contacted” or observation fields.

### Organisations

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Organisation name | shared entity text | visible; required | core required free text |
| Organisation classification | taxonomy entry, with legacy text compatibility | visible; required | taxonomy-backed hierarchy |
| Website, phone, email | typed text | visible; optional | free text/contact facts |
| Notes | shared entity text | visible; optional | free text |

Problems:

- Three secondary contact fields make every form look mandatory even though they are not.
- Alternate, former, trading, and abbreviated names have no structured home. Putting them in Notes weakens search and duplicate detection.
- Addresses must remain Location relationships; adding address fields would recreate an already-retired duplication.
- People in roles, parent/subsidiary organisations, projects, and issued documents should remain relationships, not embedded names.

Recommendation:

- Keep name and classification visible; keep classification taxonomy-backed and required.
- Make website, phone, and email reusable optional-field definitions now (presentation-only change).
- Add one small multi-value **Other names** capability later, rather than separate legal name/trading name/acronym columns. The first implementation may use one repeatable alias reference/value mechanism only if search and duplicate detection consume it; otherwise defer it rather than add a comma-separated scalar.
- Keep addresses and named contacts as relationships. Employment/membership dates belong on those relationships.
- Keep contact events and organisational observations as future generic journal entries, not “last contacted” fields.

### Locations

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Location name | shared entity text | visible; required | core required free text |
| Address lookup | transient UI helper | create/edit only; optional | derived input, not stored |
| Formatted address | typed multiline text | visible; optional | free text; duplicate-detection input |
| Address lines 1–2, suburb, city, state, post code, country | typed text | visible; optional | structured-by-convention address components |
| Latitude, longitude | range-validated numeric text | visible; optional | structured coordinate pair |
| Source | typed text | visible; optional | free-text origin metadata |
| Notes | shared entity text | visible; optional | free text |

Problems:

- The form exposes eleven stored fields even for a named place with no postal address.
- Formatted address and component fields intentionally overlap, but can drift. The lookup fills both; manual edits have no declared canonical/derived direction.
- Country duplicates the shared country catalogue used by Person nationalities and is vulnerable to spelling variants.
- `source` is ambiguous: it can mean geocoder/provider, evidence, or provenance, while generic per-field provenance already exists.
- Latitude and longitude are independently optional even though a usable coordinate requires both.

Recommendation:

- Keep only Location name and address lookup prominent. Put formatted address, component fields, coordinates, and source behind optional groups; populated fields remain visible.
- Treat latitude/longitude as one optional coordinate concept with pair validation and one add action, even if the existing two columns remain.
- Make country reference-data-backed in a later migration, with a conservative mapping of existing text and preservation of unmapped values for review.
- Define formatted address as a display/search representation and components as structured facts. Do not silently overwrite manual values after initial lookup.
- Replace or narrow `source` rather than generalising it: geocoding provider belongs to lookup metadata; evidence/provenance belongs in the platform provenance model. Until that distinction is implemented, hide Source as an advanced optional field and document its meaning.
- Do not add Organisation/Person address fields. Use Location relationships and their start/end dates for occupancy history. Visits and changing-place observations are relationship dates or journal/timeline events, not Location form fields.

### Projects

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Project name | shared entity text | visible; required | core required free text |
| Project type | controlled text with custom values | visible; optional | small controlled value |
| Status | controlled text | visible; optional in validation, default `Active` | core controlled state |
| Started | validated ISO date text | visible; optional | structured date; timeline source |
| Notes | shared entity text | visible; optional | free text |

Problems:

- The form is already small, but Started is secondary for many organising contexts.
- Custom project types can fragment spelling. A full taxonomy is not yet justified by the small flat list.
- Completed/abandoned status has no corresponding end date, so timeline history is incomplete.
- Owners, managers, sponsors, contributors, organisations, documents, assets, and locations are already relationship concepts and must not become form text.

Recommendation:

- Keep name, status, and type visible. Make Started an optional-field definition if reducing initial form weight consistently across domains.
- Keep project type as its current small controlled/custom field for now. Measure custom-value proliferation before promoting it to taxonomy.
- Add one optional **Target date** only if users need forward-looking reference without scheduling. Add **Ended date** (or Completed date) as the higher-integrity follow-up, with validation consistent with status and timeline registration. These are stable project facts, not journal entries.
- Record milestones, decisions, and progress updates as journal/timeline entries when journal support becomes domain-general. Do not add task, schedule, automation, or goal-execution fields in Phase 1.

### Documents

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Document name | shared entity text | visible; required | core required free text |
| Document type | controlled text with custom values | visible; optional | small controlled value |
| Document date | validated ISO date text | visible; optional | structured date; timeline source |
| Issuer / created by | typed text | visible; optional | free text that overlaps relationships |
| File name, path, MIME type, size | typed metadata | read-only/hidden; populated from upload | system-managed metadata |
| File upload | file storage workflow | visible; optional | local attachment, not a domain field |
| Notes | shared entity text | visible; optional | free text |

Problems:

- Issuer/created by duplicates `document_created_by_person`, `document_created_by_organisation`, and `document_issued_by_organisation` relationships. It also merges two different semantics.
- `Image` and `PDF` are formats already represented by MIME type, while the other document types describe purpose. Mixing both dimensions weakens filtering.
- File name is a weak duplicate key and can collide legitimately.
- Common document facts such as identifier/reference number and expiry date have no structured home.

Recommendation:

- Keep name and type visible. Make document date optional-on-demand; keep file upload visible because it is a primary Document workflow.
- Deprecate Issuer / created by for new structured entry once relationship selection can be integrated conveniently into the Document workflow. Preserve and display legacy text until deliberately migrated; never auto-create an Organisation from it.
- Remove file-format choices from Document type only through a compatibility-aware controlled-value cleanup. MIME type remains the format source of truth.
- Add optional **Document identifier / reference number** and **Expiry date** as the first new Document fields. Both are definition-driven scalar fields; expiry is a validated date and timeline source. Avoid type-specific fields such as passport number until identifier semantics prove insufficient.
- Ownership, holder, issuer, creator, subject, related Asset, and related Project are relationships. Renewal reminders or workflows would cross current Stage 1 boundaries; an expiry date itself does not.

### Assets

| Field | Stored as | Form/requirement | Classification |
|---|---|---|---|
| Asset name | shared entity text | visible; required | core required free text |
| Asset type | controlled text with custom values | visible; optional | small controlled value |
| Status | controlled/custom text | visible; optional in validation, default `Owned` | core controlled state |
| Serial number / asset number | typed text | visible; optional | free text; duplicate-detection input |
| Acquisition date | validated ISO date text | visible; optional | structured date; timeline source |
| Value | non-negative whole-number text, displayed with `$` | visible; optional | partially structured monetary fact |
| Latitude, longitude | range-validated numeric text | visible; optional | structured coordinate pair |
| Notes | shared entity text | visible; optional | free text |

Problems:

- Manufacturer and model are missing, so identity tends to leak into display name or Notes.
- Value assumes a dollar display, has no currency, allows only whole numbers, and does not state whether it is purchase price, current estimate, insured value, or another valuation.
- Direct coordinates can conflict with `stored_at`, `located_at`, or `last_known_at` Location relationships.
- `Document-like asset` and the ontology example of a passport overlap the Document domain. A passport is already explicitly described elsewhere as a Document.
- A single status may lose history (sold/lost/destroyed) unless changes are separately recorded.

Recommendation:

- Keep name, type, and status visible. Make serial number, acquisition date, value, and coordinates reusable optional-field definitions now; present coordinates as a pair.
- Add optional **Manufacturer** and **Model** as the first new Asset fields. Start as definition-driven text; consider Organisation relationships for manufacturer only when canonical organisation navigation is valuable and the form can support it without forcing record creation.
- Do not expand Value in the first iteration. A later redesign should name the valuation kind and store decimal amount plus reference-backed currency. Until then, label it clearly as an approximate value or document the current local-currency assumption; do not add more ambiguous monetary columns.
- Prefer a Location relationship for human-meaningful placement. Reserve direct coordinates for assets whose position is inherently point-based or where no canonical Location is useful, and label this distinction in the UI.
- Remove `Document-like asset` from new Asset type choices after compatibility review; keep existing records readable and use Document-to-Asset relationships for manuals, receipts, certificates, and identity documents.
- Acquisition from/sale to an Organisation or Person belongs in relationships where the counterpart matters. Condition changes, maintenance, valuations, and location observations belong in journal/timeline entries rather than a widening Asset form.

## Cross-domain problems and design rules

1. **Optionality is currently conflated with prominence.** Almost every scalar can be blank, but only Person add-on-demand fields are labelled `optional`. Treat `optional=True` as form prominence, and document that meaning in code before broad adoption. A future rename such as `add_on_demand` would be clearer but is not required for the first change.
2. **The renderer supports individual optional controls, not compound fields.** Coordinates and address groups need grouping semantics to avoid two separate add buttons and awkward partial values. Implement the smallest reusable group metadata rather than domain-specific JavaScript.
3. **Free-text controlled values can fragment.** Continue using flat controlled/custom fields for small lists, but report or review recurring custom values. Promote a field to taxonomy only when users need managed hierarchy, reuse, archive behaviour, or stable navigation—not merely because it has options.
4. **Reference data and taxonomy serve different purposes.** Countries/currencies/languages are shared catalogues; organisation classifications are managed hierarchies. Do not force both through one abstraction.
5. **Relationships are canonical when a value names another real entity.** Addresses, issuers, owners, manufacturers, project participants, and document subjects should not be copied into text when canonical navigation and history matter. Transitional text may remain when relationship-first entry is not yet usable.
6. **Journal/timeline facts are events, not current attributes.** Maintenance, visits, contact, status observations, progress notes, and valuation observations should become dated entries. Stable dates such as birth, acquisition, expiry, project start/end remain entity fields and can derive timeline events.
7. **Arbitrary user-defined fields are premature.** They would require definitions, data types, validation, indexing/search, duplicate/merge behaviour, provenance, export, migration, and display policy. The existing definition-driven model covers the demonstrated need with much less complexity.

## Recommended next iteration

### Iteration 1: form decluttering with no schema change

- Mark Organisation website/phone/email as add-on-demand.
- Keep Location name and lookup prominent; group the detailed address, coordinates, and source as optional sections.
- Optionally hide Project Started behind Add field; retain type and status prominently.
- Mark Document date and legacy issuer as add-on-demand; keep type and upload prominent.
- Mark Asset serial number, acquisition date, value, and coordinate pair as add-on-demand.
- Add reusable optional-group rendering and tests if grouping cannot be achieved cleanly with the current renderer.
- Clarify in architecture/UI documentation that optional-field definitions control progressive disclosure and do not imply a separate dynamic schema.

This iteration is low migration risk, but it still needs create/edit rendering tests, validation tests for grouped coordinates, and a running-application smoke test for every domain.

### Iteration 2: small high-value field additions

1. Document identifier/reference number and expiry date.
2. Asset manufacturer and model.
3. Organisation other names, only with a repeatable representation that participates in search and duplicate review.
4. Project ended date; target date only if forward-looking reference is a confirmed need.

Use the existing additive typed-column migration path for singular scalar fields. Register genuine real-world dates with the timeline and update date sanity checks. Do not implement Organisation aliases as delimiter-packed text.

### Iteration 3: semantic cleanup

- Improve relationship-first Document issuer/creator entry, then deprecate the ambiguous scalar issuer field for new data.
- Separate Document purpose from file format while retaining legacy values.
- Decide and document canonical versus derived Location address representations; move country to shared reference data.
- Redesign Asset value around amount, currency, and valuation meaning before adding more financial fields.
- Generalise journal UI/routes beyond People only when domain observations are implemented.

## Suggested implementation order

1. Document the optional/add-on-demand meaning and add reusable compound/group rendering.
2. Apply presentation-only optionality across Organisations, Locations, Assets, Documents, then Projects.
3. Add Document identifier and expiry date with timeline, migration, duplicate/search, and form tests as appropriate.
4. Add Asset manufacturer/model.
5. Add Project end-date semantics.
6. Design repeatable Organisation aliases with search/merge behaviour.
7. Perform relationship and controlled-value cleanups only after their replacement workflows are usable.

This order prioritises high-value, reversible improvements and avoids cementing duplicated concepts.

## Risks and trade-offs

- Progressive disclosure can hide useful fields from users who do not discover **Add field**. Keep core identity/classification/status fields visible, show populated optional fields automatically, and retain accessible labels and keyboard behaviour.
- Optional groups add renderer complexity. Keep group metadata declarative and domain-neutral; do not create separate form code per entity type.
- Additive columns are simple but can become a wide sparse schema. Limit them to stable, broadly useful domain facts; use external reference/measurement tables only when their semantics require reuse or structure.
- Moving text to relationships improves integrity but raises entry friction and may require creating another entity. Preserve transitional text and never perform consequential automatic conversion.
- Taxonomies improve consistency but impose catalogue maintenance. Flat controls are preferable for short, stable lists.
- Timeline registration can make sensitive or noisy dates broadly visible. Register only dates with clear event meaning and preserve existing filters.
- Alias and identifier improvements affect search, duplicate detection, merge, export, and provenance—not just forms. A superficial column-only implementation would create inconsistent platform behaviour.
- Existing local databases may contain legacy text and controlled values. All semantic cleanups require migration-safe preservation and explicit review paths.

## Documentation impact

No current behaviour changed in this audit, so the Stage 1 specification, architecture, database design, ontology, glossary, UI principles, technical-debt register, and build log remain accurate. If Iteration 1 is implemented, update at least `docs/ui_principles.md`, `docs/architecture.md`, `docs/stage_1_spec.md`, and `docs/ontology.md`; schema-bearing iterations also require `docs/database_design.md` and `docs/build_log.md` updates.
