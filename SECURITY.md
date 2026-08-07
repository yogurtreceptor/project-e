# Security Policy

## Supported versions

Project E is under active development and does not yet publish stable releases. Security fixes are made only on the current `main` branch. Older commits, development branches, forks and modified copies are not supported.

## Reporting a vulnerability

Please use [GitHub's private vulnerability reporting](https://github.com/yogurtreceptor/project-e/security/advisories/new) to report a suspected vulnerability. Do not disclose security vulnerabilities in a public issue, discussion or pull request.

Include, where possible:

- a clear description of the vulnerability and its potential impact
- the affected commit, feature or component
- reproducible steps or a minimal proof of concept using fictional or redacted data
- any known mitigations or suggested remediation

Never include a real Project E database, uploaded document, personal information, credentials or other private runtime data in a report.

The maintainer will acknowledge and assess reports as availability permits, may request additional information, and will coordinate disclosure after a fix or mitigation is available. Project E is currently maintained without a guaranteed response or remediation time.

## Scope

Reports about Project E's own code and default configuration are in scope. Vulnerabilities in third-party software or services should normally be reported to their respective maintainers, unless Project E uses them in a way that creates a distinct vulnerability.

General bugs and feature requests belong in the public issue templates, provided they contain no sensitive information.

## Calendar interchange and subscriptions

iCalendar uploads and URL-subscription responses are untrusted input. The application bounds their size and Event count, validates supported Calendar semantics before writes, and stages previews only under ignored local runtime storage. Public subscriptions accept HTTPS only, reject credentials and non-public destinations, revalidate redirects, limit redirect count and response time, and retain the last validated cache if refresh fails.

Calendar subscription query values may contain sensitive tokens. Vulnerability reports, logs and screenshots should redact complete subscription URLs; routine audit notes identify only the source host.

## Spatial packs

Spatial-pack ZIPs and every embedded SQLite/GeoJSON member are untrusted input. Inspection is bounded to a 512 MB archive, 2 GiB declared extracted bytes and 256 KB manifest, accepts exactly four root members, rejects duplicate/absolute/traversal/backslash/link paths, checks available staging space plus reserve, and verifies declared byte counts and SHA-256 digests before opening derived files read-only. MBTiles, search schema/application identity/integrity, zoom/bounds and coverage coordinates are validated before activation.

Validated versions remain in ignored private runtime storage. Activation atomically replaces a small pointer only after validation; a failed update retains the last-known-good pointer and a previous version remains available for rollback. The current first slice refuses a second region until the active pack is explicitly removed. Tile, coverage, transit, renderer and worker resources are allowlisted same-origin paths; the browser style contains no remote resource URL. Pack removal requires typed confirmation, leaves canonical records untouched and does not make public source data part of a recovery export.
