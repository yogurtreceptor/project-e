# Phase 1 Exit Review

Status: Candidate implementation prepared; maintainer confirmation pending.

Date: 2026-07-05

This review records the evidence prepared for PR #1. It does not declare Phase 1 complete or authorize merging. The maintainer must review the behavior, evidence and remaining limitations and make that decision.

## Required exit evidence

- Fresh database creation is exercised throughout the test suite. Representative additive and rebuilding upgrades from earlier Phase 1 schemas are covered by tests/test_schema_migrations.py.
- Portable export to initialized clean target import is covered by tests/test_portability.py. The round trip preserves canonical IDs, entities, recycled relationships, field provenance and uploaded document bytes, then records the import.
- Bundle validation rejects checksum changes, unsafe or incomplete structure, unsupported/current-schema mismatches, broken SQLite or foreign-key state, invalid entity or relationship structure, and document membership mismatches before apply.
- Import into a non-empty target is rejected without changing its canonical record. Recovery replacement is separately tested and creates a safety backup of the replaced state.
- Confirmed merge and permanent entity deletion create complete recovery bundles first. Merge tests show recycled relationships retain identity and deletion state while endpoints move to the survivor. Permanent-delete previews distinguish active and recycled relationship counts before cascading deletion.
- A simulated WAN failure in tests/test_offline_operation.py leaves canonical records and locally derived coordinate-backed map payloads usable. Geocoding remains optional and its HTTP endpoint reports an empty result/error rather than mutating local records.
- A temporary-port HTTP smoke test exercised System Tools Import and Export, Person creation/detail, search, map rendering, export download, bundle inspection, import preview, confirmation blocking on a populated target, and preservation of the existing Person after the blocked import.
- Required validation at the time of this review: python3 -m unittest discover -s tests passed 144 tests. python3 -m compileall app run.py tests passed immediately before handoff.

## Representative workflow result

The fictional Smoke Person workflow completed create, detail and search while map and portability pages remained available. Export produced a valid one-entity bundle. Import preview displayed verified counts. Confirming that bundle against the populated source returned HTTP 400 with the expected empty-target explanation, and the existing Person remained readable. The first smoke pass exposed a missing exception-module import in that error renderer; it was fixed and the complete path was rerun successfully.

## Remaining limitations and decision

- Import is deliberately whole-platform restore into an empty target, not conflict-aware ingestion into populated canonical data.
- Recovery replacement is command-line-only and requires the explicit --confirm-replace option.
- Remote Leaflet assets, map tiles and Nominatim remain optional WAN resources; fully offline map assets retain their documented trigger.
- Python-filtered discovery and other scale optimizations retain their documented representative-data triggers.

No Phase 1-blocking defect was found after the smoke-test correction. PR #1 should remain draft and Phase 1 should remain unconfirmed until the maintainer reviews this evidence and explicitly decides whether the exit criteria are satisfied.
