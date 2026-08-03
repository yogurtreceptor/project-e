# Phase 1 Domain Form Audit

Date: 2026-07-05

Status: Historical summary; not implementation authority.

This audit tested whether the definition-driven entity model could support useful forms without arbitrary custom fields or parallel storage models. Its approved changes were delivered: progressive optional details, Organisation aliases, Project target/end dates, Document identifier/expiry, Asset manufacturer/model and compound coordinate handling.

## Durable conclusions

Choose storage by meaning:

| Need | Model |
| --- | --- |
| Stable fact belonging only to one domain | Typed entity field |
| Shared flat catalogue value | Reference data |
| Managed hierarchy | Taxonomy |
| Link to another real object | Relationship |
| Numeric fact with selectable unit | Measurement |
| Timestamped observation or progress note | Journal/Timeline source |

`FieldDefinition.optional` means a known field is added on demand in the form; it is presentation metadata, not user-defined schema. Populated optional fields remain visible and values are not cleared when a section is hidden.

Arbitrary per-record fields remain unjustified. They would need their own definitions, types, validation, search, duplicate/merge behavior, provenance, export and display policy. The current definition-driven model covers the demonstrated need with much less complexity.

## Domain outcomes

- **People:** direct phone/email remain pragmatic. Measurements and multi-value references use shared stores. Ethnicity is self-identified and never inferred. Dated observations belong in Journal entries.
- **Organisations:** classification is taxonomy-backed; alternate/trading/former names use normalized aliases; contact fields are optional details. Addresses and named roles remain Relationships.
- **Locations:** name and lookup are primary; detailed address, coordinates and source are optional groups. Coordinates validate as a pair. Locations remain the canonical address owner.
- **Projects:** status/type remain small controlled values. Start, target and end are stable Project facts and Timeline sources. Participants and sponsors remain Relationships; progress and milestones belong in future generalised journals rather than more current-state fields.
- **Documents:** purpose is distinct from MIME/file format. Identifier and expiry are structured facts. Issuer, creator, owner and subject remain Relationships. Uploaded metadata is system-owned.
- **Assets:** manufacturer/model, serial, acquisition, value and coordinates are optional facts. Manuals, receipts and certificates are Documents linked to Assets, not Asset subtypes.

## Remaining decisions

These were deliberately not solved by the audit and still require demonstrated need and explicit authorisation:

- Replace direct contact fields with a reusable Contact Method model only when multiple values, validity periods or communication history justify it.
- Migrate Location country to shared reference data only with conservative mapping and review of unmatched values.
- Clarify Location lookup source versus evidence/provenance; do not let one ambiguous field represent both.
- Redesign Asset value only with explicit valuation kind, decimal amount and currency semantics. Do not add more ambiguous monetary columns.
- Prefer Location Relationships for human-meaningful Asset placement; reserve direct coordinates for inherently point-based or otherwise unmodelled positions.
- Generalise Journals beyond People only after real workflows establish ownership, navigation and lifecycle.

Current field definitions and validation are authoritative. Later architecture and spatial decisions supersede this audit where they conflict; Git history retains the original detailed domain-by-domain analysis.
