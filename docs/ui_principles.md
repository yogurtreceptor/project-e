# UI Principles

The Stage 1 UI should make structured information easy to enter, inspect and navigate.

## Core Experience

- Entity pages are the primary way users interact with Operation Eddy.
- Relationships should be visible, editable and navigable from entity pages.
- Search comes before map-based exploration.
- Forms should stay practical and understandable.
- Pages should feel like profiles of real-world objects, not database rows.

## Reusable Entity Pages

Every entity page should use the same profile architecture:

- Header: name, type, summary and quick actions.
- Overview: concise structured fields from the entity definition.
- Relationships: direct relationships grouped by connected entity type.
- Related Entities: easy graph navigation to connected records.
- Notes: free-text user information.
- Attachments: file metadata placeholder and future upload surface.
- Timeline: created, modified and relationship-event placeholders.
- Metadata: entity ID, type, relationship count, attachment count and timestamps.

Future domains should inherit this page structure by defining fields and labels, not by creating custom page layouts.

## Overview

Overview sections should be short and scannable.

Examples:

- Person: birthday, phone, email, occupation.
- Organisation: address, phone, website.
- Location: address, coordinates.

Only fields with meaningful values should dominate the page. Empty fields should not make the overview noisy.

## Relationships And Navigation

Relationships should not be hidden as secondary metadata.

Entity pages should let users:

- create relationships from the current entity
- edit and delete relationships from the current entity context
- navigate directly to connected entities
- understand relationship direction through labels
- record exact or approximate relationship dates

Navigation should encourage graph exploration without repeatedly returning to the dashboard.

## Attachments

Attachment upload may remain basic or placeholder during early Stage 1, but entity pages should reserve a consistent place for attached files.

Attachment UI should later support file name, notes, storage location and previews where useful.

## Timeline

Timeline starts as a placeholder showing created, modified and relationship-added events.

The structure should support richer history later without redesigning entity pages.

## Exclusions

The Stage 1 UI should not include chat, AI prompts, dispatcher controls, scheduling surfaces, login flows or automation dashboards.
