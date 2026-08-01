"""Bounded iCalendar parsing, canonical import, and Calendar ZIP export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid
import zipfile

from app.audit import record_audit_event
from app.calendar_service import (
    CalendarInput,
    create_calendar,
    get_calendar,
    next_calendar_sort_order,
)
from app.db_support import utc_now
from app.defaults import DEFAULT_EVENT_DURATION_MINUTES, PLATFORM_TIMEZONE
from app.event_recurrence import RecurrenceRule, get_recurrence, set_recurrence
from app.event_service import EventInput, create_event, get_event, list_events


MAX_ICALENDAR_BYTES = 2 * 1024 * 1024
MAX_ICALENDAR_EVENTS = 10_000
STAGING_TTL_SECONDS = 30 * 60
_DATE_VALUE = re.compile(r"^\d{8}$")
_TOKEN = re.compile(r"^[0-9a-f]{32}$")
_WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
_BLOCKING_PROPERTIES = {
    "ATTACH", "ATTENDEE", "EXDATE", "LOCATION", "ORGANIZER", "RDATE",
    "RECURRENCE-ID", "URL",
}
_SINGLETON_EVENT_PROPERTIES = {
    "UID", "SEQUENCE", "SUMMARY", "DESCRIPTION", "DTSTART", "DTEND",
    "STATUS", "RRULE", "TRANSP", "DTSTAMP", "CREATED", "LAST-MODIFIED",
}
_SUPPORTED_EVENT_PROPERTIES = _SINGLETON_EVENT_PROPERTIES


@dataclass(frozen=True)
class ICalendarEvent:
    uid: str
    sequence: int
    title: str
    description: str
    start_date: str
    end_date_exclusive: str
    status: str
    recurrence: RecurrenceRule | None
    fingerprint: str
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class ICalendarDocument:
    name: str
    timezone: str
    events: tuple[ICalendarEvent, ...]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    product_id: str = ""
    method: str = ""

    @property
    def date_span(self) -> tuple[str, str]:
        if not self.events:
            return "", ""
        return (
            min(event.start_date for event in self.events),
            max(event.end_date_exclusive for event in self.events),
        )

    @property
    def recurring_count(self) -> int:
        return sum(event.recurrence is not None for event in self.events)

    @property
    def can_apply(self) -> bool:
        return not self.blockers and all(not event.blockers for event in self.events)


@dataclass(frozen=True)
class ImportEventPreview:
    event: ICalendarEvent
    classification: str
    existing_event_id: int | None = None


@dataclass(frozen=True)
class ImportPreview:
    document: ICalendarDocument
    events: tuple[ImportEventPreview, ...]
    proposed_name: str
    proposed_timezone: str

    @property
    def can_apply(self) -> bool:
        return bool(self.events) and self.document.can_apply and not any(
            item.classification == "conflicting" for item in self.events
        )


@dataclass(frozen=True)
class ImportResult:
    calendar_id: int
    created_event_ids: tuple[int, ...]
    unchanged_event_ids: tuple[int, ...]


def parse_icalendar(content: bytes) -> ICalendarDocument:
    """Parse a deliberately bounded, all-day iCalendar 2.0 subset."""
    if len(content) > MAX_ICALENDAR_BYTES:
        raise ValueError("iCalendar content exceeds the 2 MB limit.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("iCalendar content must be valid UTF-8.") from error
    if "\x00" in text:
        raise ValueError("iCalendar content contains invalid NUL bytes.")
    physical = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded: list[str] = []
    for line in physical:
        if line.startswith((" ", "\t")):
            if not unfolded:
                raise ValueError("iCalendar content begins with an invalid folded line.")
            unfolded[-1] += line[1:]
        elif line:
            unfolded.append(line)
    if not unfolded:
        raise ValueError("iCalendar content is empty.")

    stack: list[str] = []
    calendar_properties: list[tuple[str, dict[str, str], str]] = []
    event_properties: list[list[tuple[str, dict[str, str], str]]] = []
    current_event: list[tuple[str, dict[str, str], str]] | None = None
    nested_event_component = ""
    calendar_count = 0
    calendar_blockers: list[str] = []
    for line_number, line in enumerate(unfolded, 1):
        name, parameters, value = _parse_content_line(line, line_number)
        if name == "BEGIN":
            component = value.upper()
            if component == "VCALENDAR":
                calendar_count += 1
                if stack or calendar_count > 1:
                    raise ValueError("Exactly one top-level VCALENDAR is required.")
            elif not stack or stack[0] != "VCALENDAR":
                raise ValueError(f"{component} is outside VCALENDAR.")
            if (
                stack == ["VCALENDAR"]
                and component not in {"VEVENT", "VTIMEZONE"}
            ):
                calendar_blockers.append(
                    f"Unsupported Calendar component {component} is present."
                )
            if component == "VEVENT":
                if current_event is not None:
                    raise ValueError("VEVENT components cannot be nested.")
                if len(event_properties) >= MAX_ICALENDAR_EVENTS:
                    raise ValueError("iCalendar content exceeds the 10,000 Event limit.")
                current_event = []
            elif current_event is not None:
                nested_event_component = component
                current_event.append(("BEGIN", {}, component))
            stack.append(component)
            continue
        if name == "END":
            component = value.upper()
            if not stack or stack[-1] != component:
                raise ValueError(f"Mismatched END:{component} on line {line_number}.")
            stack.pop()
            if component == "VEVENT":
                if current_event is None:
                    raise ValueError("VEVENT termination is invalid.")
                event_properties.append(current_event)
                current_event = None
                nested_event_component = ""
            elif current_event is not None and nested_event_component == component:
                current_event.append(("END", {}, component))
                nested_event_component = ""
            continue
        if not stack:
            raise ValueError(f"Property {name} is outside VCALENDAR.")
        if current_event is not None:
            current_event.append((name, parameters, value))
        elif stack == ["VCALENDAR"]:
            calendar_properties.append((name, parameters, value))
    if stack or calendar_count != 1 or current_event is not None:
        raise ValueError("iCalendar component nesting is incomplete.")

    calendar = _property_map(calendar_properties, "Calendar")
    versions = calendar.get("VERSION", [])
    if len(versions) != 1 or versions[0][1] != "2.0":
        raise ValueError("iCalendar VERSION must be exactly 2.0.")
    calscale = _single_value(calendar, "CALSCALE", "")
    if calscale and calscale.upper() != "GREGORIAN":
        raise ValueError("Only the Gregorian iCalendar scale is supported.")
    method = _single_value(calendar, "METHOD", "")
    if method and method.upper() != "PUBLISH":
        raise ValueError("Only published iCalendar data is supported.")
    name = _unescape_text(_single_value(calendar, "X-WR-CALNAME", "")).strip()
    timezone = _unescape_text(_single_value(calendar, "X-WR-TIMEZONE", "")).strip()
    product_id = _single_value(calendar, "PRODID", "")
    events = tuple(_parse_event(properties, index + 1) for index, properties in enumerate(event_properties))
    uids = [event.uid for event in events]
    if len(uids) != len(set(uids)):
        raise ValueError("Duplicate UID values in one upload are not supported.")
    warnings: list[str] = []
    if product_id:
        warnings.append(f"Source product: {product_id}")
    if method:
        warnings.append(f"Source method: {method}")
    return ICalendarDocument(
        name=name,
        timezone=timezone,
        events=events,
        warnings=tuple(warnings),
        blockers=tuple(dict.fromkeys(calendar_blockers)),
        product_id=product_id,
        method=method,
    )


def inspect_icalendar_import(
    connection: sqlite3.Connection,
    content: bytes,
    *,
    filename: str = "",
) -> ImportPreview:
    document = parse_icalendar(content)
    previews: list[ImportEventPreview] = []
    for event in document.events:
        row = connection.execute(
            """SELECT event_id, source_fingerprint
               FROM event_icalendar_identities WHERE source_uid = ?""",
            (event.uid,),
        ).fetchone()
        if row is None:
            previews.append(ImportEventPreview(event, "new"))
        elif row["source_fingerprint"] == event.fingerprint:
            previews.append(ImportEventPreview(event, "unchanged", int(row["event_id"])))
        else:
            previews.append(ImportEventPreview(event, "conflicting", int(row["event_id"])))
    safe_stem = Path(filename).stem.strip() if filename else ""
    proposed_name = document.name or safe_stem or "Imported Calendar"
    return ImportPreview(
        document,
        tuple(previews),
        proposed_name,
        document.timezone or PLATFORM_TIMEZONE,
    )


def apply_icalendar_import(
    connection: sqlite3.Connection,
    content: bytes,
    *,
    destination_calendar_id: int | None = None,
    new_calendar: CalendarInput | None = None,
) -> ImportResult:
    """Apply one confirmed import atomically through canonical service boundaries."""
    preview = inspect_icalendar_import(connection, content)
    blockers = list(preview.document.blockers)
    blockers.extend(
        blocker
        for item in preview.events
        for blocker in item.event.blockers
    )
    conflicts = [item.event.uid for item in preview.events if item.classification == "conflicting"]
    if not preview.events:
        raise ValueError("Import contains no Events.")
    if blockers:
        raise ValueError("Import is blocked: " + "; ".join(blockers))
    if conflicts:
        raise ValueError("Changed source UIDs require a reviewed update workflow: " + ", ".join(conflicts))
    if (destination_calendar_id is None) == (new_calendar is None):
        raise ValueError("Choose either one existing Calendar or one new Calendar destination.")
    new_items = [item for item in preview.events if item.classification == "new"]
    unchanged = tuple(
        item.existing_event_id for item in preview.events
        if item.classification == "unchanged" and item.existing_event_id is not None
    )
    if not new_items:
        if destination_calendar_id is not None and get_calendar(connection, destination_calendar_id) is None:
            raise ValueError("The selected destination Calendar is unavailable.")
        return ImportResult(destination_calendar_id or 0, (), unchanged)

    try:
        connection.execute("BEGIN IMMEDIATE")
        if new_calendar is not None:
            destination_calendar_id = create_calendar(
                connection,
                new_calendar,
                commit=False,
                provenance="imported",
            )
        destination = get_calendar(connection, int(destination_calendar_id or 0))
        if destination is None or destination.kind != "event":
            raise ValueError("The selected active Event Calendar is unavailable.")
        created: list[int] = []
        for item in new_items:
            source = item.event
            inclusive_end = (
                date.fromisoformat(source.end_date_exclusive) - timedelta(days=1)
            ).isoformat()
            event_id = create_event(
                connection,
                EventInput(
                    title=source.title,
                    notes=source.description,
                    calendar_id=destination.id,
                    all_day=True,
                    start_date=source.start_date,
                    end_date=inclusive_end,
                ),
                commit=False,
                provenance="imported",
                status=source.status,
            )
            event = get_event(connection, event_id, include_archived=True)
            if event is None:
                raise ValueError("Imported Event could not be reloaded.")
            if source.recurrence is not None:
                set_recurrence(
                    connection,
                    event,
                    source.recurrence,
                    commit=False,
                    provenance="imported",
                )
            connection.execute(
                """INSERT INTO event_icalendar_identities
                   (event_id, source_uid, source_sequence, source_fingerprint, imported_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (event_id, source.uid, source.sequence, source.fingerprint, utc_now()),
            )
            created.append(event_id)
        record_audit_event(
            connection,
            "import",
            [("calendar", destination.id), *(("entity", event_id) for event_id in created)],
            after={
                "created_events": len(created),
                "unchanged_events": len(unchanged),
                "source_calendar_name": preview.document.name,
            },
            notes="iCalendar upload imported into canonical Events",
            provenance="imported",
        )
        connection.commit()
        return ImportResult(destination.id, tuple(created), unchanged)
    except Exception:
        connection.rollback()
        raise


def new_import_calendar_input(
    connection: sqlite3.Connection,
    name: str,
    colour: str,
    timezone: str,
) -> CalendarInput:
    return CalendarInput(
        name=name,
        colour=colour,
        timezone=timezone,
        default_event_duration_minutes=DEFAULT_EVENT_DURATION_MINUTES,
        sort_order=next_calendar_sort_order(connection),
    )


def stage_icalendar(content: bytes, staging_dir: Path) -> str:
    if len(content) > MAX_ICALENDAR_BYTES:
        raise ValueError("iCalendar content exceeds the 2 MB limit.")
    staging_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    (staging_dir / f"calendar-{token}.ics").write_bytes(content)
    return token


def read_staged_icalendar(token: str, staging_dir: Path, *, consume: bool = False) -> bytes:
    if not _TOKEN.fullmatch(token):
        raise ValueError("Calendar import preview token is invalid.")
    path = staging_dir / f"calendar-{token}.ics"
    if not path.is_file() or time.time() - path.stat().st_mtime > STAGING_TTL_SECONDS:
        if path.is_file():
            path.unlink()
        raise ValueError("Calendar import preview has expired or does not exist.")
    content = path.read_bytes()
    if consume:
        path.unlink()
    return content


def discard_staged_icalendar(token: str, staging_dir: Path) -> None:
    if not _TOKEN.fullmatch(token):
        raise ValueError("Calendar import preview token is invalid.")
    path = staging_dir / f"calendar-{token}.ics"
    if path.is_file():
        path.unlink()


def create_calendar_export(
    connection: sqlite3.Connection,
    selections: list[str],
) -> bytes:
    """Build an all-or-nothing ZIP containing one ordinary ICS per source."""
    if not selections:
        raise ValueError("Select at least one Calendar source to export.")
    if len(selections) != len(set(selections)):
        raise ValueError("Calendar export selection contains duplicates.")
    members: list[tuple[str, bytes]] = []
    errors: list[str] = []
    for selection in selections:
        kind, separator, identifier = selection.partition(":")
        if not separator or not identifier.isdigit() or kind not in {"local", "external"}:
            errors.append(f"{selection}: invalid source identifier")
            continue
        source_id = int(identifier)
        try:
            if kind == "local":
                name, content = _export_local_calendar(connection, source_id)
            else:
                name, content = _export_external_calendar(connection, source_id)
            members.append((_member_name(name, kind, source_id), content))
        except ValueError as error:
            errors.append(f"{selection}: {error}")
    if errors:
        raise ValueError("Export compatibility check failed: " + "; ".join(errors))
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)
    return output.getvalue()


def serialize_document(document: ICalendarDocument) -> bytes:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Project E//Calendar Interchange//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    if document.name:
        lines.append("X-WR-CALNAME:" + _escape_text(document.name))
    if document.timezone:
        lines.append("X-WR-TIMEZONE:" + _escape_text(document.timezone))
    for event in document.events:
        lines.extend(_serialize_event(event))
    lines.append("END:VCALENDAR")
    return _fold_lines(lines)


def _parse_event(
    properties: list[tuple[str, dict[str, str], str]],
    position: int,
) -> ICalendarEvent:
    mapped = _property_map(properties, f"Event {position}")
    blockers: list[str] = []
    warnings: list[str] = []
    for property_name in _SINGLETON_EVENT_PROPERTIES:
        if len(mapped.get(property_name, [])) > 1:
            blockers.append(f"Event {position} repeats singleton property {property_name}.")
    uid = _single_value(mapped, "UID", "").strip()
    if not uid:
        blockers.append(f"Event {position} has no stable UID.")
    sequence_text = _single_value(mapped, "SEQUENCE", "0").strip()
    try:
        sequence = int(sequence_text)
        if sequence < 0:
            raise ValueError
    except ValueError:
        sequence = 0
        blockers.append(f"Event {position} has an invalid SEQUENCE.")
    title = _unescape_text(_single_value(mapped, "SUMMARY", "")).strip()
    if not title:
        blockers.append(f"Event {position} has no SUMMARY.")
    description = _unescape_text(_single_value(mapped, "DESCRIPTION", "")).strip()
    start_values = mapped.get("DTSTART", [])
    if len(start_values) != 1:
        blockers.append(f"Event {position} must have one DTSTART.")
        start_date = ""
    else:
        start_parameters, start_value = start_values[0]
        if not _is_date_property(start_parameters, start_value):
            blockers.append(f"Event {position} is timed; timed iCalendar import is not supported yet.")
            start_date = ""
        else:
            start_date = _ical_date(start_value, f"Event {position} DTSTART", blockers)
    end_values = mapped.get("DTEND", [])
    if len(end_values) > 1:
        blockers.append(f"Event {position} repeats DTEND.")
    if end_values:
        end_parameters, end_value = end_values[0]
        if not _is_date_property(end_parameters, end_value):
            blockers.append(f"Event {position} has a timed DTEND.")
            end_date = ""
        else:
            end_date = _ical_date(end_value, f"Event {position} DTEND", blockers)
    else:
        end_date = (date.fromisoformat(start_date) + timedelta(days=1)).isoformat() if start_date else ""
    if start_date and end_date and end_date <= start_date:
        blockers.append(f"Event {position} DTEND must be exclusive and after DTSTART.")
    status_value = _single_value(mapped, "STATUS", "CONFIRMED").upper()
    if status_value not in {"CONFIRMED", "CANCELLED"}:
        blockers.append(f"Event {position} STATUS {status_value or '(empty)'} is unsupported.")
    status = "cancelled" if status_value == "CANCELLED" else "planned"
    recurrence = None
    recurrence_values = mapped.get("RRULE", [])
    if len(recurrence_values) > 1:
        blockers.append(f"Event {position} has multiple recurrence rules.")
    elif recurrence_values and start_date:
        recurrence = _parse_recurrence(recurrence_values[0][1], start_date, position, blockers)
    if mapped.get("TRANSP"):
        warnings.append(f"Event {position} transparency is not represented by Project E.")
    for property_name in sorted(_BLOCKING_PROPERTIES):
        if mapped.get(property_name):
            blockers.append(f"Event {position} uses unsupported {property_name}.")
    for property_name in sorted(mapped):
        if (
            property_name not in _SUPPORTED_EVENT_PROPERTIES
            and property_name not in _BLOCKING_PROPERTIES
            and not property_name.startswith("X-")
        ):
            blockers.append(f"Event {position} uses unsupported {property_name}.")
    if any(name == "BEGIN" and value == "VALARM" for name, _params, value in properties):
        blockers.append(f"Event {position} contains a VALARM.")
    semantic = {
        "uid": uid,
        "sequence": sequence,
        "title": title,
        "description": description,
        "start_date": start_date,
        "end_date_exclusive": end_date,
        "status": status,
        "recurrence": recurrence.__dict__ if recurrence else None,
    }
    fingerprint = hashlib.sha256(
        json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ICalendarEvent(
        uid,
        sequence,
        title,
        description,
        start_date,
        end_date,
        status,
        recurrence,
        fingerprint,
        tuple(warnings),
        tuple(dict.fromkeys(blockers)),
    )


def _parse_recurrence(
    value: str,
    start_date: str,
    position: int,
    blockers: list[str],
) -> RecurrenceRule | None:
    parts: dict[str, str] = {}
    for item in value.split(";"):
        key, separator, part_value = item.partition("=")
        key = key.upper()
        if not separator or not key or key in parts:
            blockers.append(f"Event {position} has an invalid RRULE.")
            return None
        parts[key] = part_value.upper()
    allowed = {"FREQ", "INTERVAL", "BYDAY", "UNTIL", "COUNT", "WKST"}
    unsupported = sorted(set(parts) - allowed)
    if unsupported:
        blockers.append(f"Event {position} RRULE uses unsupported {', '.join(unsupported)}.")
        return None
    frequency = parts.get("FREQ", "").lower()
    if frequency not in {"daily", "weekly", "monthly", "yearly"}:
        blockers.append(f"Event {position} RRULE frequency is unsupported.")
        return None
    try:
        interval = int(parts.get("INTERVAL", "1"))
        if interval <= 0:
            raise ValueError
    except ValueError:
        blockers.append(f"Event {position} RRULE INTERVAL must be positive.")
        return None
    if parts.get("WKST", "MO") != "MO":
        blockers.append(f"Event {position} RRULE uses a non-Monday week start.")
    weekdays: tuple[int, ...] = ()
    ordinal = 0
    monthly_weekday = -1
    if "BYDAY" in parts:
        parsed_days: list[int] = []
        for token in parts["BYDAY"].split(","):
            match = re.fullmatch(r"([+-]?\d+)?(MO|TU|WE|TH|FR|SA|SU)", token)
            if not match:
                blockers.append(f"Event {position} RRULE BYDAY is invalid.")
                return None
            prefix, weekday = match.groups()
            if prefix:
                if frequency != "monthly" or len(parts["BYDAY"].split(",")) != 1:
                    blockers.append(f"Event {position} RRULE ordinal BYDAY is unsupported here.")
                    return None
                ordinal = int(prefix)
                if ordinal not in {-1, 1, 2, 3, 4, 5}:
                    blockers.append(f"Event {position} RRULE ordinal BYDAY is unsupported.")
                    return None
                monthly_weekday = _WEEKDAYS[weekday]
            else:
                parsed_days.append(_WEEKDAYS[weekday])
        if parsed_days:
            if frequency != "weekly":
                blockers.append(f"Event {position} RRULE BYDAY is not losslessly representable.")
                return None
            weekdays = tuple(sorted(set(parsed_days)))
    if "COUNT" in parts and "UNTIL" in parts:
        blockers.append(f"Event {position} RRULE cannot contain both COUNT and UNTIL.")
        return None
    until_date = ""
    if "UNTIL" in parts:
        until_date = _ical_date(parts["UNTIL"], f"Event {position} RRULE UNTIL", blockers)
    rule = RecurrenceRule(frequency, interval, weekdays, ordinal, monthly_weekday, until_date)
    anchor = date.fromisoformat(start_date)
    if not _matches_rule(anchor, anchor, rule):
        blockers.append(
            f"Event {position} DTSTART does not match its recurrence pattern."
        )
        return None
    if until_date and date.fromisoformat(until_date) < anchor:
        blockers.append(f"Event {position} RRULE UNTIL precedes DTSTART.")
        return None
    if frequency == "monthly" and not ordinal and anchor.day > 28:
        blockers.append(
            f"Event {position} monthly recurrence would change month-end semantics."
        )
        return None
    if frequency == "yearly" and (anchor.month, anchor.day) == (2, 29):
        blockers.append(
            f"Event {position} yearly recurrence would change leap-day semantics."
        )
        return None
    if "COUNT" in parts:
        try:
            count = int(parts["COUNT"])
            if count <= 0 or count > 100_000:
                raise ValueError
        except ValueError:
            blockers.append(f"Event {position} RRULE COUNT is invalid.")
            return None
        try:
            until = _until_for_count(anchor, rule, count)
        except ValueError:
            blockers.append(f"Event {position} RRULE COUNT exceeds the supported horizon.")
            return None
        rule = RecurrenceRule(
            frequency, interval, weekdays, ordinal, monthly_weekday, until.isoformat()
        )
    return rule


def _until_for_count(anchor: date, rule: RecurrenceRule, count: int) -> date:
    matched = 0
    current = anchor
    for _ in range(366 * 1000):
        if _matches_rule(current, anchor, rule):
            matched += 1
            if matched == count:
                return current
        current += timedelta(days=1)
    raise ValueError("RRULE COUNT expands beyond the supported recurrence horizon.")


def _matches_rule(current: date, anchor: date, rule: RecurrenceRule) -> bool:
    days = (current - anchor).days
    if rule.frequency == "daily":
        return days % rule.interval == 0
    if rule.frequency == "weekly":
        anchor_week = anchor - timedelta(days=anchor.weekday())
        current_week = current - timedelta(days=current.weekday())
        weeks = (current_week - anchor_week).days // 7
        return (
            weeks % rule.interval == 0
            and current.weekday() in (rule.weekdays or (anchor.weekday(),))
        )
    if rule.frequency == "monthly":
        months = (current.year - anchor.year) * 12 + current.month - anchor.month
        if months < 0 or months % rule.interval:
            return False
        if rule.monthly_ordinal:
            if current.weekday() != rule.monthly_weekday:
                return False
            if rule.monthly_ordinal == -1:
                return (current + timedelta(days=7)).month != current.month
            return (current.day - 1) // 7 + 1 == rule.monthly_ordinal
        from calendar import monthrange
        return current.day == min(anchor.day, monthrange(current.year, current.month)[1])
    years = current.year - anchor.year
    if years < 0 or years % rule.interval:
        return False
    from calendar import monthrange
    return current.month == anchor.month and current.day == min(anchor.day, monthrange(current.year, current.month)[1])


def _export_local_calendar(connection: sqlite3.Connection, calendar_id: int) -> tuple[str, bytes]:
    calendar = get_calendar(connection, calendar_id, include_archived=True)
    if calendar is None:
        raise ValueError("local Calendar does not exist")
    events = [event for event in list_events(connection) if event.calendar_id == calendar_id]
    exported: list[ICalendarEvent] = []
    for event in events:
        if not event.is_all_day:
            raise ValueError(f"{event.title} is timed and cannot yet be exported losslessly")
        if event.date_precision != "exact":
            raise ValueError(
                f"{event.title} has an approximate date and cannot be exported losslessly"
            )
        if connection.execute(
            "SELECT 1 FROM event_recurrence_exceptions WHERE event_id = ? LIMIT 1",
            (event.id,),
        ).fetchone():
            raise ValueError(f"{event.title} has recurrence exceptions")
        recurrence = get_recurrence(connection, event.id)
        if recurrence is not None:
            anchor = date.fromisoformat(event.start_date)
            if (
                recurrence.rule.frequency == "monthly"
                and not recurrence.rule.monthly_ordinal
                and anchor.day > 28
            ):
                raise ValueError(
                    f"{event.title} changes month-end recurrence semantics"
                )
            if (
                recurrence.rule.frequency == "yearly"
                and (anchor.month, anchor.day) == (2, 29)
            ):
                raise ValueError(
                    f"{event.title} changes leap-day recurrence semantics"
                )
        identity = connection.execute(
            "SELECT * FROM event_icalendar_identities WHERE event_id = ?",
            (event.id,),
        ).fetchone()
        uid = identity["source_uid"] if identity else f"project-e-event-{event.id}@local"
        sequence = int(identity["source_sequence"]) if identity else 0
        semantic = {
            "uid": uid,
            "sequence": sequence,
            "title": event.title,
            "description": event.notes,
            "start_date": event.start_date,
            "end_date_exclusive": event.end_date_exclusive,
            "status": event.status,
            "recurrence": recurrence.rule.__dict__ if recurrence else None,
        }
        exported.append(ICalendarEvent(
            uid,
            sequence,
            event.title,
            event.notes,
            event.start_date,
            event.end_date_exclusive,
            event.status,
            recurrence.rule if recurrence else None,
            hashlib.sha256(json.dumps(semantic, sort_keys=True, default=list).encode()).hexdigest(),
        ))
    document = ICalendarDocument(calendar.name, calendar.timezone, tuple(exported))
    return calendar.name, serialize_document(document)


def _export_external_calendar(connection: sqlite3.Connection, subscription_id: int) -> tuple[str, bytes]:
    source = connection.execute(
        "SELECT * FROM calendar_subscriptions WHERE id = ?",
        (subscription_id,),
    ).fetchone()
    if source is None:
        raise ValueError("external Calendar source does not exist")
    if not source["last_success_at"]:
        raise ValueError("external Calendar has no validated cache")
    rows = connection.execute(
        """SELECT * FROM external_calendar_events
           WHERE subscription_id = ? ORDER BY start_date, id""",
        (subscription_id,),
    ).fetchall()
    events = tuple(_event_from_external_row(row) for row in rows)
    document = ICalendarDocument(source["name"], source["timezone"], events)
    return source["name"], serialize_document(document)


def _event_from_external_row(row: sqlite3.Row) -> ICalendarEvent:
    recurrence = RecurrenceRule(**json.loads(row["recurrence_json"])) if row["recurrence_json"] else None
    return ICalendarEvent(
        row["source_uid"],
        int(row["source_sequence"]),
        row["title"],
        row["description"],
        row["start_date"],
        row["end_date_exclusive"],
        row["status"],
        recurrence,
        row["source_fingerprint"],
    )


def _serialize_event(event: ICalendarEvent) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        "UID:" + _escape_text(event.uid),
        f"SEQUENCE:{event.sequence}",
        "DTSTAMP:" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "SUMMARY:" + _escape_text(event.title),
        "DTSTART;VALUE=DATE:" + event.start_date.replace("-", ""),
        "DTEND;VALUE=DATE:" + event.end_date_exclusive.replace("-", ""),
        "STATUS:" + ("CANCELLED" if event.status == "cancelled" else "CONFIRMED"),
    ]
    if event.description:
        lines.append("DESCRIPTION:" + _escape_text(event.description))
    if event.recurrence is not None:
        lines.append("RRULE:" + _serialize_recurrence(event.recurrence))
    lines.append("END:VEVENT")
    return lines


def _serialize_recurrence(rule: RecurrenceRule) -> str:
    parts = [f"FREQ={rule.frequency.upper()}"]
    if rule.interval != 1:
        parts.append(f"INTERVAL={rule.interval}")
    if rule.weekdays:
        inverse = {value: key for key, value in _WEEKDAYS.items()}
        parts.append("BYDAY=" + ",".join(inverse[day] for day in rule.weekdays))
    elif rule.monthly_ordinal:
        inverse = {value: key for key, value in _WEEKDAYS.items()}
        parts.append(f"BYDAY={rule.monthly_ordinal}{inverse[rule.monthly_weekday]}")
    if rule.until_date:
        parts.append("UNTIL=" + rule.until_date.replace("-", ""))
    return ";".join(parts)


def _parse_content_line(line: str, line_number: int) -> tuple[str, dict[str, str], str]:
    colon = _separator_outside_quotes(line, ":")
    if colon < 1:
        raise ValueError(f"Invalid iCalendar content line {line_number}.")
    left, value = line[:colon], line[colon + 1:]
    pieces = _split_outside_quotes(left, ";")
    raw_name = pieces[0]
    name = raw_name.rsplit(".", 1)[-1].upper()
    if not re.fullmatch(r"[A-Z0-9-]+", name):
        raise ValueError(f"Invalid iCalendar property name on line {line_number}.")
    parameters: dict[str, str] = {}
    for piece in pieces[1:]:
        key, separator, parameter_value = piece.partition("=")
        key = key.upper()
        if not separator or not key or key in parameters:
            raise ValueError(f"Invalid iCalendar parameter on line {line_number}.")
        parameters[key] = parameter_value.strip('"')
    return name, parameters, value


def _property_map(
    properties: list[tuple[str, dict[str, str], str]],
    label: str,
) -> dict[str, list[tuple[dict[str, str], str]]]:
    result: dict[str, list[tuple[dict[str, str], str]]] = {}
    for name, parameters, value in properties:
        if name in {"BEGIN", "END"}:
            continue
        result.setdefault(name, []).append((parameters, value))
    for singleton in ("VERSION", "PRODID", "CALSCALE", "METHOD", "X-WR-CALNAME", "X-WR-TIMEZONE"):
        if label == "Calendar" and len(result.get(singleton, [])) > 1:
            raise ValueError(f"{label} repeats singleton property {singleton}.")
    return result


def _single_value(
    properties: dict[str, list[tuple[dict[str, str], str]]],
    name: str,
    fallback: str,
) -> str:
    values = properties.get(name, [])
    return values[0][1] if values else fallback


def _ical_date(value: str, label: str, blockers: list[str]) -> str:
    if not _DATE_VALUE.fullmatch(value):
        blockers.append(f"{label} must be a date-only YYYYMMDD value.")
        return ""
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:])).isoformat()
    except ValueError:
        blockers.append(f"{label} is not a valid date.")
        return ""


def _is_date_property(parameters: dict[str, str], value: str) -> bool:
    return parameters.get("VALUE", "DATE").upper() == "DATE" and bool(_DATE_VALUE.fullmatch(value))


def _unescape_text(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            following = value[index + 1]
            output.append("\n" if following in {"n", "N"} else following)
            index += 2
        else:
            output.append(value[index])
            index += 1
    return "".join(output)


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_lines(lines: list[str]) -> bytes:
    folded: list[bytes] = []
    for line in lines:
        current = bytearray()
        limit = 75
        for character in line:
            encoded = character.encode("utf-8")
            if current and len(current) + len(encoded) > limit:
                folded.append(bytes(current))
                current = bytearray(b" ")
                limit = 75
            current.extend(encoded)
        folded.append(bytes(current))
    return b"\r\n".join(folded) + b"\r\n"


def _member_name(name: str, kind: str, source_id: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() or "calendar"
    return f"{slug}-{kind}-{source_id}.ics"


def _separator_outside_quotes(value: str, separator: str) -> int:
    quoted = False
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            quoted = not quoted
        elif character == separator and not quoted:
            return index
    return -1


def _split_outside_quotes(value: str, separator: str) -> list[str]:
    pieces: list[str] = []
    start = 0
    while True:
        relative = _separator_outside_quotes(value[start:], separator)
        if relative < 0:
            pieces.append(value[start:])
            return pieces
        index = start + relative
        pieces.append(value[start:index])
        start = index + 1
